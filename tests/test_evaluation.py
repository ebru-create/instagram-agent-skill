"""Independent metric examples and end-to-end evaluation provenance checks."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from test_regressions import ROOT, cli, load


evaluation = load("evaluation_tests", "evaluation/evaluate.py")
FIXTURE_PATH = ROOT / "evaluation/fixtures.json"


class MetricTests(unittest.TestCase):
    def test_auc_perfect_reversed_and_all_ties(self):
        self.assertEqual(evaluation.roc_auc([0, 1, 0, 1], [0, 1, 0, 1]), 1)
        self.assertEqual(evaluation.roc_auc([0, 1, 0, 1], [1, 0, 1, 0]), 0)
        self.assertEqual(evaluation.roc_auc([0, 1, 0, 1], [2, 2, 2, 2]), .5)

    def test_auc_partial_tie_gets_half_credit(self):
        # Positive .8 beats .2 and ties .8: (1 + .5) / 2 = .75.
        self.assertEqual(evaluation.roc_auc([0, 0, 1], [.2, .8, .8]), .75)

    def test_auc_is_undefined_without_both_classes(self):
        for labels, scores in [([], []), ([1], [1]), ([0, 0], [1, 2])]:
            self.assertIsNone(evaluation.roc_auc(labels, scores))

    def test_invalid_metric_inputs_are_rejected(self):
        for labels, scores in [([1], []), ([True, 0], [1, 0]), ([2, 0], [1, 0]),
                               ([1, 0], [float("nan"), 0]), ([1, 0], [1, float("inf")])]:
            with self.subTest(labels=labels, scores=scores), self.assertRaises(ValueError):
                evaluation.roc_auc(labels, scores)

    def row(self, account, label, score, predicted=None, **extra):
        return dict(account=account, label=label, score=score, predicted_formula=predicted, **extra)

    def test_within_account_and_pooled_auc_are_distinct(self):
        rows = [self.row("a", 1, .4), self.row("a", 0, .3),
                self.row("b", 1, .2), self.row("b", 0, .1)]
        report = evaluation.summarize(rows)
        self.assertEqual(report["pooled_auc"], .75)
        self.assertEqual(report["within_account_macro_auc"], 1)
        self.assertEqual(report["evaluable_accounts"], 2)

    def test_single_class_accounts_are_excluded_from_macro(self):
        report = evaluation.summarize([self.row("a", 1, .4), self.row("a", 0, .3),
                                       self.row("b", 1, .2)])
        self.assertEqual(report["within_account_macro_auc"], 1)
        self.assertEqual(report["evaluable_accounts"], 1)
        self.assertEqual(report["total_accounts"], 2)
        self.assertIsNone(report["by_account"][1]["auc"])

    def test_coverage_does_not_equal_annotation_agreement(self):
        rows = [self.row("a", 1, .4, None, expected_formula=None),
                self.row("a", 0, .3, 2, expected_formula=1),
                self.row("a", 1, .2, 1)]
        stats = evaluation.summarize(rows)["classification"]
        self.assertAlmostEqual(stats["coverage"], 2 / 3)
        self.assertEqual(stats["annotated_n"], 2)
        self.assertEqual(stats["exact_annotation_agreement"], .5)
        self.assertEqual(stats["classified_annotated_n"], 1)
        self.assertEqual(stats["agreement_when_classified"], 0)

    def test_no_annotations_produces_null_not_zero_accuracy(self):
        stats = evaluation.summarize([self.row("a", 1, .4)])["classification"]
        self.assertEqual(stats["coverage"], 0)
        self.assertIsNone(stats["exact_annotation_agreement"])
        self.assertIsNone(stats["agreement_when_classified"])


class DatasetTests(unittest.TestCase):
    def setUp(self):
        self.dataset = json.loads(FIXTURE_PATH.read_bytes())
        self.ids = {"en": set(range(1, 27)), "tr": {1, 2, 3, 5, 9, 16}}

    def test_duplicate_ids_and_hook_rows_are_rejected(self):
        for field in ("id", "hook"):
            dataset = copy.deepcopy(self.dataset)
            dataset["rows"][1][field] = dataset["rows"][0][field]
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "duplicate"):
                evaluation.validate(dataset, self.ids)

    def test_labels_languages_and_formula_annotations_are_validated(self):
        for key, value in [("label", True), ("label", "1"), ("language", "auto"),
                           ("expected_formula", 999), ("expected_formula", True)]:
            dataset = copy.deepcopy(self.dataset)
            dataset["rows"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                evaluation.validate(dataset, self.ids)

    def test_observational_data_needs_source_and_capture_date(self):
        self.dataset["metadata"]["kind"] = "observational"
        with self.assertRaisesRegex(ValueError, "source"):
            evaluation.validate(self.dataset, self.ids)
        self.dataset["rows"][0]["source"] = "owner-supplied post reference"
        with self.assertRaisesRegex(ValueError, "observed_at"):
            evaluation.validate(self.dataset, self.ids)

    def test_observational_dates_are_checked_without_rejecting_owned_sources(self):
        self.dataset["metadata"]["kind"] = "observational"
        for row in self.dataset["rows"]:
            row.update(source="owner-supplied reference", observed_at="2026-10-17")
        evaluation.validate(self.dataset, self.ids)
        self.dataset["rows"][0]["observed_at"] = "yesterday"
        with self.assertRaisesRegex(ValueError, "ISO date"):
            evaluation.validate(self.dataset, self.ids)

    def test_language_reports_and_provenance_are_reproducible(self):
        raw = FIXTURE_PATH.read_bytes()
        first = evaluation.evaluate(self.dataset, raw)
        self.assertEqual(first, evaluation.evaluate(self.dataset, raw))
        self.assertEqual(first["reproducibility"]["dataset_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(set(first["by_language"]), {"en", "tr"})
        self.assertEqual(first["by_language"]["en"]["n"], 6)
        self.assertEqual(first["by_language"]["tr"]["n"], 6)
        for path, digest in first["reproducibility"]["source_sha256"].items():
            self.assertEqual(digest, hashlib.sha256((ROOT / path).read_bytes()).hexdigest())
        self.assertFalse(any("hook" in row for row in first["scored_rows"]))

    def test_account_case_variants_share_one_group(self):
        self.dataset["rows"][1]["account"] = self.dataset["rows"][0]["account"].upper()
        result = evaluation.evaluate(self.dataset, json.dumps(self.dataset).encode())
        self.assertEqual(result["by_language"]["en"]["total_accounts"], 2)

    def test_cli_creates_report_and_never_overwrites_input(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "nested" / "report.json"
            result = cli("evaluation/evaluate.py", str(FIXTURE_PATH), "--out", str(output))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(output.read_text())["metadata"]["kind"], "fixture")
            original = output.read_bytes()
            result = cli("evaluation/evaluate.py", str(output), "--out", str(output))
            self.assertEqual(result.returncode, 2)
            self.assertEqual(output.read_bytes(), original)

    def test_invalid_json_has_actionable_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "bad.json"
            source.write_text("{broken}")
            result = cli("evaluation/evaluate.py", str(source))
            self.assertEqual(result.returncode, 2)
            self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
