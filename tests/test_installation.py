"""Isolated install/update/rollback tests; never use real skill/profile paths."""

import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from test_regressions import ROOT, cli, load


installer = load("installation_tests", "scripts/install.py")


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.target = self.base / "skills"
        # Unit tests focus on filesystem invariants; a separate integration
        # test below executes every installed tool in both languages.
        self.smoke = patch.object(installer, "smoke_check", return_value=13)
        self.smoke.start()
        self.addCleanup(self.smoke.stop)

    def install(self, **kwargs):
        return installer.install(self.target, **kwargs)

    def make_source(self):
        source = self.base / "source"
        shutil.copytree(ROOT / "skills", source / "skills", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        shutil.copytree(ROOT / "templates", source / "templates")
        (source / ".claude-plugin").mkdir()
        shutil.copy2(ROOT / ".claude-plugin/plugin.json", source / ".claude-plugin/plugin.json")
        return source

    def test_dry_run_creates_no_destination(self):
        result = self.install(dry_run=True)
        self.assertEqual(result["status"], "dry-run")
        self.assertFalse(self.target.exists())
        self.assertEqual(result["skills"], 14)

    def test_fresh_install_has_complete_hashes_helpers_and_templates(self):
        result = self.install()
        self.assertEqual(result["smoke_checks"], 13)
        state = json.loads((self.target / installer.MANIFEST).read_text())
        for name, digest in state["files"].items():
            self.assertEqual(installer.digest(self.target / name), digest)
        self.assertTrue((self.target / "ig-account/ig_language.py").is_file())
        self.assertTrue((self.target / "ig-account/assets/templates/voice.md").is_file())
        self.assertTrue((self.target / "ig-account/assets/templates/strategy.md").is_file())

    def test_second_install_requires_explicit_update(self):
        self.install()
        with self.assertRaisesRegex(ValueError, "use --update"):
            self.install()

    def test_check_verifies_without_mutating_installation(self):
        self.install()
        before = {str(p.relative_to(self.target)): p.read_bytes() for p in installer.tree_files(self.target)}
        self.assertEqual(self.install(check=True)["status"], "ok")
        after = {str(p.relative_to(self.target)): p.read_bytes() for p in installer.tree_files(self.target)}
        self.assertEqual(before, after)

    def test_update_keeps_unmanaged_files_and_sibling_account_data(self):
        self.install()
        custom = self.target / "ig-plan/my-notes.txt"
        custom.write_text("KEEP MY NOTES")
        profile = self.base / "instagram/accounts/studio/voice.md"
        profile.parent.mkdir(parents=True)
        profile.write_text("PRIVATE VOICE")
        other_skill = self.target / "unrelated/SKILL.md"
        other_skill.parent.mkdir()
        other_skill.write_text("ANOTHER SKILL")
        result = self.install(update=True)
        self.assertEqual(custom.read_text(), "KEEP MY NOTES")
        self.assertEqual(profile.read_text(), "PRIVATE VOICE")
        self.assertEqual(other_skill.read_text(), "ANOTHER SKILL")
        self.assertEqual((Path(result["backup"]) / "ig-plan/my-notes.txt").read_text(), "KEEP MY NOTES")

    def test_local_edits_are_refused_before_any_replacement(self):
        self.install()
        custom = self.target / "ig-plan/SKILL.md"
        custom.write_text("MY EDITED INSTRUCTIONS")
        with self.assertRaisesRegex(ValueError, "local edits conflict"):
            self.install(update=True)
        self.assertEqual(custom.read_text(), "MY EDITED INSTRUCTIONS")
        self.assertFalse((self.target / installer.BACKUPS).exists())

    def test_explicit_replacement_backs_up_local_edits(self):
        self.install()
        custom = self.target / "ig-plan/SKILL.md"
        custom.write_text("MY EDITED INSTRUCTIONS")
        result = self.install(update=True, replace_existing=True)
        self.assertEqual((Path(result["backup"]) / "ig-plan/SKILL.md").read_text(), "MY EDITED INSTRUCTIONS")
        self.assertEqual(custom.read_bytes(), (ROOT / "skills/ig-plan/SKILL.md").read_bytes())

    def test_unmanaged_copy_requires_explicit_replacement_and_is_backed_up(self):
        folder = self.target / "ig-plan"
        folder.mkdir(parents=True)
        (folder / "SKILL.md").write_text("OLD MANUAL COPY")
        with self.assertRaisesRegex(ValueError, "unmanaged"):
            self.install(update=True)
        result = self.install(update=True, replace_existing=True)
        self.assertEqual((Path(result["backup"]) / "ig-plan/SKILL.md").read_text(), "OLD MANUAL COPY")

    def test_missing_helper_can_be_repaired_by_update(self):
        self.install()
        helper = self.target / "ig-account/ig_language.py"
        helper.unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            self.install(check=True)
        self.install(update=True)
        self.assertTrue(helper.is_file())

    def test_version_changes_are_reported_as_outdated(self):
        source = self.make_source()
        installer.install(self.target, source)
        config = source / ".claude-plugin/plugin.json"
        data = json.loads(config.read_text()); data["version"] = "99.0.0"
        config.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "run --update"):
            installer.install(self.target, source, check=True)

    def test_retired_managed_file_is_removed_but_backed_up(self):
        source = self.make_source()
        old = source / "skills/ig-plan/retired.txt"
        old.write_text("OLD OWNED FILE")
        installer.install(self.target, source)
        old.unlink()
        result = installer.install(self.target, source, update=True)
        self.assertFalse((self.target / "ig-plan/retired.txt").exists())
        self.assertEqual((Path(result["backup"]) / "ig-plan/retired.txt").read_text(), "OLD OWNED FILE")

    def test_smoke_failure_leaves_previous_installation_untouched(self):
        self.install()
        state = (self.target / installer.MANIFEST).read_bytes()
        with patch.object(installer, "smoke_check", side_effect=ValueError("simulated smoke failure")):
            with self.assertRaisesRegex(ValueError, "smoke failure"):
                self.install(update=True)
        self.assertEqual((self.target / installer.MANIFEST).read_bytes(), state)
        self.assertTrue((self.target / "ig-plan/SKILL.md").is_file())
        self.assertFalse(list(self.target.glob(".instagram-agent-stage-*")))

    def test_mid_activation_failure_restores_all_previous_folders(self):
        self.install()
        notes = self.target / "ig-plan/custom.txt"
        notes.write_text("KEEP ME")
        state = (self.target / installer.MANIFEST).read_bytes()
        rename = Path.rename

        def fail_one(path, destination):
            if path.parent.name.startswith(".instagram-agent-stage-") and path.name == "ig-carousel":
                raise OSError("simulated rename failure")
            return rename(path, destination)

        with patch.object(Path, "rename", fail_one):
            with self.assertRaisesRegex(OSError, "rename failure"):
                self.install(update=True)
        self.assertEqual(notes.read_text(), "KEEP ME")
        self.assertEqual((self.target / installer.MANIFEST).read_bytes(), state)
        for name in json.loads(state)["skills"]:
            self.assertTrue((self.target / name / "SKILL.md").is_file())

    def test_symlinked_folder_and_files_are_rejected(self):
        outside = self.base / "outside"
        outside.mkdir()
        self.target.mkdir()
        (self.target / "ig-plan").symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "regular directory"):
            self.install(update=True, replace_existing=True)
        self.assertEqual(list(outside.iterdir()), [])

    def test_manifest_paths_cannot_escape_managed_skill_folders(self):
        self.install()
        path = self.target / installer.MANIFEST
        data = json.loads(path.read_text())
        data["files"]["../outside.txt"] = "a" * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "managed-file path"):
            self.install(update=True)

    def test_source_and_standard_data_directories_are_not_valid_targets(self):
        for target in (ROOT / "skills", ROOT / "skills/nested", Path.home() / ".claude/instagram"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                installer.destination(target)

    def test_incomplete_source_fails_before_creating_destination(self):
        source = self.make_source()
        (source / "skills/ig-account/ig_language.py").unlink()
        with self.assertRaisesRegex(ValueError, "incomplete source"):
            installer.install(self.target, source)
        self.assertFalse(self.target.exists())

    def test_missing_whole_skill_is_rejected_during_preflight(self):
        source = self.make_source()
        shutil.rmtree(source / "skills/ig-caption")
        with self.assertRaisesRegex(ValueError, "incomplete source"):
            installer.install(self.target, source, dry_run=True)
        self.assertFalse(self.target.exists())

    def test_explicit_replacement_can_repair_file_directory_conflict(self):
        self.install()
        path = self.target / "ig-human/slop.json"
        path.unlink(); path.mkdir(); (path / "notes.txt").write_text("KEEP IN BACKUP")
        result = self.install(update=True, replace_existing=True)
        self.assertTrue(path.is_file())
        self.assertEqual((Path(result["backup"]) / "ig-human/slop.json/notes.txt").read_text(), "KEEP IN BACKUP")

    def test_new_parent_directory_never_silently_removes_custom_file(self):
        self.install()
        source = self.make_source()
        new_file = source / "skills/ig-plan/custom/new.txt"
        new_file.parent.mkdir(); new_file.write_text("NEW PACKAGE FILE")
        custom = self.target / "ig-plan/custom"
        custom.write_text("MY CUSTOM FILE")
        with self.assertRaisesRegex(ValueError, "local edits conflict"):
            installer.install(self.target, source, update=True)
        result = installer.install(self.target, source, update=True, replace_existing=True)
        self.assertEqual((custom / "new.txt").read_text(), "NEW PACKAGE FILE")
        self.assertEqual((Path(result["backup"]) / "ig-plan/custom").read_text(), "MY CUSTOM FILE")

    def test_concurrent_installation_lock_prevents_writes_and_checks(self):
        self.target.mkdir()
        lock = self.target / ".instagram-agent-install.lock"
        lock.mkdir()
        for options in ({}, {"dry_run": True}, {"check": True}):
            with self.subTest(options=options), self.assertRaisesRegex(ValueError, "locked"):
                self.install(**options)
        self.assertEqual(list(self.target.iterdir()), [lock])

    def test_failure_releases_lock_for_a_retry(self):
        with patch.object(installer, "smoke_check", side_effect=ValueError("smoke failure")):
            with self.assertRaises(ValueError):
                self.install()
        self.assertFalse((self.target / ".instagram-agent-install.lock").exists())
        self.assertEqual(self.install()["status"], "installed")


class InstalledBundleIntegrationTests(unittest.TestCase):
    def test_real_install_and_check_from_outside_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory) / "skills"
            result = cli("scripts/install.py", "--skills-dir", str(destination), cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["smoke_checks"], 13)
            result = cli("scripts/install.py", "--skills-dir", str(destination), "--check", cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "ok")

    def test_cli_flags_reject_ambiguous_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "skills"
            result = cli("scripts/install.py", "--skills-dir", str(target), "--replace-existing")
            self.assertEqual(result.returncode, 2)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
