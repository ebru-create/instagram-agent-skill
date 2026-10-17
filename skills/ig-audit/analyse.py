#!/usr/bin/env python3
"""Analyse one account's canonical CSV snapshots without network access."""
import argparse
import csv
from datetime import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
from statistics import median
import sys
import tempfile
import uuid

HELPER = Path(__file__).resolve().parents[1] / 'ig-account' / 'account.py'
spec = importlib.util.spec_from_file_location('audit_account', HELPER)
accounts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(accounts)
IDENTITY = ('account', 'post_id', 'format', 'distribution', 'published_at', 'captured_at')
COUNTS = ('views', 'reach', 'shares', 'saves', 'follows', 'non_follower_reach', 'starts', 'viewers_3s', 'enquiries', 'bookings')
DURATIONS = ('duration_seconds', 'average_watch_seconds')
RATES = {'shares_per_reach': ('shares', 'reach'), 'saves_per_reach': ('saves', 'reach'),
         'follows_per_reach': ('follows', 'reach'), 'non_follower_reach_rate': ('non_follower_reach', 'reach'),
         'hold_3s': ('viewers_3s', 'starts')}
METRICS = COUNTS + DURATIONS + tuple(RATES)


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError('timestamps require an explicit UTC offset')
    return parsed


def analyse(raw, account, primary_metric):
    account = accounts.normalize_handle(account)
    if primary_metric not in METRICS:
        raise ValueError('unsupported primary metric')
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
    headers = reader.fieldnames or []
    if len(set(headers)) != len(headers) or not set(IDENTITY) <= set(headers):
        raise ValueError('CSV needs unique headers and all identity columns')
    if set(headers) - set(IDENTITY + COUNTS + DURATIONS):
        raise ValueError('unknown CSV columns; map the source to the documented schema')
    posts, seen = [], set()
    for line, row in enumerate(reader, 2):
        try:
            if None in row or any(value is None for value in row.values()):
                raise ValueError('row column count does not match header')
            row = {key: value.strip() for key, value in row.items()}
            if accounts.normalize_handle(row['account']) != account:
                raise ValueError('account does not match --account')
            post_id = row['post_id']
            if not post_id or post_id in seen:
                raise ValueError('post_id must be nonempty and unique (one snapshot per post)')
            seen.add(post_id)
            if row['format'] not in ('reel', 'carousel', 'image', 'story'):
                raise ValueError('format must be reel, carousel, image or story')
            if row['distribution'] not in ('organic', 'paid', 'unknown'):
                raise ValueError('distribution must be organic, paid or unknown')
            elapsed = timestamp(row['captured_at']) - timestamp(row['published_at'])
            if elapsed.total_seconds() <= 0:
                raise ValueError('captured_at must be after published_at')
            values = {}
            for name in COUNTS + DURATIONS:
                value = row.get(name, '')
                if not value:
                    values[name] = None
                    continue
                pattern = r'[0-9]+' if name in COUNTS else r'[0-9]+(?:\.[0-9]+)?'
                if not re.fullmatch(pattern, value):
                    raise ValueError(f'{name} requires a nonnegative full number; blank means missing')
                values[name] = int(value) if name in COUNTS else float(value)
                if name in DURATIONS and not (0 <= values[name] < float('inf')):
                    raise ValueError(f'{name} must be finite')
            if row['format'] != 'reel' and any(values[k] is not None for k in ('starts', 'viewers_3s') + DURATIONS):
                raise ValueError('video measures are supported only for reels in this schema')
            for numerator, denominator in (('non_follower_reach', 'reach'), ('viewers_3s', 'starts')):
                if values[numerator] is not None and values[denominator] is not None and values[numerator] > values[denominator]:
                    raise ValueError(f'{numerator} cannot exceed {denominator}')
            for name, (numerator, denominator) in RATES.items():
                supported = name != 'hold_3s' or (values['duration_seconds'] is not None and values['duration_seconds'] >= 3)
                values[name] = (values[numerator] / values[denominator]
                                if supported and values[numerator] is not None and values[denominator] else None)
            posts.append({**{key: row[key] for key in IDENTITY}, 'account': account,
                          'observation_seconds': elapsed.total_seconds(), 'metrics': values})
        except (ValueError, OverflowError) as error:
            raise ValueError(f'CSV line {line}: {error}') from error
    if not posts:
        raise ValueError('CSV contains no posts')
    cohorts = {}
    for post in posts:
        key = (post['format'], post['distribution'], post['observation_seconds'])
        cohorts.setdefault(key, []).append(post)
    summaries = []
    for index, (key, group) in enumerate(cohorts.items(), 1):
        comparable = key[1] != 'unknown'
        cohort_id = f'cohort-{index}'
        summaries.append({'id': cohort_id, 'format': key[0], 'distribution': key[1],
                          'observation_seconds': key[2], 'n': len(group), 'comparable': comparable,
                          'published_from': min((p['published_at'] for p in group), key=timestamp),
                          'published_to': max((p['published_at'] for p in group), key=timestamp),
                          'coverage': {name: sum(p['metrics'][name] is not None for p in group) for name in METRICS},
                          'medians': {name: median(v) if (v := [p['metrics'][name] for p in group if p['metrics'][name] is not None]) else None for name in METRICS}})
        for post in group:
            peers = [p['metrics']['views'] for p in group if p is not post and p['metrics']['views'] is not None] if comparable else []
            baseline = median(peers) if peers else None
            post.update(cohort=cohort_id, peer_views_n=len(peers), peer_views_median=baseline,
                        relative_views=post['metrics']['views'] / baseline if baseline and post['metrics']['views'] is not None else None)
    return {'schema_version': 1, 'account': account, 'primary_metric': primary_metric,
            'source_sha256': hashlib.sha256(raw).hexdigest(), 'post_count': len(posts),
            'rate_units': 'fraction (multiply by 100 for percent)',
            'limitations': ['Input is user-mapped canonical CSV, not a verified platform export.',
                            'Exact elapsed observation time, format and distribution define cohorts; unknown distribution has no peer baseline.',
                            'Cohort medians are medians of available per-post values, not pooled rates. Coverage reports usable counts.',
                            'Relative views use other posts only; one peer is descriptive and can be unstable.',
                            'Missing/zero denominators yield null. Enquiries/bookings require user-confirmed post attribution.',
                            'Publication dates, topics, audience and selection can confound comparisons. Associations do not establish causes.'],
            'cohorts': summaries, 'posts': posts}


def save(report, root):
    directory = Path(accounts.resolve(root, report['account'])['directory']) / 'audits'
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError('audits must be a regular directory')
    directory.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=directory))
    destination = directory / ('audit-' + uuid.uuid4().hex)
    try:
        (staging / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--account', required=True)
    parser.add_argument('--primary-metric', required=True, choices=METRICS)
    parser.add_argument('--save', action='store_true', help='save a new snapshot in the initialized account audits directory')
    parser.add_argument('--root', default=accounts.DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        report = analyse(args.csv.read_bytes(), args.account, args.primary_metric)
        if args.save:
            print(json.dumps({'account': report['account'], 'saved_to': str(save(report, args.root))}))
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError, UnicodeError, csv.Error) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    main()
