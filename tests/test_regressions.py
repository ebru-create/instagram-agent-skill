"""Behavioral regressions for the local tools; no services or dependencies."""

import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


detect = load("detect", "skills/ig-human/detect.py")
humanize = load("humanize", "skills/ig-human/humanize.py")
swipe = load("swipe", "skills/ig-viral/swipe.py")
LEX = humanize.load_lexicon()


def cli(relative, *args, text="", cwd=None):
    return subprocess.run([sys.executable, str(ROOT / relative), *args],
                          input=text, text=True, capture_output=True, cwd=cwd)


class ShortTextTests(unittest.TestCase):
    def test_clean_short_copy_can_pass_without_padding(self):
        text = "I made this for you. Save it for your next workshop."
        checks, score, verdict = detect.run(text, LEX)
        self.assertEqual(verdict, "PASS")
        self.assertEqual(score, 100)
        for name in ("BURSTINESS", "SPECIFICITY", "VOICE"):
            self.assertIsNone(checks[name][0])

    def test_short_copy_still_flags_stock_vocabulary(self):
        _, _, verdict = detect.run("Leverage robust seamless solutions.", LEX)
        self.assertEqual(verdict, "FLAGGED")

    def test_empty_and_emoji_only_have_no_score(self):
        for text in ("", " \n", "👩‍💻"):
            with self.subTest(text=text):
                checks, score, verdict = detect.run(text, LEX)
                self.assertIsNone(score)
                self.assertEqual(verdict, "INSUFFICIENT TEXT")
                self.assertTrue(all(v[0] is None for v in checks.values()))

    def test_json_exposes_coverage_and_nulls(self):
        result = cli("skills/ig-human/detect.py", "--json", text="I made this for you.")
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["applicable_checks"], 2)
        self.assertIsNone(report["checks"]["VOICE"]["score"])
        self.assertEqual(report["verdict"], "PASS")

    def test_empty_cli_and_comparison_render_without_crashing(self):
        result = cli("skills/ig-human/detect.py")
        self.assertEqual(result.returncode, 1)
        self.assertIn("INSUFFICIENT TEXT", result.stdout)
        self.assertIn("N/A", result.stdout)
        with tempfile.TemporaryDirectory() as directory:
            before = Path(directory) / "before.txt"
            after = Path(directory) / "after.txt"
            before.write_text("")
            after.write_text("I made this for you.")
            result = cli("skills/ig-human/detect.py", str(before), str(after))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Score delta unavailable", result.stdout)

    def test_long_text_keeps_all_five_checks(self):
        text = ("I saved $200 on my first project. You can use my checklist today. "
                "I've tried three tools and I think you'll like this one. "
                "It's the one I use every week with my team in London.")
        checks, score, _ = detect.run(text, LEX)
        self.assertTrue(all(v[0] is not None for v in checks.values()))
        scores = [v[0] for v in checks.values()]
        self.assertAlmostEqual(score, sum(scores) / 5 * .6 + min(scores) * .4)


class UnicodeTests(unittest.TestCase):
    def test_meaningful_unicode_survives_cleaning(self):
        samples = ["Our team 👩‍💻 builds tools.", "Family: 👨‍👩‍👧‍👦",
                   "می\u200cروم", "क्\u200dष", "\u061cمرحبا\u200f",
                   "\u2067مرحبا\u2069", "ᠠ\u180eᠢ",
                   "Flag: 🏴\U000e0067\U000e0062\U000e0065\U000e006e\U000e0067\U000e007f"]
        for text in samples:
            with self.subTest(text=text):
                clean, report = humanize.humanize(text, LEX)
                self.assertEqual(clean, text + "\n")
                self.assertEqual(report["invisible"], [])

    def test_known_cleanup_candidates_are_still_removed(self):
        clean, _ = humanize.humanize("\ufeffZero\u200b waste\u00a0today\u00ad.", LEX)
        self.assertEqual(clean, "Zero waste today.\n")

    def test_semantic_characters_do_not_lower_fingerprint_score(self):
        for text in ("Team 👩‍💻", "Family 👨‍👩‍👧‍👦", "\u200fمرحبا"):
            with self.subTest(text=text):
                self.assertEqual(detect.check_fingerprint(text)[0], 100)

    def test_typography_can_be_preserved_in_both_tools(self):
        text = "I’m here — “hello”…"
        clean, report = humanize.humanize(text, LEX, preserve_typography=True)
        self.assertEqual(clean, text + "\n")
        self.assertEqual(report["typographic"], [])
        self.assertEqual(detect.check_fingerprint(text, preserve_typography=True)[0], 100)
        default, _ = humanize.humanize(text, LEX)
        self.assertNotIn("—", default)
        self.assertNotIn("“", default)
        self.assertLess(detect.check_fingerprint(text)[0], 100)

    def test_preserve_typography_cli_and_urls(self):
        text = "I’m here — https://example.com/leverage?q=robust"
        result = cli("skills/ig-human/humanize.py", "--preserve-typography", text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, text + "\n")
        result = cli("skills/ig-human/detect.py", "--preserve-typography", "--json", text=text)
        self.assertEqual(json.loads(result.stdout)["checks"]["FINGERPRINT"]["score"], 100)


