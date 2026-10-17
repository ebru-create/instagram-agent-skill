"""Experiment readiness, exact metric comparisons and account-isolated receipts."""
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest

from test_regressions import ROOT, cli, load

experiment = load('content_experiment_tests', 'skills/ig-plan/experiment.py')
PLAN = ROOT / 'skills/ig-plan/example.experiment.tr.json'
CSV = ROOT / 'skills/ig-audit/example.synthetic.csv'
AS_OF = '2026-09-13T12:00:00+03:00'


class ExperimentTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads(PLAN.read_text())
        self.rows = list(csv.DictReader(io.StringIO(CSV.read_text())))

    def raw(self):
        output = io.StringIO(newline='')
        writer = csv.DictWriter(output, fieldnames=list(self.rows[0]))
        writer.writeheader(); writer.writerows(self.rows)
        return output.getvalue().encode()

    def review(self, as_of=AS_OF):
        return experiment.review(self.plan, self.raw(), as_of)

    def test_plan_only_preserves_hypothesis_and_source_identity(self):
        raw = PLAN.read_bytes()
        report = experiment.build(raw, '@ornek_studyo')
        self.assertEqual(report['status'], 'validated_plan')
        self.assertEqual(report['plan']['hypothesis'], self.plan['hypothesis'])
        self.assertEqual(report['plan_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertNotIn('review', report)

    def test_matching_posts_review_rates_not_total_shares(self):
        report = self.review()
        self.assertEqual(report['status'], 'ready_descriptive')
        self.assertEqual(report['groups']['control']['median'], .02)
        self.assertEqual(report['groups']['variant']['median'], .04)
        self.assertEqual(report['variant_minus_control'], .02)
        self.assertTrue(report['minimum_effect_met'])
        self.assertEqual(report['groups']['control']['usable_n'], 1)
        self.assertEqual(report['groups']['control']['observations'][0]['inputs'], {'shares': 16, 'reach': 800})
        self.assertEqual(report['ignored_post_ids'], ['fictional-3', 'fictional-4'])
        self.assertEqual(report['source_sha256'], hashlib.sha256(self.raw()).hexdigest())

    def test_review_date_prevents_early_criterion(self):
        report = self.review('2026-09-11T12:00:00+03:00')
        self.assertEqual(report['status'], 'waiting_for_review')
        self.assertIsNone(report['variant_minus_control'])
        self.assertIsNone(report['minimum_effect_met'])
        self.assertEqual(report['groups']['variant']['usable_n'], 1)

    def test_missing_assigned_post_is_not_silently_dropped(self):
        self.rows.pop(1)
        report = self.review()
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['excluded_assignments'][0]['reason'], 'missing_post')
        self.assertIsNone(report['minimum_effect_met'])

    def test_all_assigned_posts_needed_even_when_minimum_count_is_met(self):
        self.plan['assignments'].append({'post_id': 'not-yet-measured', 'variant': 'control'})
        report = self.review()
        self.assertEqual(report['groups']['control']['usable_n'], 1)
        self.assertEqual(report['status'], 'incomplete')

    def test_incompatible_observations_are_disclosed_and_block_final_comparison(self):
        for field, value, reason in [('format', 'image', 'format_or_distribution_mismatch'),
                                     ('distribution', 'paid', 'format_or_distribution_mismatch'),
                                     ('captured_at', '2026-09-10T12:00:00+03:00', 'observation_window_mismatch'),
                                     ('shares', '', 'primary_metric_unavailable')]:
            with self.subTest(field=field):
                original = self.rows[1][field]
                self.rows[1][field] = value
                report = self.review()
                self.assertEqual(report['status'], 'incomplete')
                self.assertEqual(report['excluded_assignments'][0]['reason'], reason)
                self.assertIsNone(report['variant_minus_control'])
                self.rows[1][field] = original

    def test_future_capture_cannot_be_used_by_historical_review(self):
        self.plan['review_at'] = '2026-09-01T12:00:00+03:00'
        report = self.review('2026-09-08T12:00:00+03:00')
        self.assertEqual(report['status'], 'incomplete')
        self.assertEqual(report['excluded_assignments'][0]['reason'], 'capture_after_as_of')

    def test_zero_denominator_is_unavailable_but_observed_zero_is_valid(self):
        self.rows[1].update(reach='0', non_follower_reach='0')
        self.assertEqual(self.review()['status'], 'incomplete')
        self.rows[1].update(reach='1000', shares='0')
        report = self.review()
        self.assertEqual(report['status'], 'ready_descriptive')
        self.assertEqual(report['groups']['variant']['median'], 0)
        self.assertFalse(report['minimum_effect_met'])

    def test_exact_rate_threshold_does_not_fail_due_to_float_rounding(self):
        self.rows[0].update(shares='30', reach='1000')
        self.assertTrue(self.review()['minimum_effect_met'])  # .04 - .03 >= .01
        self.rows[1]['shares'] = '39'
        self.assertFalse(self.review()['minimum_effect_met'])

    def test_lower_direction_and_count_metric(self):
        self.plan.update(primary_metric='views', direction='lower', minimum_effect=500)
        self.rows[1]['views'] = '500'
        report = self.review()
        self.assertEqual(report['variant_minus_control'], -500)
        self.assertTrue(report['minimum_effect_met'])

    def test_medians_are_per_post_not_pooled_rates(self):
        extra = dict(self.rows[0], post_id='fictional-5', reach='10000', shares='0')
        self.rows.append(extra)
        self.plan['assignments'].append({'post_id': 'fictional-5', 'variant': 'control'})
        report = self.review()
        self.assertEqual(report['groups']['control']['median'], .01)
        self.assertEqual(report['groups']['control']['usable_n'], 2)

    def test_malformed_or_ambiguous_plans_are_rejected(self):
        for key, value in [('schema_version', True), ('account', 'other'), ('experiment_id', '../bad'),
                           ('direction', 'best'), ('primary_metric', 'sales_rate'),
                           ('minimum_effect', True), ('minimum_effect', 0), ('minimum_effect', float('nan')),
                           ('observation_hours', -1), ('min_posts_per_variant', 0),
                           ('review_at', '2026-09-12'), ('distribution', 'unknown'),
                           ('held_similar', []), ('confounders', ['']), ('hypothesis', '')]:
            plan = copy.deepcopy(self.plan); plan[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                experiment.validate(plan, 'ornek_studyo')
        self.plan['assignments'][1]['post_id'] = 'fictional-1'
        with self.assertRaises(ValueError):
            experiment.validate(self.plan, 'ornek_studyo')

    def test_prospective_plan_needs_no_invented_post_ids_and_target_is_enforced(self):
        self.plan['assignments'] = []
        report = experiment.build(json.dumps(self.plan).encode(), 'ornek_studyo')
        self.assertEqual(report['status'], 'validated_plan')
        self.assertEqual(self.review()['status'], 'incomplete')
        self.plan = json.loads(PLAN.read_text())
        self.plan['min_posts_per_variant'] = 2
        self.assertEqual(self.review()['status'], 'incomplete')

    def test_unknown_plan_fields_and_duplicate_json_keys_fail(self):
        raw = PLAN.read_bytes().replace(b'"schema_version": 1,', b'"schema_version": 1, "schema_version": 1,')
        with self.assertRaises(ValueError):
            experiment.build(raw, 'ornek_studyo')
        self.plan['typo'] = 1
        with self.assertRaises(ValueError):
            experiment.validate(self.plan, 'ornek_studyo')

    def test_csv_account_mismatch_and_duplicate_post_fail_whole_review(self):
        self.rows[0]['account'] = 'other'
        with self.assertRaises(ValueError):
            self.review()
        self.rows[0]['account'] = 'ornek_studyo'
        self.rows.append(dict(self.rows[0]))
        with self.assertRaises(ValueError):
            self.review()

    def test_save_preserves_previous_snapshots_and_plan_and_results(self):
        with tempfile.TemporaryDirectory() as root:
            context = experiment.audit.accounts.initialize(root, 'ornek_studyo')
            for field in ('plan', 'results'):
                Path(context['paths'][field]).write_text('KEEP')
            report = experiment.build(PLAN.read_bytes(), 'ornek_studyo', CSV.read_bytes(), AS_OF)
            first = experiment.save(report, root)
            first_bytes = (first / 'report.json').read_bytes()
            second = experiment.save(report, root)
            self.assertNotEqual(first, second)
            self.assertEqual((first / 'report.json').read_bytes(), first_bytes)
            saved = json.loads(first_bytes)
            self.assertEqual(saved['plan_sha256'], report['plan_sha256'])
            self.assertIn('saved_at', saved)
            self.assertEqual(first.parent, Path(context['directory']) / 'experiments')
            for field in ('plan', 'results'):
                self.assertEqual(Path(context['paths'][field]).read_text(), 'KEEP')

    def test_save_requires_initialized_account_and_refuses_symlinks(self):
        with tempfile.TemporaryDirectory() as root:
            report = experiment.build(PLAN.read_bytes(), 'ornek_studyo')
            with self.assertRaises(ValueError):
                experiment.save(report, root)
            context = experiment.audit.accounts.initialize(root, 'ornek_studyo')
            (Path(context['directory']) / 'experiments').symlink_to(root, target_is_directory=True)
            with self.assertRaises(ValueError):
                experiment.save(report, root)

    def test_cli_is_read_only_without_save(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'absent'
            result = cli('skills/ig-plan/experiment.py', str(PLAN), '--account', 'ornek_studyo',
                         '--csv', str(CSV), '--as-of', AS_OF, '--root', str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'ready_descriptive')
            self.assertFalse(root.exists())

    def test_cli_missing_inputs_and_invalid_csv_give_actionable_errors(self):
        result = cli('skills/ig-plan/experiment.py', str(PLAN), '--account', 'wrong')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)
        with self.assertRaises(ValueError):
            experiment.build(PLAN.read_bytes(), 'ornek_studyo', as_of=AS_OF)
        with tempfile.TemporaryDirectory() as temp:
            bad_csv = Path(temp) / 'bad.csv'; bad_csv.write_text('"unterminated')
            result = cli('skills/ig-plan/experiment.py', str(PLAN), '--account', 'ornek_studyo', '--csv', str(bad_csv))
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
