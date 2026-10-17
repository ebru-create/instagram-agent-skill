"""Exercise the complete installed workflow and preserve inspectable failures."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_carousel import FONT, HAS_PILLOW
from test_regressions import load

workflow = load('workflow_validation_tests', 'validation/run_workflow.py')


@unittest.skipUnless(FONT and HAS_PILLOW, 'workflow rendering needs optional Pillow and a suitable font')
class WorkflowTests(unittest.TestCase):
    def test_full_replay_links_exports_publications_audit_and_experiment(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'replay'
            report = workflow.run(output, FONT)
            self.assertEqual(report['status'], 'passed_with_manual_review')
            self.assertEqual(report['account'], 'ornek_studyo')
            stages = {check['stage']: check for check in report['checks']}
            self.assertEqual(stages['content-and-exports']['slides'], 8)
            self.assertEqual(stages['publication-audit-test']['rates'], [.02, .04])
            self.assertTrue(stages['failure-paths']['incomplete_review_blocked'])
            self.assertTrue(stages['isolation-and-history']['second_account_unchanged'])
            self.assertTrue(report['editorial_reviews'])
            self.assertIn('handoff.tr.md', report['artifacts'])
            ledger = json.loads((output / 'account-data/accounts/ornek_studyo/publications.json').read_text())
            self.assertEqual(len(ledger['entries']), 2)
            self.assertEqual({entry['content_id'] for entry in ledger['entries']},
                             {'kurgusal-atolye-kapak-01', 'kurgusal-atolye-kapak-02'})
            steps = json.loads((output / 'commands.json').read_text())
            self.assertEqual(report['command_count'], len(steps))
            self.assertEqual(next(s for s in steps if s['step'] == 'wrong-account-rejected')['exit_code'], 2)
            self.assertEqual(json.loads((output / 'report.json').read_text())['status'], report['status'])

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            sentinel = Path(temp) / 'keep.txt'; sentinel.write_text('KEEP')
            with self.assertRaisesRegex(ValueError, 'new output'):
                workflow.run(temp, FONT)
            self.assertEqual(sentinel.read_text(), 'KEEP')
            self.assertEqual(list(Path(temp).iterdir()), [sentinel])

    def test_failure_keeps_report_and_prior_command_evidence(self):
        original = workflow.Workflow.call
        def fail_render(instance, name, *args, **kwargs):
            if name == 'render-control':
                raise ValueError('simulated export failure')
            return original(instance, name, *args, **kwargs)
        with tempfile.TemporaryDirectory() as temp, patch.object(workflow.Workflow, 'call', fail_render):
            output = Path(temp) / 'failed-run'
            with self.assertRaisesRegex(ValueError, 'simulated'):
                workflow.run(output, FONT)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertGreater(report['command_count'], 0)
            self.assertIn('commands.json', report['artifacts'])
            self.assertFalse((output / 'account-data/accounts/ornek_studyo/publications.json').exists())


class WorkflowPreflightTests(unittest.TestCase):
    def test_missing_font_does_not_create_an_output_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / 'new'
            with self.assertRaisesRegex(ValueError, 'font'):
                workflow.run(out, Path(temp) / 'absent.ttf')
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