class ResearchTests(unittest.TestCase):
    def test_counts_keep_their_magnitude(self):
        for text, expected in [("1.2M", 1200000), ("1.2k", 1200), ("2B", 2000000000),
                               ("1,234,567", 1234567), (" 12 K ", 12000),
                               ("0", 0), ("", None), ("0.125K", 125)]:
            with self.subTest(text=text):
                self.assertEqual(swipe.parse_count(text), expected)

    def test_ambiguous_or_invalid_counts_are_rejected(self):
        for text in ("1,2M", "1.234.567", "1.2", "-5", "NaN", "12 views", "1.0001K"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                swipe.parse_count(text)

    def test_all_count_columns_are_parsed_and_zero_views_retained(self):
        result = cli("skills/ig-viral/swipe.py", "--json", text=(
            "account\tfollowers\tmedian\tviews\thook\n"
            "@a\t1.2K\t2K\t1.2M\tI saved you three hours\n"
            "@b\t1,000\t100\t0\tMy first attempt failed\n"))
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)["reels"]
        self.assertEqual(len(rows), 2)
        self.assertEqual((rows[0]["views"], rows[0]["median"], rows[0]["followers"]),
                         (1200000, 2000, 1200))
        self.assertEqual(rows[1]["outlier"], 0)

    def test_invalid_input_reports_row_and_field(self):
        result = cli("skills/ig-viral/swipe.py", "--json", text=(
            "account\tviews\thook\n@a\t1,2M\tA hook\n"))
        self.assertEqual(result.returncode, 2)
        self.assertIn("row 2, views", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_mixed_baselines_have_independent_ranks_and_summaries(self):
        rows = [dict(account="@median", views=1000, median=100, followers=10000, hook="I saved three hours"),
                dict(account="@proxy", views=100000, median=None, followers=100, hook="My first mistake"),
                dict(account="@missing", views=500, median=None, followers=None, hook="A story"),
                dict(account="@median2", views=100, median=100, followers=10000, hook="A second story")]
        result = swipe.analyse(rows, swipe.load_formulas(swipe.HOOKS))
        self.assertEqual(result["baseline"], "mixed (ranked separately)")
        groups = result["groups"]
        self.assertEqual([g["baseline"] for g in groups],
                         ["account median", "follower count", "unavailable"])
        self.assertEqual([r["account"] for r in groups[0]["reels"]], ["@median", "@median2"])
        self.assertEqual(groups[0]["top_words"], 4)
        self.assertEqual(groups[1]["top_formulas"], [])
        self.assertIsNone(groups[2]["reels"][0]["outlier"])
        self.assertEqual(groups[2]["top_formulas"], [])
        output = io.StringIO()
        swipe.render(result, output)
        self.assertIn("baseline: follower count", output.getvalue())
        self.assertIn("proxy", output.getvalue())
        markdown = swipe.to_markdown(result)
        self.assertIn("## Baseline: account median", markdown)
        self.assertIn("## Baseline: follower count", markdown)
        self.assertIn("## Baseline: unavailable", markdown)

    def test_zero_baselines_do_not_divide_by_zero(self):
        result = swipe.analyse([dict(account="@a", views=1, median=0, followers=0, hook="A hook")], None)
        self.assertIsNone(result["reels"][0]["outlier"])
        self.assertEqual(result["reels"][0]["baseline_type"], "unavailable")

    def test_markdown_can_be_written_to_current_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            result = cli("skills/ig-viral/swipe.py", "--out", "swipe.md", cwd=directory,
                         text="account\tfollowers\tviews\thook\n@a\t1K\t1.2M\tI saved three hours\n")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("1,200,000", (Path(directory) / "swipe.md").read_text())


if __name__ == "__main__":
    unittest.main()
