#!/usr/bin/env python3
"""Record user-reported publications locally and reconcile their CSV identities."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tempfile

AUDIT = Path(__file__).resolve().parents[1] / 'ig-audit' / 'analyse.py'
spec = importlib.util.spec_from_file_location('publication_audit', AUDIT)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
FIELDS = {'account', 'content_id', 'post_id', 'format', 'distribution', 'published_at', 'reference'}
ENTRY_FIELDS = FIELDS | {'revision', 'recorded_at', 'source_sha256'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object)


def validate(data, account):
    if not isinstance(data, dict) or set(data) != FIELDS:
        raise ValueError('publication fields must match the documented schema')
    if any(not isinstance(value, str) or not value.strip() for value in data.values()):
        raise ValueError('every publication field needs nonempty text')
    data = {key: value.strip() for key, value in data.items()}
    data['account'] = audit.accounts.normalize_handle(data['account'])
    if data['account'] != audit.accounts.normalize_handle(account):
        raise ValueError('publication account does not match --account')
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', data['content_id']):
        raise ValueError('content_id needs a short lowercase slug, e.g. workshop-cover-01')
    if data['format'] not in ('reel', 'carousel', 'image', 'story'):
        raise ValueError('unsupported format')
    if data['distribution'] not in ('organic', 'paid', 'unknown'):
        raise ValueError('distribution must be organic, paid or unknown')
    if audit.timestamp(data['published_at']) > datetime.now(timezone.utc):
        raise ValueError('published_at is in the future; planned posts are not publication records')
    return data


def ledger_path(root, account):
    return Path(audit.accounts.resolve(root, account)['paths']['publications'])


def read_ledger(root, account):
    account = audit.accounts.normalize_handle(account)
    path = ledger_path(root, account)
    if not path.exists():
        return {'schema_version': 1, 'account': account, 'entries': []}
    data = decode(path.read_bytes())
    if (not isinstance(data, dict) or set(data) != {'schema_version', 'account', 'entries'}
            or type(data['schema_version']) is not int or data['schema_version'] != 1
            or data['account'] != account or not isinstance(data['entries'], list)):
        raise ValueError('invalid publication ledger; original file was preserved')
    revisions = {}
    for entry in data['entries']:
        if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
            raise ValueError('invalid publication entry')
        publication = validate({key: entry[key] for key in FIELDS}, account)
        if publication != {key: entry[key] for key in FIELDS}:
            raise ValueError('publication entry must contain normalized fields')
        expected = revisions.get(publication['content_id'], 0) + 1
        if type(entry['revision']) is not int or entry['revision'] != expected:
            raise ValueError('invalid revision sequence')
        revisions[publication['content_id']] = expected
        if (not isinstance(entry['source_sha256'], str)
                or not re.fullmatch(r'[a-f0-9]{64}', entry['source_sha256'])):
            raise ValueError('invalid source hash')
        if not isinstance(entry['recorded_at'], str):
            raise ValueError('recorded_at must be a timezone-aware timestamp')
        recorded = audit.timestamp(entry['recorded_at'])
        if recorded < audit.timestamp(publication['published_at']):
            raise ValueError('recorded_at precedes publication')
    current = list(latest(data).values())
    if len({entry['post_id'] for entry in current}) != len(current):
        raise ValueError('different content records cannot share an active post_id')
    return data


def latest(ledger):
    return {entry['content_id']: entry for entry in ledger['entries']}


def record(raw, root, account, revise=False):
    publication = validate(decode(raw), account)
    path = ledger_path(root, account)
    lock = path.with_name('.publications.lock')
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError('publication ledger is locked; another write may be running') from error
    temporary = None
    try:
        ledger = read_ledger(root, account)
        active = latest(ledger)
        previous = active.get(publication['content_id'])
        if previous is not None and not revise:
            raise ValueError('content_id is already recorded; use --revise for an explicit correction')
        if previous is None and revise:
            raise ValueError('--revise requires an existing content_id')
        if any(entry['post_id'] == publication['post_id'] and entry['content_id'] != publication['content_id']
               for entry in active.values()):
            raise ValueError('post_id already belongs to another content record')
        entry = {**publication, 'revision': previous['revision'] + 1 if previous else 1,
                 'recorded_at': datetime.now(timezone.utc).isoformat(),
                 'source_sha256': hashlib.sha256(raw).hexdigest()}
        ledger['entries'].append(entry)
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                         prefix='.publications-', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(json.dumps(ledger, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        temporary.replace(path)
        return {'account': publication['account'], 'status': 'revised' if previous else 'recorded',
                'saved_to': str(path), 'entry': entry, 'verification': 'user-reported, not platform-verified'}
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
        lock.rmdir()


def reconcile(raw, root, account):
    ledger = read_ledger(root, account)
    active = {entry['post_id']: entry for entry in latest(ledger).values()}
    report = audit.analyse(raw, account, 'views')
    csv_ids = {post['post_id'] for post in report['posts']}
    matched, conflicts = [], []
    for post in report['posts']:
        entry = active.get(post['post_id'])
        if entry is None:
            continue
        fields = [name for name in ('format', 'distribution') if post[name] != entry[name]]
        if audit.timestamp(post['published_at']) != audit.timestamp(entry['published_at']):
            fields.append('published_at')
        if fields:
            conflicts.append({'post_id': post['post_id'], 'content_id': entry['content_id'],
                              'fields': {field: {'record': entry[field], 'csv': post[field]} for field in fields}})
        else:
            matched.append({'post_id': post['post_id'], 'content_id': entry['content_id'], 'revision': entry['revision']})
    return {'account': ledger['account'], 'source_sha256': report['source_sha256'],
            'ledger_sha256': hashlib.sha256(json.dumps(ledger, sort_keys=True, ensure_ascii=False).encode()).hexdigest(),
            'matched': matched, 'identity_conflicts': conflicts,
            'csv_without_record': sorted(csv_ids - set(active)),
            'records_without_csv': sorted(set(active) - csv_ids),
            'limitations': ['Records reflect user reports, not platform verification or measured performance.',
                            'Missing rows may reflect a partial export; no values or IDs are inferred or changed.',
                            'Match exact post_id strings across publications, CSV and experiment assignments.',
                            'Resolve conflicts before drawing conclusions; reconciliation does not edit the CSV or prior audit snapshots.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('check', 'record', 'list', 'reconcile'):
        command = commands.add_parser(name)
        command.add_argument('--account', required=True)
        command.add_argument('--root', default=audit.accounts.DEFAULT_ROOT)
        if name in ('check', 'record'):
            command.add_argument('input', type=Path)
        if name == 'record':
            command.add_argument('--revise', action='store_true')
        if name == 'reconcile':
            command.add_argument('csv', type=Path)
    args = parser.parse_args()
    try:
        if args.command == 'check':
            result = {'status': 'valid', 'publication': validate(decode(args.input.read_bytes()), args.account)}
        elif args.command == 'record':
            result = record(args.input.read_bytes(), args.root, args.account, args.revise)
        elif args.command == 'list':
            ledger = read_ledger(args.root, args.account)
            result = {'account': ledger['account'], 'publications': list(latest(ledger).values()),
                      'revision_count': len(ledger['entries']), 'verification': 'user-reported, not platform-verified'}
        else:
            result = reconcile(args.csv.read_bytes(), args.root, args.account)
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError, UnicodeError, TypeError, OverflowError, audit.csv.Error) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    main()
