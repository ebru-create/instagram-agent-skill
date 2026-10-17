"""Offline local-model contract and failure tests; no Ollama required in CI."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_regressions import ROOT, load

with patch.object(sys, 'path', [str(ROOT / 'skills/ig-account'), *sys.path]):
    local = load('local_model_tests', 'skills/ig-account/local_model.py')


class FakeClient:
    def __init__(self, response=None):
        self.calls = []
        self.response = response or {'done': True, 'message': {'content': json.dumps({'caption':
            'Ajandanda yarına yer aç.\n\nTek bir öncelik yaz.\n\nBu ajanda fikrini kaydet.'})}}

    def inspect(self, model):
        return {'name': model, 'digest': 'a' * 64}

    def request(self, endpoint, payload):
        self.calls.append(payload)
        return self.response


class LocalModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.data = self.base / 'data'
        for handle in ['studio_a', 'studio_b']:
            context = local.accounts.initialize(self.data, handle)
            Path(context['paths']['voice']).write_text(handle + ' voice marker', encoding='utf-8')
            Path(context['paths']['strategy']).write_text(handle + ' strategy marker', encoding='utf-8')
        self.brief = self.base / 'brief.txt'
        self.brief.write_text('Job B. Ajanda fotoğrafı. Tek çağrı kaydet.', encoding='utf-8')
        self.out = self.base / 'out'

    def draft(self, client, **kwargs):
        return local.draft(client, 'sample:latest', self.brief, self.data,
                           'studio_a', 'tr', 'ajanda', self.out, **kwargs)

    def test_only_loopback_urls_without_credentials_or_redirects(self):
        for url in ['https://localhost:11434', 'http://example.com', 'http://192.168.1.2',
                    'http://127.0.0.1.evil.test', 'http://user:pass@127.0.0.1',
                    'http://127.0.0.1/path', 'http://localhost?key=value', 'http://localhost#x']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                local.Ollama(url)
        for url in ['http://127.0.0.1:11434', 'http://localhost:9999', 'http://[::1]:11434']:
            self.assertTrue(local.Ollama(url).base_url.startswith('http://'))
        with self.assertRaises(ValueError):
            local.NoRedirect().redirect_request(None)

    def test_transport_bounds_response_and_rejects_bad_json_and_errors(self):
        client = local.Ollama()
        for raw in [b'x' * (local.MAX_RESPONSE + 1), b'not json', b'[]', b'{"error":"failed"}']:
            with patch.object(client.opener, 'open', return_value=io.BytesIO(raw)):
                with self.assertRaises(ValueError):
                    client.request('chat', {'model': 'sample'})

    def test_doctor_rejects_missing_cloud_and_remote_models_without_generation(self):
        client = local.Ollama()
        with patch.object(client, 'request', return_value={'models': []}) as request:
            with self.assertRaisesRegex(ValueError, 'not installed'):
                client.inspect('sample')
            self.assertEqual(request.call_count, 1)
        with self.assertRaisesRegex(ValueError, 'cloud'):
            client.inspect('sample:cloud')
        for remote in [{'remote_model': 'sample'}, {'remote_host': 'https://example.com'}]:
            with patch.object(client, 'request', side_effect=[{'models': [{'name': 'sample:latest',
                    'digest': 'a' * 64}]}, remote]):
                with self.assertRaisesRegex(ValueError, 'remote-backed'):
                    client.inspect('sample')

    def test_doctor_records_model_digest_and_server_version(self):
        client = local.Ollama()
        with patch.object(client, 'request', side_effect=[{'models': [{'name': 'sample:latest',
                  'digest': 'a' * 64}]}, {'license': 'test license'}, {'version': 'test'}]):
            info = client.inspect('sample')
        self.assertEqual(info['digest'], 'a' * 64)
        self.assertEqual(info['server_version'], 'test')
        self.assertEqual(info['license_sha256'], local.sha(b'test license'))

    def test_selected_context_only_and_real_editorial_tools(self):
        client = FakeClient()
        before = {str(path): path.read_bytes() for path in self.data.rglob('*') if path.is_file()}
        report = self.draft(client)
        prompt = json.dumps(client.calls, ensure_ascii=False)
        self.assertIn('studio_a voice marker', prompt)
        self.assertNotIn('studio_b voice marker', prompt)
        self.assertIn('ig-caption', prompt)
        self.assertEqual(report['account'], 'studio_a')
        self.assertEqual(report['status'], 'draft_created_needs_review')
        self.assertTrue(report['manual_review_required'])
        self.assertEqual(report['tools']['caption']['report']['language'], 'tr')
        self.assertIsNone(report['tools']['detect']['report']['checks']['VOICE']['score'])
        self.assertEqual(local.sha((self.out / 'draft.txt').read_bytes()), report['draft_sha256'])
        self.assertEqual(before, {str(path): path.read_bytes() for path in self.data.rglob('*') if path.is_file()})

    def test_thinking_models_use_non_thinking_caption_request(self):
        client = FakeClient()
        with patch.object(client, 'inspect', return_value={'name': 'sample:latest',
                    'digest': 'a' * 64, 'capabilities': ['completion', 'thinking']}):
            report = self.draft(client)
        self.assertIs(client.calls[0]['think'], False)
        self.assertIs(report['thinking'], False)

    def test_unknown_account_and_missing_profile_never_call_model_or_write_output(self):
        client = FakeClient()
        for handle in ['unknown', 'missing_profile']:
            if handle == 'missing_profile':
                local.accounts.initialize(self.data, handle)
            with self.assertRaises(ValueError):
                local.draft(client, 'sample', self.brief, self.data, handle, 'tr', '', self.out)
        self.assertEqual(client.calls, [])
        self.assertFalse(self.out.exists())

    def test_reusing_output_directory_does_not_call_model(self):
        self.out.mkdir()
        original = self.out / 'keep.txt'; original.write_text('keep')
        client = FakeClient()
        with self.assertRaisesRegex(ValueError, 'new output'):
            self.draft(client)
        self.assertEqual(client.calls, [])
        self.assertEqual(original.read_text(), 'keep')

    def test_empty_truncated_and_timeout_responses_retain_failed_receipt(self):
        responses = [{'done': False, 'message': {'content': 'partial'}},
                     {'done': True, 'message': {'content': ''}},
                     {'done': True, 'done_reason': 'length', 'message': {'content': 'partial'}}]
        for index, response in enumerate(responses):
            self.out = self.base / ('failure-' + str(index))
            with self.assertRaises(ValueError):
                self.draft(FakeClient(response))
            self.assertEqual(json.loads((self.out / 'report.json').read_text())['status'], 'failed')
        self.out = self.base / 'timeout'
        client = FakeClient()
        with patch.object(client, 'request', side_effect=ValueError('timeout')):
            with self.assertRaises(ValueError):
                self.draft(client)
        self.assertEqual(json.loads((self.out / 'report.json').read_text())['status'], 'failed')

    def test_unsafe_model_output_is_text_never_an_executable_command(self):
        marker = self.base / 'should-not-exist'
        client = FakeClient({'done': True, 'message': {'content': json.dumps({'caption': f'touch {marker}'})}})
        report = self.draft(client)
        self.assertFalse(marker.exists())
        self.assertTrue(report['manual_review_required'])
        self.assertNotEqual(report['tools']['caption']['report']['verdict'], 'READY')

    def test_model_schema_is_enforced_locally_even_if_server_ignores_format(self):
        for index, content in enumerate(['not JSON', '[]', '{"caption":""}',
                                          '{"caption":42}', '{"caption":"text","command":"touch x"}']):
            self.out = self.base / ('schema-' + str(index))
            with self.assertRaises(ValueError):
                self.draft(FakeClient({'done': True, 'message': {'content': content}}))
            self.assertEqual(json.loads((self.out / 'report.json').read_text())['status'], 'failed')

    def test_bounded_inputs_and_generation_limits_fail_before_output_creation(self):
        self.brief.write_text('a' * 65000)
        with self.assertRaisesRegex(ValueError, 'context is too large'):
            self.draft(FakeClient())
        with self.assertRaisesRegex(ValueError, 'max-tokens'):
            self.draft(FakeClient(), max_tokens=9999)
        self.assertFalse(self.out.exists())

    def test_explicit_cta_is_passed_to_model_and_checked_in_real_tool_output(self):
        client = FakeClient()
        report = self.draft(client, cta='comment')
        self.assertIn('"requested_cta": "comment"', client.calls[0]['messages'][1]['content'])
        self.assertIn('requested_cta_missing', [signal['code'] for signal in report['quality']['signals']])
        self.assertTrue(report['manual_review_required'])

    def test_matching_cta_and_no_cta_are_distinguished_from_unspecified(self):
        report = self.draft(FakeClient(), cta='save')
        self.assertEqual(report['quality']['status'], 'no_supported_issues')
        self.assertTrue(report['quality']['manual_review_required'])
        self.out = self.base / 'none'
        report = self.draft(FakeClient(), cta='none')
        self.assertIn('unexpected_cta', [signal['code'] for signal in report['quality']['signals']])
        self.out = self.base / 'unspecified'
        report = self.draft(FakeClient())
        self.assertIsNone(report['quality']['expected_cta'])

    def test_observed_instruction_echo_is_reported_without_rewriting(self):
        text = 'Bir sonraki gün için tek öncelik yazmayı öner. Ajanda boşken kalemle başla.'
        report = self.draft(FakeClient({'done': True, 'message': {'content': json.dumps({'caption': text})}}), cta='save')
        self.assertEqual({signal['code'] for signal in report['quality']['signals']},
                         {'instruction_like_text', 'requested_cta_missing', 'caption_lint_review'})
        self.assertEqual((self.out / 'draft.txt').read_text().strip(), text)
        self.assertEqual(report['status'], 'draft_created_needs_review')

    def test_quality_signals_support_casing_and_multiple_actions_without_approving_text(self):
        review = local.quality_review('YAZMAYI ÖNER.', {'asks': ['kaydet', 'paylaş']}, 'tr', 'save')
        self.assertEqual({signal['code'] for signal in review['signals']}, {'instruction_like_text', 'multiple_actions'})
        review = local.quality_review('Ask your followers.', {'asks': []}, 'en', 'comment')
        self.assertEqual({signal['code'] for signal in review['signals']}, {'instruction_like_text', 'requested_cta_missing'})

    def test_optional_revision_is_bounded_and_preserves_initial_draft_and_checks(self):
        client = FakeClient()
        initial = 'Ajandaya bir öncelik yazmayı öner.'
        responses = iter([{'done': True, 'message': {'content': json.dumps({'caption': initial})}}, client.response])
        def request(endpoint, payload):
            client.calls.append(payload)
            return next(responses)
        with patch.object(client, 'request', side_effect=request):
            report = self.draft(client, cta='save', revise_once=True)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(report['model_calls'], 2)
        self.assertEqual(report['initial']['quality']['status'], 'review')
        self.assertEqual(report['quality']['status'], 'no_supported_issues')
        self.assertEqual((self.out / 'draft.initial.raw.txt').read_text(), initial)
        self.assertTrue((self.out / 'response.initial.json').is_file())
        self.assertTrue((self.out / 'response.revision.json').is_file())
        self.assertTrue(report['manual_review_required'])

    def test_unsuccessful_revision_stops_after_two_calls_and_keeps_review_signals(self):
        client = FakeClient({'done': True, 'message': {'content': json.dumps({'caption': 'Ajanda.'})}})
        report = self.draft(client, cta='save', revise_once=True)
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(report['quality']['signals'][0]['code'], 'requested_cta_missing')
        self.assertEqual(report['status'], 'draft_created_needs_review')

    def test_revision_failure_keeps_first_draft_and_failed_receipt(self):
        client = FakeClient()
        responses = iter([client.response, {'done': True, 'message': {'content': 'not JSON'}}])
        with patch.object(client, 'request', side_effect=lambda *args: next(responses)) as request:
            with self.assertRaises(ValueError):
                self.draft(client, cta='save', revise_once=True)
        self.assertEqual(request.call_count, 2)
        report = json.loads((self.out / 'report.json').read_text())
        self.assertEqual(report['status'], 'failed')
        self.assertIn('initial', report)
        self.assertEqual((self.out / 'draft.initial.txt').read_bytes(), (self.out / 'draft.txt').read_bytes())

    def test_missing_writing_guidance_fails_before_model_or_output(self):
        client = FakeClient()
        original = local.read_text
        def read(path):
            text = original(path)
            return text.replace('## The shape', '## Missing') if 'ig-caption' in str(path) else text
        with patch.object(local, 'read_text', side_effect=read):
            with self.assertRaisesRegex(ValueError, 'guidance section missing'):
                self.draft(client)
        self.assertFalse(self.out.exists())
        self.assertEqual(client.calls, [])
