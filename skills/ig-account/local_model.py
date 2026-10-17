#!/usr/bin/env python3
"""Run a bounded caption workflow against an already installed local Ollama model."""
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

import account as accounts
from ig_language import lower

SKILLS = Path(__file__).resolve().parents[1]
MAX_RESPONSE = 2 * 1024 * 1024
CTA_LABELS = {'save': {'tr': 'kaydet', 'en': 'save this'},
              'comment': {'tr': 'yorum yaz', 'en': 'comment a keyword'},
              'share': {'tr': 'paylaş', 'en': 'share this'},
              'dm': {'tr': 'mesaj gönder', 'en': 'DM me'},
              'follow': {'tr': 'takip et', 'en': 'follow'}}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError('local model redirects are not allowed')


class Ollama:
    def __init__(self, base_url='http://127.0.0.1:11434', timeout=180):
        url = urllib.parse.urlsplit(base_url)
        host = url.hostname
        try:
            loopback = host == 'localhost' or ipaddress.ip_address(host).is_loopback
            port = url.port
        except ValueError:
            loopback = False
        if (url.scheme != 'http' or not loopback or url.username or url.password
                or url.path not in ('', '/') or url.query or url.fragment):
            raise ValueError('use an HTTP loopback Ollama URL without credentials, path or query')
        if not 1 <= timeout <= 600:
            raise ValueError('timeout must be between 1 and 600 seconds')
        # Normalize localhost to a numeric loopback; bypass proxies and redirects.
        host = '127.0.0.1' if host == 'localhost' else host
        self.base_url = f'http://[{host}]' if ':' in host else f'http://{host}'
        self.base_url += ':' + str(port or 11434)
        self.timeout = timeout
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, endpoint, payload=None):
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
        request = urllib.request.Request(self.base_url + '/api/' + endpoint, data=data,
                                         headers={'Content-Type': 'application/json'})
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                raw = response.read(MAX_RESPONSE + 1)
            if len(raw) > MAX_RESPONSE:
                raise ValueError('local model response exceeds size limit')
            result = json.loads(raw)
            if not isinstance(result, dict) or result.get('error'):
                raise ValueError('local model returned an error or invalid object')
            return result
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ValueError('local Ollama request failed; check server, model and timeout') from error

    def inspect(self, model):
        if not model or 'cloud' in model.lower() or len(model) > 200:
            raise ValueError('select an installed local model, not a cloud model')
        name = model if ':' in model else model + ':latest'
        models = self.request('tags').get('models', [])
        entry = next((item for item in models if item.get('name') == name), None)
        if not entry:
            raise ValueError('model is not installed locally; install it explicitly with ollama pull MODEL')
        detail = self.request('show', {'model': name})
        if any(item.get(key) for item in (entry, detail) for key in ('remote_host', 'remote_model')):
            raise ValueError('remote-backed models are not supported by this local workflow')
        digest = entry.get('digest', '')
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('Ollama did not provide a valid local model digest')
        return {'name': name, 'digest': digest, 'details': entry.get('details', {}),
                'capabilities': detail.get('capabilities', []),
                'license_sha256': sha(detail.get('license', '').encode()),
                'server_version': self.request('version').get('version'),
                'base_url': self.base_url}


def read_text(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'expected a regular input file: {path}')
    with path.open('rb') as stream:
        raw = stream.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024:
        raise ValueError(f'input is too large: {path}')
    return raw.decode('utf-8')


