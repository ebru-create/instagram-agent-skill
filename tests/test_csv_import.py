"""Explicit import mapping, locale precision, previews and safe canonical export."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_regressions import ROOT, cli, load

importer = load('csv_import_tests', 'skills/ig-audit/import_csv.py')
SOURCE = ROOT / 'skills/ig-audit/import.example.tr.csv'
MAPPING = ROOT / 'skills/ig-audit/import.mapping.example.tr.json'
UI = 'skills/ig-account/turkce.py'


class CsvImportTests(unittest.TestCase):
    def setUp(self):
        self.raw = SOURCE.read_bytes()
        self.config = json.loads(MAPPING.read_text())

    def convert(self, raw=None, account='ornek_studyo'):
        return importer.convert(raw if raw is not None else self.raw,
                                json.dumps(self.config, ensure_ascii=False).encode(), account)

    def test_turkish_source_maps_to_valid_canonical_data_and_preserves_missing_zero(self):
        report, canonical = self.convert()
        self.assertEqual(report['status'], 'ready')
        self.assertEqual(report['source_record_count'], 3)
        self.assertEqual(report['canonical_preview'][0]['views'], '1000')
        self.assertEqual(report['canonical_preview'][0]['saves'], '')
        self.assertEqual(report['canonical_preview'][2]['saves'], '0')
        self.assertEqual(report['canonical_preview'][2]['duration_seconds'], '15.5')
        self.assertEqual(report['canonical_preview'][2]['average_watch_seconds'], '6.25')
        self.assertEqual(report['canonical_preview'][0]['published_at'], '2026-09-01T12:00:00+03:00')
        analysed = importer.audit.analyse(canonical, 'ornek_studyo', 'shares_per_reach')
        self.assertEqual(analysed['posts'][0]['metrics']['shares_per_reach'], .02)
        self.assertEqual(analysed['posts'][1]['metrics']['shares_per_reach'], .04)
        self.assertEqual(report['source_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(report['canonical_sha256'], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(report['unmapped_source_columns'], ['Not'])

    def test_locales_are_explicit_and_grouping_must_be_valid(self):
        for value, style, expected in [('1.234', 'tr', '1234'), ('1,234', 'en', '1234'),
                                        ('1.234,0', 'tr', '1234'), ('1,234.0', 'en', '1234'),
                                        ('00123', 'plain', '123')]:
            self.assertEqual(importer.numeric(value, style, True), expected)
        for value, style in [('1,234', 'tr'), ('1.234', 'en'), ('12.34', 'tr'), ('1.2K', 'en'),
                             ('1,2 B', 'tr'), ('-1', 'plain'), ('NaN', 'plain')]:
            with self.subTest(value=value, style=style), self.assertRaises(importer.ImportIssue):
                importer.numeric(value, style, True)
        self.assertEqual(importer.numeric('0,125', 'tr', False), '0.125')

    def test_fractional_count_blocks_export_without_rounding_or_row_filtering(self):
        report, _ = self.convert(self.raw.replace(b'1.000;800', b'1,2;800'))
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['source_record_count'], 3)
        self.assertEqual(report['converted_record_count'], 2)
        self.assertEqual(report['errors'][0]['code'], 'count_fraction')
        self.assertEqual(report['errors'][0]['source_line'], 2)
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):
            importer.export(report, b'', Path(temp) / 'never')

    def test_wrong_account_and_duplicate_ids_fail_canonical_validation(self):
        report, _ = self.convert(account='another')
        self.assertEqual(report['status'], 'blocked')
        self.assertIn('account', report['errors'][0]['message'])
        report, _ = self.convert(self.raw.replace(b'fictional-2', b'fictional-1'))
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['errors'][0]['source_line'], 3)
        self.assertNotIn('canonical_sha256', report)

    def test_mixed_accounts_from_a_mapped_column_are_never_silently_filtered(self):
        self.config['columns']['account'] = 'Not'
        del self.config['constants']['account']
        raw = self.raw.decode().replace('Tamamen kurgusal veri', 'ornek_studyo', 1).replace('Tamamen kurgusal veri', 'other')
        report, _ = self.convert(raw.encode())
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['source_record_count'], 3)

    def test_unmapped_labels_and_bad_row_width_are_visible(self):
        report, _ = self.convert(self.raw.replace('Organik'.encode(), 'Bilinmeyen'.encode(), 1))
        self.assertEqual(report['errors'][0]['code'], 'value_map')
        report, _ = self.convert(self.raw + b'broken;row\n')
        self.assertEqual(report['errors'][0]['code'], 'row_width')
        self.assertEqual(report['status'], 'blocked')

    def test_no_date_only_or_naive_timezone_guessing(self):
        config = copy.deepcopy(self.config)
        config['date_format'] = 'iso'; config['timezone'] = None
        with self.assertRaises(importer.ImportIssue):
            importer.date('2026-09-01T12:00:00', config)
        config['timezone'] = '+03:00'
        with self.assertRaises(importer.ImportIssue):
            importer.date('2026-09-01', config)
        self.assertEqual(importer.date('2026-09-01T09:00:00Z', config), '2026-09-01T09:00:00+00:00')
        self.assertEqual(importer.date('2026-09-01T12:00:00', config), '2026-09-01T12:00:00+03:00')

    def test_date_order_is_configured_not_inferred_from_number_locale(self):
        self.config['date_format'] = '%d/%m/%Y %H:%M'
        self.assertTrue(importer.date('03/04/2026 12:00', self.config).startswith('2026-04-03'))
        self.config['date_format'] = '%m/%d/%Y %H:%M'
        self.assertTrue(importer.date('03/04/2026 12:00', self.config).startswith('2026-03-04'))

    def test_bom_and_explicit_cp1254_encoding(self):
        report, _ = self.convert(b'\xef\xbb\xbf' + self.raw)
        self.assertEqual(report['status'], 'ready')
        self.config['encoding'] = 'cp1254'
        report, _ = self.convert(self.raw.decode().replace('—', '').encode('cp1254'))
        self.assertEqual(report['status'], 'ready')

    def test_missing_values_cannot_designate_numbers_or_invent_metric_constants(self):
        for change in [('missing_values', ['0']), ('constants', {**self.config['constants'], 'views': '0'}),
                       ('measurement_scope', 'last_30_days'), ('timezone', None)]:
            config = copy.deepcopy(self.config); config[change[0]] = change[1]
            with self.subTest(change=change), self.assertRaises(ValueError):
                importer.mapping(json.dumps(config).encode())

    def test_business_metrics_require_explicit_post_attribution(self):
        self.config['columns']['bookings'] = 'Not'
        with self.assertRaises(ValueError):
            importer.mapping(json.dumps(self.config).encode())
        self.config['attribution'] = 'post_level_confirmed'
        self.assertEqual(importer.mapping(json.dumps(self.config).encode())['attribution'], 'post_level_confirmed')

    def test_duplicate_header_and_json_key_and_missing_source_column_fail(self):
        for raw in (b'col;col\n1;2\n', b';col\n1;2\n'):
            with self.assertRaises(ValueError):
                importer.source_rows(raw, ';', 'utf-8')
        raw = MAPPING.read_bytes().replace(b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,')
        with self.assertRaises(ValueError):
            importer.mapping(raw)
        self.config['columns']['views'] = 'Absent'
        with self.assertRaises(ValueError):
            self.convert()

    def test_preview_is_bounded_and_no_error_is_hidden_by_a_success_status(self):
        bad_row = self.raw.decode().splitlines()[1].replace('1.000', '1,2')
        report, _ = self.convert(('\n'.join([self.raw.decode().splitlines()[0]] + [bad_row] * 25) + '\n').encode())
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['error_count'], 25)
        self.assertEqual(len(report['errors']), 20)
        self.assertEqual(report['source_record_count'], 25)

    def test_new_output_contains_valid_csv_and_provenance_and_refuses_overwrite(self):
        report, canonical = self.convert()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'converted'
            saved = importer.export(report, canonical, output)
            self.assertEqual((output / 'canonical.csv').read_bytes(), canonical)
            self.assertEqual(json.loads((output / 'import-report.json').read_text()), saved)
            self.assertEqual(saved['status'], 'exported')
            self.assertEqual(SOURCE.read_bytes(), self.raw)
            with self.assertRaises(ValueError):
                importer.export(report, canonical, output)

    def test_failed_write_cleans_staging_and_never_produces_partial_output(self):
        report, canonical = self.convert()
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'converted'
            with patch.object(Path, 'write_bytes', side_effect=OSError('simulated disk failure')):
                with self.assertRaises(OSError):
                    importer.export(report, canonical, output)
            self.assertFalse(output.exists())
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_cli_and_turkish_entrypoint_preview_and_blocked_export_are_read_only(self):
        preview = cli(UI, 'ice-aktar', str(SOURCE), '--esleme', str(MAPPING), '--hesap', 'ornek_studyo')
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertIn('dosya henüz yazılmadı', preview.stdout)
        inspect = cli(UI, 'ice-aktar', str(SOURCE), '--ayirici', ';')
        self.assertEqual(inspect.returncode, 0, inspect.stderr)
        self.assertIn('Kaynak sütunlar incelendi', inspect.stdout)
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'never'
            blocked = cli(UI, 'ice-aktar', str(SOURCE), '--esleme', str(MAPPING), '--hesap', 'other', '--cikti', str(output), '--json')
            self.assertEqual(blocked.returncode, 2)
            self.assertEqual(json.loads(blocked.stdout)['status'], 'blocked')
            self.assertFalse(output.exists())
            conflict = cli(UI, 'ice-aktar', str(SOURCE), '--esleme', str(MAPPING), '--hesap', 'ornek_studyo', '--ayirici', ';')
            self.assertEqual(conflict.returncode, 2)
            self.assertIn('yalnızca sütun incelemesinde', conflict.stderr)


if __name__ == '__main__':
    unittest.main()
