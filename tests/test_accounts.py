"""Account routing tested with temporary data, never the user's profiles."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from test_regressions import cli, load


accounts = load("ig_accounts", "skills/ig-account/account.py")


class AccountTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "data"

    def test_legacy_resolution_is_read_only(self):
        result = accounts.resolve(self.root)
        self.assertEqual(result["mode"], "legacy")
        self.assertEqual(Path(result["paths"]["voice"]), self.root / "voice.md")
        self.assertFalse(self.root.exists())

    def test_initialization_normalizes_handle_and_does_not_import_legacy(self):
        self.root.mkdir()
        legacy = self.root / "voice.md"
        legacy.write_text("LEGACY VOICE", encoding="utf-8")
        result = accounts.initialize(self.root, " @Studio_One ")
        self.assertEqual(result["account"], "studio_one")
        self.assertEqual(Path(result["directory"]), self.root / "accounts" / "studio_one")
        self.assertFalse(Path(result["paths"]["voice"]).exists())
        self.assertEqual(legacy.read_text(), "LEGACY VOICE")

    def test_reinitialization_preserves_existing_content(self):
        first = accounts.initialize(self.root, "studio_one")
        voice = Path(first["paths"]["voice"])
        voice.write_text("MY OWN VOICE", encoding="utf-8")
        self.assertEqual(first, accounts.initialize(self.root, "@STUDIO_ONE"))
        self.assertEqual(voice.read_text(), "MY OWN VOICE")

    def test_no_implicit_selection_even_for_one_account(self):
        accounts.initialize(self.root, "studio_one")
        with self.assertRaisesRegex(ValueError, "choose the publishing account"):
            accounts.resolve(self.root)

    def test_two_conversations_resolve_independently(self):
        a = accounts.initialize(self.root, "studio_one")
        b = accounts.initialize(self.root, "studio_two")
        for key in accounts.FILES:
            Path(a["paths"][key]).write_text("ACCOUNT A", encoding="utf-8")
            Path(b["paths"][key]).write_text("ACCOUNT B", encoding="utf-8")
        # Interleaved calls do not mutate a shared current-account setting.
        for handle, expected in [("studio_two", "ACCOUNT B"), ("studio_one", "ACCOUNT A"),
                                 ("studio_two", "ACCOUNT B")]:
            result = accounts.resolve(self.root, handle)
            for path in result["paths"].values():
                self.assertEqual(Path(path).read_text(), expected)
        self.assertEqual(accounts.list_accounts(self.root), ["studio_one", "studio_two"])
        self.assertFalse((self.root / "active.json").exists())

    def test_missing_file_never_falls_back(self):
        a = accounts.initialize(self.root, "studio_one")
        b = accounts.initialize(self.root, "studio_two")
        Path(a["paths"]["voice"]).write_text("OTHER BRAND", encoding="utf-8")
        (self.root / "voice.md").write_text("LEGACY", encoding="utf-8")
        result = accounts.resolve(self.root, "studio_two")
        self.assertEqual(result, b)
        self.assertFalse(Path(result["paths"]["voice"]).exists())
        with self.assertRaisesRegex(ValueError, "unknown account"):
            accounts.resolve(self.root, "studio_three")
        self.assertFalse((self.root / "accounts" / "studio_three").exists())

    def test_invalid_handles_cannot_escape_root(self):
        for handle in ("..", ".", "../other", "a/b", "a\\b", "@", "@@a", "a b", "a" * 31):
            with self.subTest(handle=handle), self.assertRaises(ValueError):
                accounts.initialize(self.root, handle)
        self.assertFalse(self.root.exists())

    def test_account_and_file_symlinks_are_rejected(self):
        a = accounts.initialize(self.root, "studio_one")
        b = accounts.initialize(self.root, "studio_two")
        (self.root / "accounts" / "alias").symlink_to(a["directory"], target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "symbolic link"):
            accounts.resolve(self.root, "alias")
        Path(b["paths"]["voice"]).symlink_to(a["paths"]["voice"])
        with self.assertRaisesRegex(ValueError, "regular file"):
            accounts.resolve(self.root, "studio_two")

    def test_helper_cli_outputs_paths_and_lists_without_reading_context(self):
        result = cli("skills/ig-account/account.py", "--root", str(self.root), "init", "@A")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["account"], "a")
        result = cli("skills/ig-account/account.py", "--root", str(self.root), "show")
        self.assertEqual(result.returncode, 2)
        result = cli("skills/ig-account/account.py", "--root", str(self.root), "list")
        self.assertEqual(json.loads(result.stdout), {"accounts": ["a"]})


class AccountResearchTests(unittest.TestCase):
    DATA = "account\tfollowers\tmedian\tviews\thook\n@competitor\t1K\t100\t1.2M\tI saved three hours\n"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / "data"

    def test_research_saves_only_to_selected_publishing_account(self):
        a = accounts.initialize(self.root, "studio_one")
        b = accounts.initialize(self.root, "studio_two")
        Path(b["paths"]["swipe"]).write_text("KEEP BRAND B", encoding="utf-8")
        (self.root / "swipe.md").write_text("KEEP LEGACY", encoding="utf-8")
        result = cli("skills/ig-viral/swipe.py", "--account", "@STUDIO_ONE",
                     "--data-root", str(self.root), "--json", text=self.DATA)
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["owner_account"], "studio_one")
        self.assertEqual(report["reels"][0]["account"], "@competitor")
        self.assertIn("Publishing account: @studio_one", Path(a["paths"]["swipe"]).read_text())
        self.assertEqual(Path(b["paths"]["swipe"]).read_text(), "KEEP BRAND B")
        self.assertEqual((self.root / "swipe.md").read_text(), "KEEP LEGACY")

    def test_unknown_account_fails_without_creating_data(self):
        result = cli("skills/ig-viral/swipe.py", "--account", "unknown",
                     "--data-root", str(self.root), text=self.DATA)
        self.assertEqual(result.returncode, 2)
        self.assertIn("unknown account", result.stderr)
        self.assertFalse(self.root.exists())

    def test_explicit_output_cannot_override_account_destination(self):
        result = cli("skills/ig-viral/swipe.py", "--account", "studio_one", "--out", "other.md",
                     text=self.DATA)
        self.assertEqual(result.returncode, 2)
        self.assertIn("not allowed with argument", result.stderr)

    def test_custom_root_cannot_silently_affect_legacy_output(self):
        result = cli("skills/ig-viral/swipe.py", "--data-root", str(self.root), text=self.DATA)
        self.assertEqual(result.returncode, 2)
        self.assertIn("--data-root requires --account", result.stderr)

    def test_symlink_output_cannot_overwrite_another_account(self):
        a = accounts.initialize(self.root, "studio_one")
        b = accounts.initialize(self.root, "studio_two")
        Path(b["paths"]["swipe"]).write_text("KEEP BRAND B", encoding="utf-8")
        Path(a["paths"]["swipe"]).symlink_to(b["paths"]["swipe"])
        result = cli("skills/ig-viral/swipe.py", "--account", "studio_one",
                     "--data-root", str(self.root), text=self.DATA)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(Path(b["paths"]["swipe"]).read_text(), "KEEP BRAND B")

    def test_installed_folder_layout_works_without_repository_templates(self):
        from test_regressions import ROOT
        destination = Path(self.temp.name) / "installed"
        for name in ("ig-account", "ig-reel", "ig-viral"):
            shutil.copytree(ROOT / "skills" / name, destination / name)
        import subprocess
        import sys
        helper = destination / "ig-account" / "account.py"
        setup = subprocess.run([sys.executable, str(helper), "--root", str(self.root),
                                "init", "studio_one"], capture_output=True, text=True)
        self.assertEqual(setup.returncode, 0, setup.stderr)
        result = subprocess.run([sys.executable, str(destination / "ig-viral" / "swipe.py"),
                                 "--account", "studio_one", "--data-root", str(self.root)],
                                input=self.DATA, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Publishing account: @studio_one", result.stdout)


if __name__ == "__main__":
    unittest.main()
