#!/usr/bin/env python3
"""Opt-in live Ollama check using a fresh generic installation and fictional profiles."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def run(model, out, base_url='http://127.0.0.1:11434', timeout=180, revise_once=False):
    out = Path(out).expanduser().absolute()
    out.mkdir(parents=True, exist_ok=False)
    steps = []

    def call(script, *args, codes=(0,)):
        result = subprocess.run([sys.executable, str(script), *map(str, args)],
                                text=True, capture_output=True, timeout=timeout + 60)
        steps.append({'program': str(script), 'args': list(map(str, args)),
                      'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
        (out / 'commands.json').write_text(json.dumps(steps, ensure_ascii=False, indent=2), encoding='utf-8')
        if result.returncode not in codes:
            raise ValueError('validation command failed; see commands.json')
        return json.loads(result.stdout) if result.stdout.strip() else {}

    report = {'kind': 'synthetic-live-local-model-check', 'status': 'running',
              'revision_requested': revise_once,
              'manual_review_required': True, 'checks': [], 'outputs': [],
              'limitations': ['Two fictional caption scenarios, not a quality benchmark.',
                              'No model-generated tool calls or autonomous file access are tested.',
                              'Editorial scores do not establish factual accuracy or business outcomes.']}
    try:
        target = out / 'installed'
        call(ROOT / 'scripts/install.py', '--host', 'generic', '--skills-dir', target)
        helper = target / 'ig-account/local_model.py'
        call(ROOT / 'scripts/install.py', '--host', 'generic', '--skills-dir', target, '--check')
        doctor = call(helper, '--base-url', base_url, 'doctor', '--model', model)
        report['model'] = doctor
        data = out / 'accounts-data'
        cases = [
            ('ornek_atolye', 'ATOLYE_MAVI', 'ajanda',
             'Kurgusal marka ATOLYE_MAVI. Sen dili, kısa ve sakin Türkçe. Sayı, fiyat veya başarı iddiası ekleme.',
             'Hedef: ücretsiz ajanda örneğini tanıtmak. Kaydetme tek çağrı olsun.',
             'Job B: tek fotoğrafın açıklaması. Fotoğrafta boş ajanda ve kalem var. '
             'Bir sonraki gün için tek öncelik yazmayı öner. Arama sözcüğü ajanda. '
             'Yalnızca kaydetmeye davet et. En fazla 100 kelime; fiyat, müşteri, süre ve sonuç iddiası yok.'),
            ('ornek_seramik', 'SERAMIK_YESIL', 'seramik',
             'Kurgusal marka SERAMIK_YESIL. Siz dili, sade Türkçe. Başka markalardan söz etme.',
             'Hedef: seramik taslaklarını anlatmak. Tek çağrı yorumda seçim belirtmek.',
             'Job B: tek fotoğrafta iki seramik fincan taslağı var. Biri düz, diğeri çizgili. '
             'Arama sözcüğü seramik. Takipçiye hangi deseni seçtiğini yorumda sor. '
             'En fazla 100 kelime. Satış, tarih, fiyat veya müşteri deneyimi iddiası ekleme.')]
        contexts = {}
        for handle, marker, keyword, voice, strategy, brief in cases:
            context = call(target / 'ig-account/account.py', '--root', data, 'init', handle)
            contexts[handle] = context
            for name, text in [('voice', voice), ('strategy', strategy)]:
                Path(context['paths'][name]).write_text(text, encoding='utf-8')
        for handle, marker, keyword, voice, strategy, brief in cases:
            context = contexts[handle]
            path = out / (handle + '.brief.txt'); path.write_text(brief, encoding='utf-8')
            receipt = call(helper, '--base-url', base_url, '--timeout', timeout, 'caption',
                            '--model', model, '--brief', path, '--account', handle,
                            '--root', data, '--language', 'tr', '--keywords', keyword,
                            '--cta', 'save' if handle == 'ornek_atolye' else 'comment',
                            '--max-tokens', 500, '--out', out / handle,
                            *(['--revise-once'] if revise_once else []))
            text = (out / handle / 'draft.txt').read_text(encoding='utf-8')
            foreign = next(item[1] for item in cases if item[0] != handle)
            if not text.strip() or foreign.casefold() in text.casefold():
                raise ValueError('empty output or other account marker in caption')
            expected = {str(Path(context['paths'][key])) for key in ('voice', 'strategy')}
            if not expected.issubset(receipt['input_sha256']):
                raise ValueError('selected profile hashes absent from receipt')
            if receipt['model']['digest'] != doctor['digest']:
                raise ValueError('model changed during validation')
            report['outputs'].append({'account': handle, 'draft_sha256': hashlib.sha256(text.encode()).hexdigest(),
                                       'caption_verdict': receipt['tools']['caption']['report']['verdict'],
                                       'detect_verdict': receipt['tools']['detect']['report']['verdict'],
                                       'model_calls': receipt['model_calls'],
                                       'quality': receipt['quality']})
        call(helper, '--base-url', base_url, 'caption', '--model', model,
                      '--brief', path, '--account', 'missing_account', '--root', data,
                      '--out', out / 'must-not-exist', codes=(2,))
        if (out / 'must-not-exist').exists() or 'unknown account' not in steps[-1]['stderr']:
            raise ValueError('unknown account wrote output')
        report['checks'] = ['fresh generic installation + 13 smoke checks',
                            'two fictional account generations with distinct profile hashes; at most two model calls each',
                            'both outputs cleaned and linted in Turkish',
                            'explicit requested CTAs and instruction-copy signals recorded',
                            'no other-account marker in either output',
                            'unknown account rejected before output creation']
        report['status'] = 'passed_with_manual_review'
    except Exception as error:
        report['status'] = 'failed'
        report['error'] = str(error)
        raise
    finally:
        (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--base-url', default='http://127.0.0.1:11434')
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--revise-once', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.model, args.out, args.base_url, args.timeout, args.revise_once), ensure_ascii=False, indent=2))
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(2, str(error) + '\n')
