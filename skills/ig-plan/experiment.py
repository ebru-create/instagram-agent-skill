#!/usr/bin/env python3
"""Validate a local two-variant content test and review canonical CSV snapshots."""
import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import shutil
from statistics import median
import tempfile
import uuid

AUDIT_PATH = Path(__file__).resolve().parents[1] / 'ig-audit' / 'analyse.py'
spec = importlib.util.spec_from_file_location('experiment_audit', AUDIT_PATH)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
FIELDS = {'schema_version', 'account', 'experiment_id', 'hypothesis', 'change',
          'held_similar', 'confounders', 'primary_metric', 'direction', 'minimum_effect',
          'format', 'distribution', 'observation_hours', 'review_at',
          'min_posts_per_variant', 'assignments'}
VARIANTS = ('control', 'variant')


def text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{field} needs nonempty text')
    return value.strip()


def positive(value, field):
    if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{field} needs a finite positive number')
    return value


def validate(plan, account):
    if not isinstance(plan, dict) or set(plan) != FIELDS:
        raise ValueError('plan fields must match the documented schema')
    plan = dict(plan)
    if type(plan['schema_version']) is not int or plan['schema_version'] != 1:
        raise ValueError('schema_version must be 1')
    plan['account'] = audit.accounts.normalize_handle(text(plan['account'], 'account'))
    if plan['account'] != audit.accounts.normalize_handle(account):
        raise ValueError('plan account does not match --account')
    for field in ('experiment_id', 'hypothesis', 'change', 'review_at'):
        plan[field] = text(plan[field], field)
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', plan['experiment_id']):
        raise ValueError('experiment_id needs 1-64 lowercase letters, digits, hyphens or underscores')
    for field in ('held_similar', 'confounders'):
        if not isinstance(plan[field], list) or not plan[field]:
            raise ValueError(f'{field} needs a nonempty list of notes')
        plan[field] = [text(item, field) for item in plan[field]]
    if plan['primary_metric'] not in audit.METRICS:
        raise ValueError('unsupported primary_metric')
    if plan['direction'] not in ('higher', 'lower'):
        raise ValueError('direction must be higher or lower')
    positive(plan['minimum_effect'], 'minimum_effect')
    positive(plan['observation_hours'], 'observation_hours')
    if not math.isfinite(plan['observation_hours'] * 3600):
        raise ValueError('observation_hours is too large')
    if plan['format'] not in ('reel', 'carousel', 'image', 'story'):
        raise ValueError('unsupported format')
    if plan['format'] != 'reel' and plan['primary_metric'] in ('starts', 'viewers_3s', 'hold_3s') + audit.DURATIONS:
        raise ValueError('video primary metrics require reel format in this schema')
    if plan['distribution'] not in ('organic', 'paid'):
        raise ValueError('distribution must be known: organic or paid')
    audit.timestamp(plan['review_at'])
    count = plan['min_posts_per_variant']
    if type(count) is not int or count < 1:
        raise ValueError('min_posts_per_variant must be a positive integer chosen for this test')
    if not isinstance(plan['assignments'], list):
        raise ValueError('assignments must be a list (empty before published IDs are available)')
    assignments, seen = [], set()
    for item in plan['assignments']:
        if not isinstance(item, dict) or set(item) != {'post_id', 'variant'}:
            raise ValueError('each assignment needs only post_id and variant')
        post_id = text(item['post_id'], 'post_id')
        if post_id in seen or item['variant'] not in VARIANTS:
            raise ValueError('assignments need unique post IDs and control/variant labels')
        seen.add(post_id)
        assignments.append({'post_id': post_id, 'variant': item['variant']})
    plan['assignments'] = assignments
    return plan


