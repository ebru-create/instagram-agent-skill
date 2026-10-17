"""Distribution integrity and installation from an isolated source ZIP."""
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from test_regressions import ROOT, cli, load

release = load('release_package_tests', 'scripts/package_release.py')


@unittest.skipUnless(shutil.which('git'), 'release source selection requires Git')
class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base / 'source'; self.source.mkdir()
        for name in release.ROOT_FILES:
            if (ROOT / name).is_file():
                shutil.copy2(ROOT / name, self.source / name)
        for name in release.DIRECTORIES:
            if (ROOT / name).is_dir():
                shutil.copytree(ROOT / name, self.source / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        release.git(self.source, 'init', '-q')
        release.git(self.source, 'add', '.')
        self.commit()

    def commit(self):
        # Disposable repositories must have no background Git maintenance racing
        # TemporaryDirectory cleanup on runners with newer Git versions.
        release.git(self.source, '-c', 'user.name=Release Fixture', '-c', 'user.email=fixture@example.invalid',
                    '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
                    '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'gc.autoDetach=false',
                    'commit', '-qm', 'fixture')

    def test_same_source_produces_identical_archives_and_verified_hash_inventory(self):
        first = release.build(self.base / 'one', self.source)
        second = release.build(self.base / 'two', self.source)
        self.assertEqual(first['archive_sha256'], second['archive_sha256'])
        self.assertEqual(Path(first['archive']).read_bytes(), Path(second['archive']).read_bytes())
        checked = release.verify(first['archive'])
        self.assertEqual(checked['version'], first['version'])
        self.assertEqual(checked['archive_sha256'], first['archive_sha256'])
        manifest = json.loads((self.base / 'one/release-manifest.json').read_text())
        self.assertEqual(len(manifest['skills']), 14)
        self.assertIn('skills/ig-audit/import_csv.py', manifest['files'])
        sums = (self.base / 'one/SHA256SUMS').read_text()
        self.assertIn(first['archive_sha256'], sums)

    def test_untracked_files_and_outside_inventory_data_are_excluded(self):
        (self.source / 'skills/ig-account/private-local.txt').write_text('PRIVATE FIXTURE')
        (self.source / 'local-account-data').mkdir()
        (self.source / 'local-account-data/voice.md').write_text('PRIVATE FIXTURE')
        (self.source / '.env').write_text('FIXTURE_ONLY=value')
        release.git(self.source, 'add', '.env'); self.commit()
        files, _ = release.inventory(self.source)
        self.assertNotIn('.env', files)
        self.assertNotIn('skills/ig-account/private-local.txt', files)
        self.assertFalse(any(name.startswith('local-account-data') for name in files))

    def test_dirty_tracked_files_and_existing_output_are_refused(self):
        readme = self.source / 'README.md'; readme.write_text(readme.read_text() + '\nchanged\n')
        with self.assertRaisesRegex(ValueError, 'clean committed'):
            release.build(self.base / 'out', self.source)
        self.assertFalse((self.base / 'out').exists())
        with self.assertRaisesRegex(ValueError, 'new release'):
            release.build(self.source, self.source)

    def test_selected_symlinks_are_refused(self):
        path = self.source / 'docs/link.txt'; path.symlink_to(self.source / 'README.md')
        release.git(self.source, 'add', 'docs/link.txt'); self.commit()
        with self.assertRaisesRegex(ValueError, 'symbolic links'):
            release.inventory(self.source)

    def test_broken_documentation_link_and_version_mismatch_block_build(self):
        readme = self.source / 'README.md'; readme.write_text(readme.read_text() + '\n[broken](docs/missing.md)\n')
        release.git(self.source, 'add', 'README.md'); self.commit()
        with self.assertRaisesRegex(ValueError, 'broken packaged'):
            release.inventory(self.source)
        # Version mismatch is checked before local links.
        plugin = self.source / '.claude-plugin/plugin.json'
        data = json.loads(plugin.read_text()); data['version'] = '9.9.9'; plugin.write_text(json.dumps(data))
        release.git(self.source, 'add', '.claude-plugin/plugin.json'); self.commit()
        with self.assertRaisesRegex(ValueError, 'changelog'):
            release.inventory(self.source)

    def test_modified_or_extra_archive_entries_fail_verification(self):
        files, manifest = release.inventory(self.source)
        valid = release.archive_bytes(files, manifest)
        with zipfile.ZipFile(io.BytesIO(valid)) as archive:
            entries = {name: archive.read(name) for name in archive.namelist()}
        prefix = 'instagram-agent-skill-' + manifest['version'] + '/'
        for mode in ('modified', 'extra'):
            altered = dict(entries)
            if mode == 'modified':
                altered[prefix + 'README.md'] = b'changed'
            else:
                altered[prefix + 'unlisted.txt'] = b'extra'
            path = self.base / (mode + '.zip')
            with zipfile.ZipFile(path, 'w') as archive:
                for name, raw in altered.items():
                    archive.writestr(name, raw)
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                release.verify(path)

    def test_extracted_source_installs_without_git_and_installed_turkish_cli_runs(self):
        result = release.build(self.base / 'release', self.source)
        extracted = self.base / 'extracted'
        with zipfile.ZipFile(result['archive']) as archive:
            archive.extractall(extracted)
        package = extracted / ('instagram-agent-skill-' + result['version'])
        self.assertFalse((package / '.git').exists())
        destination = self.base / 'installed'
        installed = cli(str(package / 'scripts/install.py'), '--skills-dir', str(destination), cwd=self.base)
        self.assertEqual(installed.returncode, 0, installed.stderr)
        checked = cli(str(package / 'scripts/install.py'), '--skills-dir', str(destination), '--check', cwd=self.base)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        self.assertEqual(json.loads(checked.stdout)['status'], 'ok')
        used = cli(str(destination / 'ig-account/turkce.py'), 'analiz',
                   str(destination / 'ig-audit/example.synthetic.csv'), '--hesap', 'ornek_studyo',
                   '--olcut', 'paylasim_orani', cwd=self.base)
        self.assertEqual(used.returncode, 0, used.stderr)
        self.assertIn('fictional-1: %2,00', used.stdout)

    def test_failed_build_cleans_stage_without_creating_output(self):
        with patch.object(release, 'verify', side_effect=ValueError('simulated verification failure')):
            with self.assertRaises(ValueError):
                release.build(self.base / 'out', self.source)
        self.assertFalse((self.base / 'out').exists())
        self.assertEqual(list(self.base.glob('.release-stage-*')), [])


if __name__ == '__main__':
    unittest.main()
