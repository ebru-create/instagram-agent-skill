#!/usr/bin/env python3
"""Inspect/map a supplied CSV into the canonical audit schema without guessing."""
import argparse
import csv
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import tempfile

spec = importlib.util.spec_from_file_location('import_audit', Path(__file__).with_name('analyse.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
FIELDS = audit.IDENTITY + audit.COUNTS + audit.DURATIONS
REQUIRED = {'schema_version', 'delimiter', 'encoding', 'number_format', 'date_format',
            'timezone', 'columns', 'constants', 'value_maps', 'missing_values', 'measurement_scope'}
DATE_FORMATS = ('iso', '%d.%m.%Y %H:%M', '%d/%m/%Y %H:%M', '%m/%d/%Y %H:%M', '%Y-%m-%d %H:%M:%S')


class ImportIssue(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key: ' + key)
        result[key] = value
    return result


def mapping(raw):
    config = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object)
    if not isinstance(config, dict) or not REQUIRED <= set(config) or set(config) - REQUIRED - {'attribution'}:
        raise ValueError('mapping fields must match the documented schema')
    if type(config['schema_version']) is not int or config['schema_version'] != 1:
        raise ValueError('mapping schema_version must be 1')
    for name, allowed in (('delimiter', (',', ';', '\t')), ('encoding', ('utf-8', 'utf-8-sig', 'cp1254')),
                          ('number_format', ('plain', 'tr', 'en')), ('date_format', DATE_FORMATS)):
        if config[name] not in allowed:
            raise ValueError('unsupported mapping ' + name)
    if config['measurement_scope'] != 'cumulative_since_publication':
        raise ValueError('measurement_scope must confirm cumulative_since_publication; calendar-range subtotals are incompatible')
    offset = config['timezone']
    if offset is not None and (not isinstance(offset, str) or not re.fullmatch(r'[+-](?:0\d|1[0-3]):[0-5]\d|[+-]14:00', offset)):
        raise ValueError('timezone must be null or an explicit offset such as +03:00')
    if config['date_format'] != 'iso' and offset is None:
        raise ValueError('an explicit timezone is required for naive source dates')
    for name in ('columns', 'constants', 'value_maps'):
        if not isinstance(config[name], dict):
            raise ValueError(name + ' must be an object')
    columns, constants = config['columns'], config['constants']
    if (set(columns) - set(FIELDS) or set(constants) - {'account', 'format', 'distribution', 'captured_at'}
            or set(columns) & set(constants) or not set(audit.IDENTITY) <= set(columns) | set(constants)):
        raise ValueError('mapping must cover all identity fields without overlapping columns/constants or invented metric constants')
    if any(not isinstance(value, str) or not value.strip() or value != value.strip() for value in list(columns.values()) + list(constants.values())):
        raise ValueError('mapping column names/constants must be nonempty trimmed text')
    if len(set(columns.values())) != len(columns):
        raise ValueError('one source column cannot supply multiple canonical fields')
    if set(config['value_maps']) - {'format', 'distribution'}:
        raise ValueError('value_maps supports only format and distribution')
    for name, values in config['value_maps'].items():
        allowed = ('reel', 'carousel', 'image', 'story') if name == 'format' else ('organic', 'paid', 'unknown')
        if not isinstance(values, dict) or not values or name not in columns:
            raise ValueError('value maps need a mapped source column and nonempty pairs')
        if any(not isinstance(key, str) or not key or key != key.strip() or value not in allowed for key, value in values.items()):
            raise ValueError('invalid value map entries')
    missing = config['missing_values']
    if not isinstance(missing, list) or any(not isinstance(v, str) or v != v.strip() or any(c.isdigit() for c in v) for v in missing):
        raise ValueError('missing_values must be trimmed text tokens without digits; never designate observed numbers as missing')
    if set(columns) & {'enquiries', 'bookings'} and config.get('attribution') != 'post_level_confirmed':
        raise ValueError('business metrics require explicit post_level_confirmed attribution')
    return config


def source_rows(raw, delimiter, encoding):
    reader = csv.reader(io.StringIO(raw.decode(encoding), newline=''), delimiter=delimiter, strict=True)
    headers = [cell.strip() for cell in next(reader, [])]
    if not headers or any(not name for name in headers) or len(set(headers)) != len(headers):
        raise ValueError('source CSV needs unique nonempty column headers')
    rows = [(reader.line_num, row) for row in reader]
    return headers, rows


def numeric(value, style, count):
    if style == 'plain':
        pattern, grouping, decimal = r'[0-9]+(?:\.[0-9]+)?', '', '.'
    else:
        grouping, decimal = ('.', ',') if style == 'tr' else (',', '.')
        group, dec = re.escape(grouping), re.escape(decimal)
        pattern = rf'(?:[0-9]+|[0-9]{{1,3}}(?:{group}[0-9]{{3}})+)(?:{dec}[0-9]+)?'
    if not re.fullmatch(pattern, value):
        raise ImportIssue('number_format', 'number does not match the explicitly selected locale; abbreviations are unsupported')
    normalized = value.replace(grouping, '') if grouping else value
    number = Decimal(normalized.replace(decimal, '.'))
    if count and number != number.to_integral_value():
        raise ImportIssue('count_fraction', 'count is fractional; no rounding is performed')
    return str(int(number)) if count else format(number, 'f')


def date(value, config):
    try:
        if config['date_format'] == 'iso':
            if not re.search(r'[T ]\d{2}:\d{2}', value):
                raise ValueError('ISO input must include the actual time')
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        else:
            parsed = datetime.strptime(value, config['date_format'])
        if parsed.tzinfo is None:
            offset = config['timezone']
            if offset is None:
                raise ValueError('naive source date needs an explicit offset')
            minutes = (int(offset[1:3]) * 60 + int(offset[4:])) * (-1 if offset[0] == '-' else 1)
            parsed = parsed.replace(tzinfo=timezone(timedelta(minutes=minutes)))
        return parsed.isoformat()
    except ValueError as error:
        raise ImportIssue('date_format', 'date does not match the selected format/timezone') from error


def canonical_bytes(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator='\n')
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def convert(raw, config_raw, account):
    config = mapping(config_raw)
    account = audit.accounts.normalize_handle(account)
    headers, records = source_rows(raw, config['delimiter'], config['encoding'])
    missing_columns = sorted(set(config['columns'].values()) - set(headers))
    if missing_columns:
        raise ValueError('mapped source columns not found: ' + ', '.join(missing_columns))
    converted, issues = [], []
    for record, (line, cells) in enumerate(records, 2):
        if len(cells) != len(headers):
            issues.append({'record': record, 'source_line': line, 'field': None, 'code': 'row_width', 'message': 'row column count does not match header'})
            continue
        source = dict(zip(headers, cells))
        row, row_issues = {}, []
        for field in FIELDS:
            value = (source[config['columns'][field]] if field in config['columns'] else config['constants'].get(field, '')).strip()
            try:
                if field in audit.COUNTS + audit.DURATIONS:
                    value = '' if not value or value in config['missing_values'] else numeric(value, config['number_format'], field in audit.COUNTS)
                elif field in ('published_at', 'captured_at'):
                    value = date(value, config)
                elif field in config['value_maps']:
                    if value not in config['value_maps'][field]:
                        raise ImportIssue('value_map', 'source label is not in the explicit value map')
                    value = config['value_maps'][field][value]
                row[field] = value
            except ImportIssue as error:
                row_issues.append({'record': record, 'source_line': line, 'field': field,
                                   'value': value, 'code': error.code, 'message': str(error)})
        issues.extend(row_issues)
        if not row_issues:
            converted.append(row)
    canonical = canonical_bytes(converted)
    if not issues:
        try:
            audit.analyse(canonical, account, 'views')
        except (ValueError, OverflowError) as error:
            match = re.search(r'CSV line (\d+)', str(error))
            index = int(match[1]) - 2 if match else None
            issues.append({'record': index + 2 if index is not None else None,
                           'source_line': records[index][0] if index is not None and index < len(records) else None,
                           'field': None, 'code': 'canonical_validation', 'message': str(error)})
    report = {'schema_version': 1, 'status': 'blocked' if issues else 'ready', 'account': account,
              'source_sha256': hashlib.sha256(raw).hexdigest(), 'mapping_sha256': hashlib.sha256(config_raw).hexdigest(),
              'importer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'mapping': config,
              'source_columns': headers, 'unmapped_source_columns': [h for h in headers if h not in config['columns'].values()],
              'source_record_count': len(records), 'converted_record_count': len(converted),
              'error_count': len(issues), 'errors': issues[:20], 'canonical_preview': converted[:5],
              'missing_counts': {name: sum(not row[name] for row in converted) for name in FIELDS},
              'missing_counts_basis': 'converted records only; invalid records are listed as errors',
              'limitations': ['Only user-mapped fields are interpreted; semantic definitions, source authenticity and post attribution are not verified.',
                              'Counts must be cumulative since publication. Account constants assert file ownership; never use them to combine brands.',
                              'No date/locale/timezone guessing, row filtering, rounding of counts or abbreviation expansion is performed.',
                              'Preview includes at most five converted records and twenty errors. All errors block export; converted rows alone do not imply import readiness.']}
    if not issues:
        report['canonical_sha256'] = hashlib.sha256(canonical).hexdigest()
    return report, canonical


def export(report, canonical, output):
    if report['status'] != 'ready':
        raise ValueError('import is blocked; fix all errors before exporting')
    output = Path(output).expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise ValueError('choose a new output directory; existing files are preserved')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.csv-import-', dir=output.parent))
    exported = {**report, 'status': 'exported', 'output_directory': str(output)}
    try:
        (stage / 'canonical.csv').write_bytes(canonical)
        (stage / 'import-report.json').write_text(json.dumps(exported, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        if output.exists() or output.is_symlink():
            raise ValueError('output directory appeared during import; choose a new output directory')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    return exported


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csv', type=Path)
    parser.add_argument('--mapping', type=Path)
    parser.add_argument('--account')
    parser.add_argument('--out', type=Path, help='new directory with canonical.csv and import-report.json; omit for read-only preview')
    parser.add_argument('--delimiter', choices=(',', ';', '\t'), help='inspection only; default comma')
    parser.add_argument('--encoding', choices=('utf-8', 'utf-8-sig', 'cp1254'), help='inspection only; default utf-8-sig')
    args = parser.parse_args()
    try:
        raw = args.csv.read_bytes()
        if args.mapping:
            if args.delimiter is not None or args.encoding is not None:
                raise ValueError('--delimiter/--encoding are inspection-only; set them in the mapping for conversion')
            if not args.account:
                raise ValueError('--mapping requires --account')
            config_raw = args.mapping.read_bytes()
            report, canonical = convert(raw, config_raw, args.account)
            if args.out and report['status'] == 'ready':
                report = export(report, canonical, args.out)
        else:
            if args.out or args.account:
                raise ValueError('inspection does not accept --out/--account; supply --mapping for conversion')
            headers, records = source_rows(raw, args.delimiter or ',', args.encoding or 'utf-8-sig')
            report = {'status': 'inspected', 'source_sha256': hashlib.sha256(raw).hexdigest(),
                      'source_columns': headers, 'source_record_count': len(records),
                      'source_preview': [dict(zip(headers, cells)) if len(cells) == len(headers) else {'row_width_error': cells} for _, cells in records[:5]],
                      'note': 'Read-only inspection; no semantic field mapping or canonical validation performed.'}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 2 if report['status'] == 'blocked' else 0
    except (ValueError, OSError, UnicodeError, csv.Error, OverflowError) as error:
        parser.exit(2, f'error: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