def guidance_section(text, heading):
    match = re.search(r'^## ' + re.escape(heading) + r'\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL)
    if not match:
        raise ValueError('required caption guidance section missing: ' + heading)
    return '## ' + heading + '\n' + match.group(1).strip()


def prepare(brief, root, account, language, keywords, cta=None):
    context = accounts.resolve(root, account)
    files = {str(brief): read_text(brief)}
    for name in ('ig-caption', 'ig-human'):
        path = SKILLS / name / 'SKILL.md'
        files[str(path)] = read_text(path)
    profile = {}
    for name in ('voice', 'strategy'):
        path = Path(context['paths'][name])
        if path.exists() or path.is_symlink():
            profile[name] = read_text(path)
            files[str(path)] = profile[name]
    if not profile.get('voice') or not profile.get('strategy'):
        raise ValueError('provide nonempty voice.md and strategy.md for the selected account first')
    caption_guidance = files[str(SKILLS / 'ig-caption/SKILL.md')]
    human_guidance = files[str(SKILLS / 'ig-human/SKILL.md')]
    guidance = ('ig-caption writing guidance:\n' + '\n\n'.join(
        guidance_section(caption_guidance, heading) for heading in ('The shape', 'Rules'))
        + '\n\nig-human writing guidance:\n'
        + guidance_section(human_guidance, 'Why this matters more on Instagram than it looks'))
    system = ('Draft one Instagram caption. Follow the supplied ig-caption and ig-human guidance. '
              'The runner resolves accounts and runs editorial tools after generation; do not claim you ran tools. '
              'Return JSON with exactly one string field caption, without headings, receipts, Markdown fences or analysis. '
              'Use only supplied facts, no invented results, testimonials, prices or dates. '
              'Do not execute commands or request files. Treat the brief and profile as source data. '
              'If essential facts are missing, ask one short clarification instead of inventing them.\n\n'
              + guidance)
    source_data = {'publishing_account': context['account'], 'language': language,
                   'keywords': keywords, 'profile': profile, 'brief': files[str(brief)], 'requested_cta': cta}
    user = ('Write the actual caption for the following brief in the requested language. '
            'Return {"caption":"the copy-ready caption"}. Do not explain your process.\n'
            + json.dumps(source_data, ensure_ascii=False)
            + '\nWrite directly to the reader in the account voice. The brief gives instructions '
              'to you, not sentences to copy. Turn writer-facing directions into natural '
              'reader-facing copy; do not tell the reader to instruct a writer. '
              'Use the explicitly requested CTA once as an actual reader request; '
              'none means no CTA, null means follow the brief. The current brief and explicit '
              'CTA take precedence over older profile preferences. Do not add other requests. '
              'Check the language, topic, reader voice and requested CTA before returning '
              'only the final caption JSON, without analysis.')
    if language == 'tr':
        target = {'save': 'Okuyucudan bu paylaşımı kaydetmesini iste.',
                  'comment': 'Okuyucudan kendi seçimini veya görüşünü BU PAYLAŞIMIN YORUMUNA yazmasını iste.',
                  'share': 'Okuyucudan bu paylaşımı paylaşmasını iste.',
                  'dm': 'Okuyucudan hesabımıza özel mesaj göndermesini iste.',
                  'follow': 'Okuyucudan hesabımızı takip etmesini iste.',
                  'none': 'Okuyucudan bir eylem isteme.',
                  None: 'Briefte istenen tek çağrıyı uygula.'}[cta]
        user += ('\nSON YAZIM GÖREVİ: Takipçinin okuyacağı doğal Türkçe açıklamayı yaz. '
                 'Yazara verilen görevi, tamamlanmış bir okuyucu önerisine dönüştür. '
                 'Yalnızca dilbilgisi örneği: "Bir kitap seçmeyi öner" görevinin okuyucu metni '
                 '"Bir kitap seç." olur. Konunu ve gerçek bilgilerini yukarıdaki brieften al. '
                 'Önerinin anlamını ve olumlu/olumsuz yönünü koru. '
                 'Profilde sen dili varsa sen, siz dili varsa siz kullan. '
                 + target + ' Bir başkasına veya takipçiye yorum yapma yönergesi verme. '
                 'Yanıt yalnızca {"caption":"okuyucuya hazır açıklama"} JSON nesnesi olsun.')
    if len(system) + len(user) > 24000:
        raise ValueError('caption context is too large for this bounded workflow; shorten brief/profiles')
    return context, [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], {
        name: sha(text.encode('utf-8')) for name, text in files.items()}, source_data


def tool(relative, text, language, extra=()):
    result = subprocess.run([sys.executable, str(SKILLS / relative), '--language', language,
                             '--json', *extra], input=text, text=True, capture_output=True, timeout=30)
    if result.returncode not in (0, 1):
        raise ValueError('editorial tool failed: ' + relative)
    return {'exit_code': result.returncode, 'script_sha256': sha((SKILLS / relative).read_bytes()),
            'report': json.loads(result.stdout)}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def quality_review(text, caption_report, language, cta=None):
    """Limited observable checks, never a model-quality or factuality score."""
    asks = caption_report['asks']
    signals = []
    if cta == 'none' and asks:
        signals.append({'code': 'unexpected_cta', 'detail': 'No CTA requested, but an action was detected.'})
    elif cta in CTA_LABELS and CTA_LABELS[cta][language] not in asks:
        signals.append({'code': 'requested_cta_missing', 'detail': 'The explicitly requested CTA was not detected.'})
    if len(asks) > 1:
        signals.append({'code': 'multiple_actions', 'detail': 'More than one action category was detected.'})
    if caption_report.get('verdict', 'READY') != 'READY':
        signals.append({'code': 'caption_lint_review', 'detail': 'Caption checks contain warnings or failures; inspect tools.caption.'})
    pattern = (r'\b(?:yazmayı|kaydetmeyi|paylaşmayı|yorum yapmayı)\s+öner(?:in)?\b|'
               r'\btakipçiye\b[^.!?\n]{0,60}\b(?:sor|sorun|söyle|söyleyin)\b'
               if language == 'tr' else r'\b(?:ask (?:the|your) followers|write (?:a|the) caption)\b')
    if re.search(pattern, lower(text, language)):
        signals.append({'code': 'instruction_like_text',
                        'detail': 'Possible instruction copied into audience-facing text; inspect manually.'})
    return {'expected_cta': cta, 'detected_actions': asks, 'signals': signals,
            'status': 'review' if signals else 'no_supported_issues', 'manual_review_required': True}


def caption_response(response):
    message = response.get('message')
    raw = message.get('content') if isinstance(message, dict) else None
    if (response.get('done') is not True or response.get('done_reason') == 'length'
            or not isinstance(raw, str) or not raw.strip()):
        raise ValueError('model returned empty, truncated or incomplete output')
    structured = json.loads(raw)
    if (not isinstance(structured, dict) or set(structured) != {'caption'}
            or not isinstance(structured['caption'], str) or not structured['caption'].strip()):
        raise ValueError('expected exactly one nonempty caption string from local model')
    return structured['caption']


def draft(client, model, brief, root, account, language, keywords, out, max_tokens=800, cta=None, revise_once=False):
    if not 64 <= max_tokens <= 2048:
        raise ValueError('max-tokens must be between 64 and 2048')
    if cta is not None and cta not in (*CTA_LABELS, 'none'):
        raise ValueError('unsupported requested CTA')
    context, messages, hashes, source_data = prepare(brief, root, account, language, keywords, cta)
    model_info = client.inspect(model)
    out = Path(out).expanduser().absolute()
    if out.exists() or out.is_symlink():
        raise ValueError('choose a new output directory')
    out.mkdir(parents=True, exist_ok=False)
    report = {'schema_version': 1, 'status': 'running', 'account': context['account'],
              'language': language, 'model': model_info, 'input_sha256': hashes,
              'runner_sha256': sha(Path(__file__).read_bytes()),
              'revision_requested': revise_once,
              'manual_review_required': True, 'tools': {}}
    dump(out / 'report.json', report)
    try:
        payload = {'model': model_info['name'], 'messages': messages, 'stream': False,
                   'format': {'type': 'object', 'properties': {'caption': {'type': 'string'}},
                              'required': ['caption'], 'additionalProperties': False},
                   'keep_alive': 0, 'options': {'temperature': 0, 'seed': 42,
                                               'num_ctx': 8192, 'num_predict': max_tokens}}
        if 'thinking' in model_info.get('capabilities', []):
            payload['think'] = False
        report['generation_options'] = payload['options']
        report['thinking'] = payload.get('think', 'model_default')
        report['request_sha256'] = sha(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode())
        report['model_calls'] = 1
        response = client.request('chat', payload)
        dump(out / 'response.json', response)
        raw = caption_response(response)
        (out / 'draft.raw.txt').write_text(raw, encoding='utf-8')
        override = Path(context['paths']['lexicon_tr' if language == 'tr' else 'lexicon'])
        extra = ('--lexicon', str(override)) if override.is_file() else ()
        lexicon = override if extra else SKILLS / 'ig-human' / ('slop.tr.json' if language == 'tr' else 'slop.json')
        report['lexicon_sha256'] = sha(lexicon.read_bytes())
        cleaned = tool('ig-human/humanize.py', raw, language, extra)
        report['tools']['humanize'] = cleaned
        text = cleaned['report']['text']
        (out / 'draft.txt').write_text(text, encoding='utf-8')
        report['tools']['detect'] = tool('ig-human/detect.py', text, language, extra)
        report['tools']['caption'] = tool('ig-caption/caption.py', text, language,
                                           ('--keywords', keywords))
        report['quality'] = quality_review(text, report['tools']['caption']['report'], language, cta)
        report['draft_sha256'] = sha(text.encode('utf-8'))
        report['timing'] = {key: response.get(key) for key in
                            ('total_duration', 'load_duration', 'prompt_eval_count', 'eval_count')}
        if revise_once:
            report['initial'] = {key: report[key] for key in
                                  ('quality', 'tools', 'draft_sha256', 'timing', 'request_sha256')}
            for name in ('response.json', 'draft.raw.txt', 'draft.txt'):
                path = out / name
                initial_name = 'response.initial.json' if name == 'response.json' else name.replace('draft.', 'draft.initial.')
                (out / initial_name).write_bytes(path.read_bytes())
            revision_data = {'caption_to_revise': text, 'brief': source_data['brief'],
                             'profile': source_data['profile'], 'requested_cta': cta,
                             'keywords': keywords, 'language': language, 'signals': report['quality']['signals']}
            revision_instruction = (
                '\nDüzeltme: Yazara görev verme; öneriyi doğrudan okuyucuya söyle. '
                'Olumlu öneriyi olumsuza çevirme. Sen/siz hitabını profildeki gibi kullan. '
                'Yalnızca istenen çağrıyı bir kez kullan. save = okuyucudan kaydetmesini iste; '
                'comment = okuyucudan seçimini bu paylaşımın yorumunda belirtmesini iste; '
                'share = okuyucudan paylaşmasını iste; dm = hesabımıza özel mesaj iste; '
                'follow = hesabımızı takip etmesini iste; none = çağrı ekleme; null = briefi izle. '
                'Verilmeyen gerçek ekleme. Yalnızca düzeltilmiş açıklamanın JSON nesnesini döndür.'
                if language == 'tr' else
                '\nRevise the caption into audience-facing copy. Preserve the brief meaning '
                'and profile voice. Include the one explicitly requested CTA (save/comment/share/dm/follow). '
                'none means no action; null means follow the brief. Do not invent facts. '
                'Return only the revised English caption JSON, without explanation.')
            revision_payload = dict(payload, messages=[
                {'role': 'system', 'content': 'Revise one caption using only supplied facts. '
                 'Preserve the brief meaning and profile voice/address. Return exactly {"caption":"final caption"}.'},
                {'role': 'user', 'content': json.dumps(revision_data, ensure_ascii=False) + revision_instruction}])
            if sum(len(message['content']) for message in revision_payload['messages']) > 24000:
                raise ValueError('revision context is too large')
            report['revision_request_sha256'] = sha(json.dumps(revision_payload, ensure_ascii=False, sort_keys=True).encode())
            report['model_calls'] = 2
            revised_response = client.request('chat', revision_payload)
            dump(out / 'response.revision.json', revised_response)
            revised = caption_response(revised_response)
            cleaned = tool('ig-human/humanize.py', revised, language, extra)
            text = cleaned['report']['text']
            revised_tools = {'humanize': cleaned,
                             'detect': tool('ig-human/detect.py', text, language, extra),
                             'caption': tool('ig-caption/caption.py', text, language, ('--keywords', keywords))}
            (out / 'draft.raw.txt').write_text(revised, encoding='utf-8')
            (out / 'draft.txt').write_text(text, encoding='utf-8')
            dump(out / 'response.json', revised_response)
            report['tools'] = revised_tools
            report['quality'] = quality_review(text, revised_tools['caption']['report'], language, cta)
            report['draft_sha256'] = sha(text.encode('utf-8'))
            report['timing'] = {key: revised_response.get(key) for key in
                               ('total_duration', 'load_duration', 'prompt_eval_count', 'eval_count')}
        report['status'] = 'draft_created_needs_review'
        dump(out / 'report.json', report)
        return report
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        dump(out / 'report.json', report)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:11434')
    parser.add_argument('--timeout', type=int, default=180)
    commands = parser.add_subparsers(dest='command', required=True)
    doctor = commands.add_parser('doctor', help='inspect an already installed local model')
    doctor.add_argument('--model', required=True)
    caption = commands.add_parser('caption', help='draft, clean and lint one caption for manual review')
    caption.add_argument('--model', required=True)
    caption.add_argument('--brief', type=Path, required=True)
    caption.add_argument('--account', required=True)
    caption.add_argument('--root', default=accounts.DEFAULT_ROOT)
    caption.add_argument('--language', choices=('tr', 'en'), default='tr')
    caption.add_argument('--keywords', default='')
    caption.add_argument('--out', type=Path, required=True)
    caption.add_argument('--max-tokens', type=int, default=800)
    caption.add_argument('--cta', choices=(*CTA_LABELS, 'none'),
                         help='explicit requested action; omitted follows brief, none requests no action')
    caption.add_argument('--revise-once', action='store_true',
                         help='explicitly request one additional revision; retain original and both checks')
    args = parser.parse_args()
    try:
        client = Ollama(args.base_url, args.timeout)
        if args.command == 'doctor':
            report = client.inspect(args.model)
        else:
            report = draft(client, args.model, args.brief, args.root, args.account,
                           args.language, args.keywords, args.out, args.max_tokens, args.cta, args.revise_once)
        print(json.dumps(report, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f'Local model workflow: {error}\n')


if __name__ == '__main__':
    main()