def review(plan, raw, as_of):
    plan = validate(plan, plan['account'])
    as_of_time = audit.timestamp(as_of)
    evidence = audit.analyse(raw, plan['account'], plan['primary_metric'])
    posts = {post['post_id']: post for post in evidence['posts']}
    arms = {arm: [] for arm in VARIANTS}
    exact_values = {arm: [] for arm in VARIANTS}
    excluded = []
    for assignment in plan['assignments']:
        post = posts.get(assignment['post_id'])
        reason = None
        if post is None:
            reason = 'missing_post'
        elif audit.timestamp(post['captured_at']) > as_of_time:
            reason = 'capture_after_as_of'
        elif post['format'] != plan['format'] or post['distribution'] != plan['distribution']:
            reason = 'format_or_distribution_mismatch'
        elif post['observation_seconds'] != plan['observation_hours'] * 3600:
            reason = 'observation_window_mismatch'
        elif post['metrics'][plan['primary_metric']] is None:
            reason = 'primary_metric_unavailable'
        if reason:
            excluded.append({**assignment, 'reason': reason})
        else:
            metric = plan['primary_metric']
            if metric in audit.RATES:
                numerator, denominator = audit.RATES[metric]
                value = Fraction(post['metrics'][numerator], post['metrics'][denominator])
                inputs = {name: post['metrics'][name] for name in (numerator, denominator)}
            else:
                value = Fraction(str(post['metrics'][metric]))
                inputs = {metric: post['metrics'][metric]}
            exact_values[assignment['variant']].append(value)
            arms[assignment['variant']].append({'post_id': post['post_id'],
                                               'value': post['metrics'][plan['primary_metric']],
                                               'inputs': inputs,
                                               'published_at': post['published_at'],
                                               'captured_at': post['captured_at']})
    medians = {arm: median(values) if values else None for arm, values in exact_values.items()}
    groups = {arm: {'assigned_n': sum(a['variant'] == arm for a in plan['assignments']),
                    'usable_n': len(rows), 'median': float(medians[arm]) if rows else None,
                    'observations': rows} for arm, rows in arms.items()}
    enough = not excluded and all(group['usable_n'] >= plan['min_posts_per_variant'] for group in groups.values())
    status = ('waiting_for_review' if as_of_time < audit.timestamp(plan['review_at']) else
              'ready_descriptive' if enough else 'incomplete')
    difference, criterion = None, None
    if status == 'ready_descriptive':
        exact_difference = medians['variant'] - medians['control']
        difference = float(exact_difference)
        directed = exact_difference if plan['direction'] == 'higher' else -exact_difference
        criterion = directed >= Fraction(str(plan['minimum_effect']))
    return {'status': status, 'as_of': as_of, 'source_sha256': evidence['source_sha256'],
            'primary_metric': plan['primary_metric'], 'direction': plan['direction'],
            'groups': groups, 'excluded_assignments': excluded,
            'ignored_post_ids': sorted(set(posts) - {a['post_id'] for a in plan['assignments']}),
            'variant_minus_control': difference, 'minimum_effect_met': criterion,
            'limitations': [
                'Readiness and minimum counts are user-set bookkeeping criteria, not statistical power or significance.',
                'Medians use per-post metric values, not pooled event totals; rate units are fractions.',
                'Assignments and held-similar notes are supplied by the user; randomization and comparability are not verified.',
                'Small samples, topic, timing, audience and selection can explain differences; no causal winner or automatic scaling decision.',
                'Inputs and as_of are user-supplied. A saved plan is not proof of prospective registration; revisions need disclosure.',
                'No final difference or criterion is emitted before review_at or while assigned observations are unavailable.'
            ]}


def unique_object(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise ValueError(f'duplicate JSON key: {key}')
        obj[key] = value
    return obj


def build(plan_raw, account, csv_raw=None, as_of=None):
    plan = validate(json.loads(plan_raw.decode('utf-8-sig'), object_pairs_hook=unique_object), account)
    if as_of is not None and csv_raw is None:
        raise ValueError('--as-of requires --csv')
    result = {'schema_version': 1, 'account': plan['account'], 'plan': plan,
              'plan_sha256': hashlib.sha256(plan_raw).hexdigest(),
              'status': 'validated_plan'}
    if csv_raw is not None:
        result['review'] = review(plan, csv_raw, as_of or datetime.now(timezone.utc).isoformat())
        result['status'] = result['review']['status']
    return result


def save(result, root):
    directory = Path(audit.accounts.resolve(root, result['account'])['directory']) / 'experiments'
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise ValueError('experiments must be a regular directory')
    directory.mkdir(exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.pending-', dir=directory))
    destination = directory / ('experiment-' + uuid.uuid4().hex)
    saved = {**result, 'saved_at': datetime.now(timezone.utc).isoformat()}
    try:
        (staging / 'report.json').write_text(json.dumps(saved, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        staging.rename(destination)
    except BaseException:
        shutil.rmtree(staging)
        raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('--account', required=True)
    parser.add_argument('--csv', type=Path, help='canonical account CSV; omit to validate the plan only')
    parser.add_argument('--as-of', help='timezone-aware review time; defaults to current UTC time')
    parser.add_argument('--save', action='store_true', help='save a fresh snapshot in an initialized account')
    parser.add_argument('--root', default=audit.accounts.DEFAULT_ROOT)
    args = parser.parse_args()
    try:
        result = build(args.plan.read_bytes(), args.account, args.csv.read_bytes() if args.csv else None, args.as_of)
        if args.save:
            print(json.dumps({'account': result['account'], 'status': result['status'], 'saved_to': str(save(result, args.root))}))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, OSError, UnicodeError, OverflowError, TypeError, audit.csv.Error) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    main()
