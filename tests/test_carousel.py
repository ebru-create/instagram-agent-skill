"""PNG export checks with real fonts; no account data or platform uploads."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_regressions import ROOT, cli, load


renderer = load("carousel_renderer_tests", "skills/ig-carousel/render.py")
EXAMPLE = ROOT / "skills/ig-carousel/example.tr.json"
FONT = next((path for path in [os.environ.get("CAROUSEL_TEST_FONT", ""),
                             "/System/Library/Fonts/Supplemental/Arial.ttf",
                             "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"] if path and Path(path).is_file()), None)
HAS_PILLOW = importlib.util.find_spec("PIL") is not None


class CarouselSchemaTests(unittest.TestCase):
    def setUp(self):
        self.job = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_theme_needs_readable_contrast(self):
        self.job["theme"]["text"] = self.job["theme"]["background"]
        with self.assertRaisesRegex(ValueError, "contrast"):
            renderer.validate(self.job)

    def test_each_slide_needs_alt_text(self):
        del self.job["slides"][1]["alt_text"]
        with self.assertRaisesRegex(ValueError, "alt_text"):
            renderer.validate(self.job)

    def test_slide_count_and_publishing_handle_are_validated(self):
        for key, value in [("slides", []), ("slides", self.job["slides"] * 6),
                            ("account", "../another"), ("language", "auto")]:
            job = copy.deepcopy(self.job); job[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                renderer.validate(job)

    def test_hidden_controls_and_unsupported_scripts_are_rejected_for_drawn_text(self):
        for title in ("İş\x00", "İş\u200d", "مرحبا"):
            self.job["slides"][0]["title"] = title
            with self.subTest(title=title), self.assertRaises(ValueError):
                renderer.validate(self.job)

    def test_emoji_in_caption_metadata_is_preserved(self):
        self.job["caption"] = "Ekibimiz 👩‍💻"
        self.assertEqual(renderer.validate(self.job)["caption"], self.job["caption"])

    def test_missing_glyph_is_rejected_instead_of_silent_tofu(self):
        class Mask:
            size = (1, 1)
            def __bytes__(self):
                return b"\x00"
        class NoGlyphs:
            def getmask(self, char):
                return Mask()
        with self.assertRaisesRegex(ValueError, "no glyph"):
            renderer.glyphs_available("Ş", NoGlyphs(), "title")

    def test_optional_dependency_failure_is_actionable(self):
        # -S disables site packages without uninstalling the user's packages.
        result = subprocess.run([sys.executable, "-S", str(ROOT / "skills/ig-carousel/render.py"),
                                 str(EXAMPLE), "--font", FONT or "not-used.ttf", "--check"],
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("optional Pillow", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


@unittest.skipUnless(HAS_PILLOW and FONT, "optional PNG tests need Pillow and a Latin/Turkish TrueType font")
class CarouselRenderingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.job = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_output_has_numbered_rgb_pngs_alt_text_and_correct_dimensions(self):
        from PIL import Image
        output = self.base / "export"
        report = renderer.export(self.job, FONT, output=output, source_bytes=EXAMPLE.read_bytes())
        self.assertEqual(report["status"], "exported")
        self.assertEqual([row["file"] for row in report["slides"]], ["01.png", "02.png", "03.png", "04.png"])
        self.assertEqual(report["account"], "ornek_studyo")
        self.assertEqual(report["source_sha256"], hashlib.sha256(EXAMPLE.read_bytes()).hexdigest())
        for row, original in zip(report["slides"], self.job["slides"]):
            with Image.open(output / row["file"]) as image:
                self.assertEqual(image.size, (1080, 1350))
                self.assertEqual(image.mode, "RGB")
            self.assertEqual(row["alt_text"], original["alt_text"])
            self.assertEqual(row["sha256"], hashlib.sha256((output / row["file"]).read_bytes()).hexdigest())
        self.assertEqual(json.loads((output / "manifest.json").read_text()), report)
        self.assertEqual((output / "caption.txt").read_text().strip(), self.job["caption"])
        self.assertTrue((output / "review/overview.png").is_file())

    def test_check_does_not_create_output(self):
        report = renderer.export(self.job, FONT)
        self.assertEqual(report["status"], "checked")
        self.assertEqual(report["slide_count"], 4)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_render_is_repeatable_with_same_fonts_and_environment(self):
        a = renderer.export(self.job, FONT, output=self.base / "a")
        b = renderer.export(self.job, FONT, output=self.base / "b")
        self.assertEqual(a, b)

    def test_overflow_on_a_later_slide_leaves_no_partial_export(self):
        self.job["slides"][2]["body"] = "Uzun metin " * 120
        output = self.base / "nested" / "export"
        with self.assertRaisesRegex(ValueError, "overflows"):
            renderer.export(self.job, FONT, output=output)
        self.assertFalse(output.parent.exists())

    def test_unbroken_words_are_not_clipped(self):
        self.job["slides"][0]["title"] = "W" * 100
        with self.assertRaisesRegex(ValueError, "unbroken word"):
            renderer.export(self.job, FONT)

    def test_old_exports_and_account_files_are_never_overwritten(self):
        output = self.base / "existing"
        output.mkdir(); (output / "voice.md").write_text("KEEP MY PROFILE")
        with self.assertRaisesRegex(ValueError, "never overwritten"):
            renderer.export(self.job, FONT, output=output)
        self.assertEqual((output / "voice.md").read_text(), "KEEP MY PROFILE")

    def test_failed_image_save_cleans_staging(self):
        from PIL import Image
        output = self.base / "export"
        with patch.object(Image.Image, "save", side_effect=OSError("simulated save error")):
            with self.assertRaisesRegex(OSError, "save error"):
                renderer.export(self.job, FONT, output=output)
        self.assertEqual(list(self.base.iterdir()), [])

    def test_missing_font_is_an_error_without_output(self):
        with self.assertRaisesRegex(ValueError, "font"):
            renderer.export(self.job, self.base / "missing.ttf", output=self.base / "export")
        self.assertEqual(list(self.base.iterdir()), [])

    def test_english_job_keeps_language_and_copy(self):
        self.job["language"] = "en"
        self.job["slides"] = [dict(title="Three useful questions", body="Start with the purpose.",
                                    alt_text="Text card about purpose.") for _ in range(2)]
        self.assertEqual(renderer.export(self.job, FONT)["language"], "en")

    def test_cli_checks_layout(self):
        result = cli("skills/ig-carousel/render.py", str(EXAMPLE), "--font", FONT, "--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["slide_count"], 4)

    def test_installed_exporter_works_without_repository_context(self):
        destination = self.base / "skills"
        result = cli("scripts/install.py", "--skills-dir", str(destination), cwd=self.base)
        self.assertEqual(result.returncode, 0, result.stderr)
        script = destination / "ig-carousel/render.py"
        example = destination / "ig-carousel/example.tr.json"
        result = subprocess.run([sys.executable, str(script), str(example), "--font", FONT, "--check"],
                                cwd=self.base, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
