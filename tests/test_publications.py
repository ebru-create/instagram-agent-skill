"""Publication history, account boundaries, atomic writes and CSV reconciliation."""
import csv
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_regressions import ROOT, cli, load

publication = load('publication_tests', 'skills/ig-account/publication.py')
EXAMPLE = ROOT / 'skills/ig-account/example.publication.tr.json'
CSV = ROOT / 'skills/ig-audit/example.synthetic.csv'


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.context = publication.audit.accounts.initialize(self.root, 'ornek_studyo')
        self.path = Path(self.context['paths']['publications'])
        self.data = json.loads(EXAMPLE.read_text())

    def record(self, revise=False):
        return publication.record(json.dumps(self.data, ensure_ascii=False).encode(), self.root, '@ornek_studyo', revise)

    def csv(self, **changes):
        rows = list(csv.DictReader(io.StringIO(CSV.read_text())))
        rows[0].update(changes)
        output = io.StringIO(newline=''); writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
        return output.getvalue().encode()

    def test_first_record_has_identity_hash_and_user_reported_provenance(self):
        result = publication.record(EXAMPLE.read_bytes(), self.root, 'ornek_studyo')
        self.assertEqual(result['entry']['revision'], 1)
        self.assertEqual(result['entry']['source_sha256'], hashlib.sha256(EXAMPLE.read_bytes()).hexdigest())
        self.assertEqual(result['entry']['reference'], self.data['reference'])
        self.assertEqual(result['verification'], 'user-reported, not platform-verified')
        self.assertEqual(len(publication.read_ledger(self.root, 'ornek_studyo')['entries']), 1)

    def test_duplicate_content_or_post_cannot_silently_overwrite(self):
        self.record(); before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.record()
        self.data['content_id'] = 'another-local-id'
        with self.assertRaises(ValueError):
            self.record()
        self.assertEqual(before, self.path.read_bytes())

    def test_revision_can_correct_post_id_and_retains_original_history(self):
        self.record()
        self.data.update(post_id='corrected-id', reference='Kullanıcı kimliği düzeltti.')
        result = self.record(revise=True)
        ledger = publication.read_ledger(self.root, 'ornek_studyo')
        self.assertEqual(result['entry']['revision'], 2)
        self.assertEqual(ledger['entries'][0]['post_id'], 'fictional-1')
        current = publication.latest(ledger)[self.data['content_id']]
        self.assertEqual(current['post_id'], 'corrected-id')
        result = publication.reconcile(self.csv(), self.root, 'ornek_studyo')
        self.assertIn('fictional-1', result['csv_without_record'])
        self.assertEqual(result['records_without_csv'], ['corrected-id'])

    def test_revision_requires_known_content_and_cannot_take_another_active_post(self):
        with self.assertRaises(ValueError):
            self.record(revise=True)
        self.record()
        self.data.update(content_id='second', post_id='fictional-2')
        self.record()
        self.data['post_id'] = 'fictional-1'
        with self.assertRaises(ValueError):
            self.record(revise=True)

    def test_csv_match_and_partial_coverage_are_explicit_and_read_only(self):
        self.record(); before = self.path.read_bytes()
        raw = self.csv()
        result = publication.reconcile(raw, self.root, 'ornek_studyo')
        self.assertEqual(result['matched'][0]['content_id'], self.data['content_id'])
        self.assertEqual(result['identity_conflicts'], [])
        self.assertEqual(result['csv_without_record'], ['fictional-2', 'fictional-3', 'fictional-4'])
        self.assertEqual(result['source_sha256'], hashlib.sha256(raw).hexdigest())
        self.assertEqual(before, self.path.read_bytes())

    def test_conflicts_disclose_each_changed_field_without_rewriting_csv(self):
        self.record()
        result = publication.reconcile(self.csv(format='image', distribution='paid', published_at='2026-09-01T13:00:00+03:00'), self.root, 'ornek_studyo')
        fields = result['identity_conflicts'][0]['fields']
        self.assertEqual(set(fields), {'format', 'distribution', 'published_at'})
        self.assertEqual(fields['format'], {'record': 'carousel', 'csv': 'image'})
        self.assertEqual(result['matched'], [])

    def test_equivalent_timezones_match_same_publication_instant(self):
        self.record()
        result = publication.reconcile(self.csv(published_at='2026-09-01T09:00:00Z'), self.root, 'ornek_studyo')
        self.assertEqual(len(result['matched']), 1)
        self.assertEqual(result['identity_conflicts'], [])

    def test_records_missing_from_csv_are_disclosed(self):
        self.data['post_id'] = 'outside-export-window'; self.record()
        result = publication.reconcile(self.csv(), self.root, 'ornek_studyo')
        self.assertEqual(result['records_without_csv'], ['outside-export-window'])

    def test_empty_ledger_read_and_reconciliation_create_nothing(self):
        self.assertEqual(publication.read_ledger(self.root, 'ornek_studyo')['entries'], [])
        result = publication.reconcile(self.csv(), self.root, 'ornek_studyo')
        self.assertEqual(len(result['csv_without_record']), 4)
        self.assertFalse(self.path.exists())

    def test_wrong_accounts_never_mix_with_selected_account(self):
        publication.audit.accounts.initialize(self.root, 'other')
        self.data['account'] = 'other'
        with self.assertRaises(ValueError):
            self.record()
        with self.assertRaises(ValueError):
            publication.reconcile(self.csv(account='other'), self.root, 'ornek_studyo')
        self.assertFalse(self.path.exists())
        self.assertFalse((self.root / 'accounts/other/publications.json').exists())

    def test_future_dates_ambiguous_dates_and_malformed_fields_fail(self):
        for field, value in [('published_at', '9999-01-01T12:00:00+00:00'),
                             ('published_at', '2026-09-01'), ('content_id', '../escape'),
                             ('format', 'video'), ('distribution', ''), ('reference', ''), ('post_id', None)]:
            data = dict(self.data); data[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                publication.validate(data, 'ornek_studyo')
        raw = EXAMPLE.read_bytes().replace(b'"account":', b'"account": "ornek_studyo", "account":', 1)
        with self.assertRaises(ValueError):
            publication.decode(raw)

    def test_corrupted_history_is_preserved_and_blocks_writes(self):
        self.path.write_text('{ broken')
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.record()
        self.assertEqual(self.path.read_bytes(), before)
        self.assertFalse(self.path.with_name('.publications.lock').exists())

    def test_invalid_history_revision_and_entry_account_are_rejected(self):
        self.record(); original = json.loads(self.path.read_text())
        for field, value in [('revision', 3), ('account', 'other'), ('source_sha256', 'bad'), ('recorded_at', 1)]:
            entry = dict(original['entries'][0]); entry[field] = value
            self.path.write_text(json.dumps({**original, 'entries': [entry]}))
            with self.subTest(field=field), self.assertRaises(ValueError):
                publication.read_ledger(self.root, 'ornek_studyo')

    def test_lock_refuses_concurrent_write_without_removing_existing_lock(self):
        lock = self.path.with_name('.publications.lock'); lock.mkdir()
        with self.assertRaises(ValueError):
            self.record()
        self.assertTrue(lock.is_dir())
        self.assertFalse(self.path.exists())

    def test_failed_atomic_replace_keeps_original_and_cleans_temporary_files(self):
        self.record(); before = self.path.read_bytes()
        self.data['reference'] = 'Changed note'
        with patch.object(Path, 'replace', side_effect=OSError('simulated replace failure')):
            with self.assertRaises(OSError):
                self.record(revise=True)
        self.assertEqual(before, self.path.read_bytes())
        self.assertEqual(list(self.path.parent.glob('.publications*')), [])

    def test_symlinked_ledger_and_uninitialized_accounts_are_refused(self):
        outside = self.root / 'outside'; outside.write_text('KEEP')
        self.path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.record()
        self.assertEqual(outside.read_text(), 'KEEP')
        with self.assertRaises(ValueError):
            publication.read_ledger(self.root, 'unknown')

    def test_recording_preserves_existing_draft_log_and_results(self):
        for key in ('plan', 'log', 'results'):
            Path(self.context['paths'][key]).write_text('KEEP')
        self.record()
        for key in ('plan', 'log', 'results'):
            self.assertEqual(Path(self.context['paths'][key]).read_text(), 'KEEP')

    def test_cli_check_needs_no_account_folder_and_errors_have_no_traceback(self):
        root = self.root / 'does-not-exist'
        result = cli('skills/ig-account/publication.py', 'check', str(EXAMPLE), '--account', 'ornek_studyo', '--root', str(root))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(root.exists())
        result = cli('skills/ig-account/publication.py', 'check', str(EXAMPLE), '--account', 'other')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
