"""Host layouts and root selection in isolated homes; no real model required."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_regressions import ROOT, load

installer = load('host_installer_tests', 'scripts/install.py')
accounts = load('host_account_tests', 'skills/ig-account/account.py')


class HostTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / 'home'; self.home.mkdir()
        self.env = dict(os.environ, HOME=str(self.home), INSTAGRAM_AGENT_HOME='')

    def run_cli(self, script, *args, env=None):
        return subprocess.run([sys.executable, str(ROOT / script), *args],
                              env=env or self.env, text=True, capture_output=True)

    def test_cli_host_previews_are_read_only_and_select_expected_destinations(self):
        for host, expected in [('codex', self.home / '.agents/skills'),
                               ('claude-code', self.home / '.claude/skills')]:
            result = self.run_cli('scripts/install.py', '--host', host, '--dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(Path(report['destination']), expected)
            self.assertFalse(expected.exists())
        result = self.run_cli('scripts/install.py', '--dry-run')
        self.assertEqual(Path(json.loads(result.stdout)['destination']), self.home / '.claude/skills')

    def test_generic_requires_target_and_explicit_target_wins_for_every_host(self):
        result = self.run_cli('scripts/install.py', '--host', 'generic', '--dry-run')
        self.assertEqual(result.returncode, 2)
        for host in ['generic', 'codex', 'claude-code']:
            target = self.base / host
            result = self.run_cli('scripts/install.py', '--host', host, '--skills-dir', str(target), '--dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(Path(json.loads(result.stdout)['destination']), target)
            self.assertFalse(target.exists())

    def test_core_installs_and_checks_without_claude_metadata(self):
        source = self.base / 'source'
        for name in ['skills', 'templates']:
            shutil.copytree(ROOT / name, source / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(ROOT / 'instagram-agent.json', source / 'instagram-agent.json')
        target = self.base / 'generic-skills'
        with patch.object(installer, 'smoke_check', return_value=13):
            installed = installer.install(target, source)
            checked = installer.install(target, source, check=True)
        self.assertEqual(installed['skills'], 14)
        self.assertEqual(checked['status'], 'ok')
        self.assertFalse((source / '.claude-plugin').exists())

    def test_new_root_and_legacy_precedence_never_migrate_or_merge(self):
        with patch.dict(os.environ, self.env), patch.object(accounts.Path, 'home', return_value=self.home):
            neutral = self.home / '.local/share/instagram-agent'
            legacy = self.home / '.claude/instagram'
            self.assertEqual(Path(accounts.default_root()), neutral)
            self.assertFalse(neutral.exists())
            legacy.mkdir(parents=True)
            accounts.initialize(legacy, 'old_account')
            accounts.initialize(neutral, 'new_account')
            self.assertEqual(Path(accounts.default_root()), legacy)
            self.assertEqual(accounts.list_accounts(accounts.default_root()), ['old_account'])
            with self.assertRaisesRegex(ValueError, 'unknown account'):
                accounts.resolve(accounts.default_root(), 'new_account')

    def test_environment_root_reaches_turkish_research_analytics_and_publication(self):
        data = self.base / 'common-data'
        env = dict(self.env, INSTAGRAM_AGENT_HOME=str(data))
        created = self.run_cli('skills/ig-account/turkce.py', 'hesap', 'ekle', 'ornek_studyo', '--json', env=env)
        self.assertEqual(created.returncode, 0, created.stderr)
        account = data / 'accounts/ornek_studyo'
        self.assertTrue(account.is_dir())
        saved = self.run_cli('skills/ig-account/turkce.py', 'analiz',
                             str(ROOT / 'skills/ig-audit/example.synthetic.csv'), '--hesap', 'ornek_studyo',
                             '--olcut', 'erisim', '--kaydet', '--json', env=env)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        saved_to = Path(json.loads(saved.stdout)['saved_to'])
        self.assertTrue(saved_to.is_relative_to(account / 'audits'))
        self.assertTrue(saved_to.is_dir())
        published = self.run_cli('skills/ig-account/publication.py', 'record',
                                 str(ROOT / 'skills/ig-account/example.publication.tr.json'),
                                 '--account', 'ornek_studyo', env=env)
        self.assertEqual(published.returncode, 0, published.stderr)
        self.assertTrue((account / 'publications.json').is_file())
        source = self.base / 'research.tsv'
        source.write_text('account\tfollowers\tmedian\tviews\thook\n@other\t1000\t100\t500\tThree useful ideas\n')
        saved = self.run_cli('skills/ig-viral/swipe.py', str(source), '--account', 'ornek_studyo', env=env)
        self.assertEqual(saved.returncode, 0, saved.stderr)
        self.assertTrue((account / 'swipe.md').is_file())
        self.assertFalse((self.home / '.claude').exists())

    def test_explicit_cli_root_wins_over_environment_without_touching_other_root(self):
        overridden = self.base / 'environment-data'
        explicit = self.base / 'explicit-data'
        result = self.run_cli('skills/ig-account/account.py', '--root', str(explicit), 'init', 'test_account',
                              env=dict(self.env, INSTAGRAM_AGENT_HOME=str(overridden)))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((explicit / 'accounts/test_account').is_dir())
        self.assertFalse(overridden.exists())

    def test_installer_refuses_all_known_account_data_roots(self):
        configured = self.base / 'configured-data'
        with patch.object(installer.Path, 'home', return_value=self.home), \
                patch.dict(os.environ, {'INSTAGRAM_AGENT_HOME': str(configured)}):
            for data in [configured, self.home / '.claude/instagram', self.home / '.local/share/instagram-agent']:
                for target in [data, data / 'skills']:
                    with self.assertRaisesRegex(ValueError, 'account-data'):
                        installer.destination(target)
                    self.assertFalse(target.exists())

    def test_every_host_installs_same_files_and_runs_tools_from_unrelated_directory(self):
        inventories = []
        for host in ['codex', 'claude-code', 'generic']:
            target = self.base / host
            result = self.run_cli('scripts/install.py', '--host', host, '--skills-dir', str(target))
            self.assertEqual(result.returncode, 0, result.stderr)
            checked = self.run_cli('scripts/install.py', '--host', host, '--skills-dir', str(target), '--check')
            self.assertEqual(checked.returncode, 0, checked.stderr)
            inventories.append(json.loads((target / installer.MANIFEST).read_text())['files'])
            env = dict(self.env, INSTAGRAM_AGENT_HOME=str(self.base / ('data-' + host)))
            result = subprocess.run([sys.executable, str(target / 'ig-account/turkce.py'),
                                     'hesap', 'ekle', 'test_account', '--json'],
                                    env=env, cwd=self.home, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((Path(env['INSTAGRAM_AGENT_HOME']) / 'accounts/test_account').is_dir())
        self.assertEqual(inventories[0], inventories[1])
        self.assertEqual(inventories[1], inventories[2])
