"""Canonical CSV calculations, evidence limits and isolated account snapshots."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from test_regressions import ROOT, cli, load

audit = load('audit_analytics_tests', 'skills/ig-audit/analyse.py')
EXAMPLE = ROOT / 'skills/ig-audit/example.synthetic.csv'


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.raw = EXAMPLE.read_bytes()
        self.rows = list(csv.DictReader(io.StringIO(self.raw.decode())))

    def report(self, rows=None):
        if rows is None:
            raw = self.raw
        else:
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=list(self.rows[0]))
            writer.writeheader(); writer.writerows(rows)
            raw = output.getvalue().encode()
        return audit.analyse(raw, '@ornek_studyo', 'shares_per_reach')

    def test_rates_raw_counts_coverage_and_provenance(self):
        result = self.report()
        self.assertEqual(result['source_sha256'], hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(result['account'], 'ornek_studyo')
        self.assertEqual(result['post_count'], 4)
        self.assertAlmostEqual(result['posts'][0]['metrics']['shares_per_reach'], .02)
        self.assertEqual(result['posts'][0]['metrics']['shares'], 16)
        self.assertEqual(result['cohorts'][0]['coverage']['bookings'], 0)
        self.assertAlmostEqual(result['cohorts'][0]['medians']['shares_per_reach'], .03)
        self.assertEqual(result['posts'][2]['metrics']['hold_3s'], .6)

    def test_peer_baseline_excludes_self_and_separates_formats_and_paid(self):
        result = self.report()
        first, second, reel, paid = result['posts']
        self.assertEqual(first['peer_views_median'], 2000)
        self.assertEqual(first['relative_views'], .5)
        self.assertEqual(second['relative_views'], 2)
        self.assertEqual(first['peer_views_n'], 1)
        self.assertIsNone(reel['relative_views'])
        self.assertIsNone(paid['relative_views'])
        self.assertEqual(len(result['cohorts']), 3)

    def test_different_observation_windows_never_pool(self):
        self.rows[1]['captured_at'] = '2026-09-09T13:00:00+03:00'
        result = self.report(self.rows)
        self.assertEqual(len(result['cohorts']), 4)
        self.assertIsNone(result['posts'][0]['relative_views'])

    def test_equivalent_timezones_compare_elapsed_time(self):
        self.rows[1]['captured_at'] = '2026-09-09T09:00:00Z'
        self.assertEqual(len(self.report(self.rows)['cohorts']), 3)

    def test_unknown_distribution_has_no_peer_multiple(self):
        for row in self.rows[:2]:
            row['distribution'] = 'unknown'
        result = self.report(self.rows)
        self.assertFalse(result['cohorts'][0]['comparable'])
        self.assertIsNone(result['posts'][0]['relative_views'])

    def test_zero_denominator_missing_numerator_and_missing_baseline(self):
        self.rows[0].update(reach='0', non_follower_reach='0', views='0')
        self.rows[1].update(shares='')
        result = self.report(self.rows)
        self.assertIsNone(result['posts'][0]['metrics']['shares_per_reach'])
        self.assertIsNone(result['posts'][1]['metrics']['shares_per_reach'])
        self.assertIsNone(result['posts'][1]['relative_views'])
        self.assertEqual(result['cohorts'][0]['coverage']['shares_per_reach'], 0)

    def test_short_or_unknown_video_duration_has_no_hold_rate(self):
        for duration in ('2.9', ''):
            with self.subTest(duration=duration):
                self.rows[2]['duration_seconds'] = duration
                self.assertIsNone(self.report(self.rows)['posts'][2]['metrics']['hold_3s'])

    def test_repeat_events_can_exceed_reach(self):
        self.rows[0]['shares'] = '1600'
        self.assertEqual(self.report(self.rows)['posts'][0]['metrics']['shares_per_reach'], 2)

    def test_invalid_rows_fail_instead_of_silent_filtering(self):
        for column, value in [('account', 'other_brand'), ('post_id', 'fictional-2'),
                              ('views', '-1'), ('views', '1.2K'), ('views', '1,200'),
                              ('average_watch_seconds', 'NaN'), ('format', 'video'),
                              ('distribution', ''), ('published_at', '2026-09-01'),
                              ('captured_at', '2026-08-01T12:00:00+03:00'),
                              ('non_follower_reach', '801')]:
            rows = [dict(row) for row in self.rows]
            rows[0][column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                self.report(rows)

    def test_retention_consistency(self):
        self.rows[2]['viewers_3s'] = '2501'
        with self.assertRaises(ValueError):
            self.report(self.rows)

    def test_bad_headers_empty_files_and_extra_cells(self):
        for raw in (b'', b'account,account\nx,x\n', self.raw.replace(b'views,reach', b'unknown,reach'),
                    self.raw + b'extra,row,with,too,few,cells\n',
                    EXAMPLE.with_name('template.csv').read_bytes()):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                audit.analyse(raw, 'ornek_studyo', 'views')

    def test_save_creates_distinct_account_snapshots_and_preserves_results(self):
        with tempfile.TemporaryDirectory() as temp:
            context = audit.accounts.initialize(temp, 'ornek_studyo')
            results = Path(context['paths']['results'])
            results.write_text('Existing audit')
            report = self.report()
            first = audit.save(report, temp)
            second = audit.save(report, temp)
            self.assertNotEqual(first, second)
            self.assertEqual(json.loads((first / 'report.json').read_text()), report)
            self.assertEqual(results.read_text(), 'Existing audit')
            self.assertEqual(first.parent, Path(context['directory']) / 'audits')

    def test_save_refuses_uninitialized_or_symlinked_account_storage(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(ValueError):
                audit.save(self.report(), temp)
            context = audit.accounts.initialize(temp, 'ornek_studyo')
            (Path(context['directory']) / 'audits').symlink_to(temp, target_is_directory=True)
            with self.assertRaises(ValueError):
                audit.save(self.report(), temp)

    def test_cli_stdout_is_read_only_and_reports_errors_without_tracebacks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'absent'
            result = cli('skills/ig-audit/analyse.py', str(EXAMPLE), '--account', 'ornek_studyo',
                         '--primary-metric', 'views', '--root', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['post_count'], 4)
            self.assertFalse(root.exists())
            bad = cli('skills/ig-audit/analyse.py', str(EXAMPLE), '--account', 'wrong', '--primary-metric', 'views')
            self.assertEqual(bad.returncode, 2)
            self.assertNotIn('Traceback', bad.stderr)


if __name__ == '__main__':
    unittest.main()
