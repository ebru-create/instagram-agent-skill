#!/usr/bin/env python3
"""Replay a fictional Turkish workflow against a fresh installed bundle."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCENARIO = Path(__file__).with_name('scenario.tr.json')


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def require(condition, message):
    if not condition:
        raise ValueError(message)


class Workflow:
    def __init__(self, out):
        self.out = out
        self.steps = []

    def call(self, name, program, *args, text=None, codes=(0,), json_output=True):
        result = subprocess.run([sys.executable, str(program), *map(str, args)],
                                input=text, text=True, capture_output=True, cwd=self.out,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}, timeout=120)
        receipt = {'step': name, 'program': str(program), 'args': list(map(str, args)),
                   'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}
        self.steps.append(receipt)
        dump(self.out / 'commands.json', self.steps)
        require(result.returncode in codes, f'{name}: unexpected exit {result.returncode}; see commands.json')
        if not json_output:
            return receipt
        try:
            return json.loads(result.stdout)
        except ValueError as error:
            raise ValueError(f'{name}: expected JSON output; see commands.json') from error


def run(out, font):
    out, font = Path(out).expanduser().absolute(), Path(font).expanduser().resolve()
    require(font.is_file(), 'provide an existing Turkish-capable font with --font')
    require(not out.exists() and not out.is_symlink(), 'choose a new output directory')
    # mkdir is exclusive; no existing account root or export is reused.
    out.mkdir(parents=True, exist_ok=False)
    workflow = Workflow(out)
    report = {'schema_version': 1, 'kind': 'synthetic-workflow-validation', 'status': 'running',
              'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'python': platform.python_version(), 'checks': [], 'editorial_reviews': [],
              'limitations': [
                  'Tamamen kurgusal veriler; gerçek hesap, yayın veya Instagram bağlantısı kullanılmadı.',
                  'Plan ve taslaklar elle hazırlanmış sabit örneklerdir; modelin yaratıcı kararları ve talimatlara uyumu ölçülmedi.',
                  'Yayın kayıtları, analitik veriler ve tarihsel değerlendirme simülasyondur; performans veya nedensellik kanıtı değildir.',
                  'Otomatik kontroller görsel ve editoryal insan incelemesinin yerine geçmez.'
              ]}
    try:
        scenario = json.loads(SCENARIO.read_text(encoding='utf-8'))
        account, other = scenario['account'], scenario['other_account']
        report['account'] = account
        report['scenario_sha256'] = hashlib.sha256(SCENARIO.read_bytes()).hexdigest()
        dump(out / 'scenario.json', scenario)
        skills, data = out / 'skills', out / 'account-data'
        workflow.call('install', ROOT / 'scripts/install.py', '--skills-dir', skills)
        tool = lambda relative: skills / relative
        workflow.call('check-install', ROOT / 'scripts/install.py', '--skills-dir', skills, '--check')
        report['bundle_manifest_sha256'] = hashlib.sha256((skills / '.instagram-agent-install.json').read_bytes()).hexdigest()
        context = workflow.call('init-account', tool('ig-account/account.py'), '--root', data, 'init', account)
        second = workflow.call('init-second-account', tool('ig-account/account.py'), '--root', data, 'init', other)
        other_voice = Path(second['paths']['voice'])
        other_voice.write_text('İkinci markanın korunacak örnek sesi.', encoding='utf-8')
        sentinel = hashlib.sha256(other_voice.read_bytes()).hexdigest()
        total = scenario['shared_preparation_minutes'] + sum(slot['minutes'] for slot in scenario['slots'])
        require(total <= scenario['weekly_minutes'], 'fixture exceeds its stated budget')
        plan = ('# KURGUSAL PLAN — elle hazırlanmış test girdisi\n\n'
                f"Hesap: @{account}\nHedef: {scenario['goal']}\n"
                f"Kapasite: {scenario['weekly_minutes']} dakika; toplam: {total} dakika.\n"
                'Bu dosya model tarafından üretilmiş plan değildir. Yayın yapılmadı.\n\n')
        for slot in scenario['slots']:
            plan += f"- {slot['content_id']}: {slot['cover']} — {slot['minutes']} dakika\n"
        Path(context['paths']['plan']).write_text(plan, encoding='utf-8')
        Path(context['paths']['strategy']).write_text('# Kurgusal strateji\n' + scenario['goal'], encoding='utf-8')
        Path(context['paths']['voice']).write_text('# Kurgusal ses\nDil: Türkçe. Sade anlatım, sen hitabı.', encoding='utf-8')
        report['checks'].append({'stage': 'plan-fixture', 'minutes': total, 'capacity': scenario['weekly_minutes']})
        original = json.loads((skills / 'ig-plan/example.experiment.tr.json').read_text(encoding='utf-8'))
        original['assignments'] = []
        prospective = out / 'experiment-before.json'; dump(prospective, original)
        workflow.call('save-prospective-test', tool('ig-plan/experiment.py'), prospective,
                      '--account', account, '--root', data, '--save')
        empty = workflow.call('no-publications-yet', tool('ig-account/publication.py'), 'list', '--account', account, '--root', data)
        require(not empty['publications'], 'a plan must not create publication records')
        caption = json.loads((skills / 'ig-carousel/example.tr.json').read_text(encoding='utf-8'))['caption']
        cleaned = workflow.call('humanize-caption', tool('ig-human/humanize.py'), '--language', 'tr', '--json', text=caption)
        lint = workflow.call('lint-caption', tool('ig-caption/caption.py'), '--language', 'tr', '--json', text=cleaned['text'], codes=(0, 1))
        require(cleaned['language'] == lint['language'] == scenario['language'], 'caption language drift')
        require(lint['verdict'] != 'FIX', 'caption contains a structural failure')
        detect = workflow.call('editorial-check', tool('ig-human/detect.py'), '--language', 'tr', '--json', text=cleaned['text'])
        require(detect['language'] == 'tr' and detect['checks']['VOICE']['score'] is None,
                'Turkish unsupported voice check must remain N/A')
        report['editorial_reviews'] = [check for check in lint['checks'] if check['status'] != 'PASS']
        report['editorial_reviews'].append({'check': 'text-diagnostics', 'status': detect['verdict'],
                                           'detail': f"Metin denetimi: {detect['verdict']}; Türkçe marka sesi puanı N/A. Bunlar editoryal ipuçlarıdır."})
        report['editorial_reviews'].append({'check': 'manual-review', 'status': 'REQUIRED',
                                           'detail': 'Doğal Türkçe, marka sesi ve tüm görseller insan tarafından incelenmeli; puan için metin değiştirilmedi.'})
        jobs = []
        for slot in scenario['slots']:
            job = json.loads((skills / 'ig-carousel/example.tr.json').read_text(encoding='utf-8'))
            job['caption'] = cleaned['text']
            job['slides'][0]['title'] = slot['cover']
            job['slides'][0]['alt_text'] = f"Kurgusal kapak: {slot['cover']} Krem zemin üzerinde koyu yeşil yazı."
            source = out / (slot['content_id'] + '.json'); dump(source, job)
            export = out / slot['content_id']
            manifest = workflow.call('render-' + slot['variant'], tool('ig-carousel/render.py'), source,
                                     '--font', font, '--out', export)
            require(manifest['account'] == account and manifest['language'] == scenario['language'], 'export account/language drift')
            require((export / 'caption.txt').read_text(encoding='utf-8').strip() == cleaned['text'].strip(), 'caption changed during export')
            for slide in manifest['slides']:
                require(slide['alt_text'] and hashlib.sha256((export / slide['file']).read_bytes()).hexdigest() == slide['sha256'], 'missing alt text or changed PNG')
                from PIL import Image
                with Image.open(export / slide['file']) as image:
                    require(image.size == (1080, 1350) and image.mode == 'RGB', 'incorrect PNG format')
            jobs.append(manifest)
        report['checks'].append({'stage': 'content-and-exports', 'exports': len(jobs), 'slides': sum(len(j['slides']) for j in jobs), 'caption_verdict': lint['verdict']})
        # Fixed fictional rows are selected by scenario IDs, not by observed performance.
        fixture = skills / 'ig-audit/example.synthetic.csv'
        rows = list(csv.DictReader(io.StringIO(fixture.read_text(encoding='utf-8'))))
        selected = [row for row in rows if row['post_id'] in {s['post_id'] for s in scenario['slots']}]
        require(len(selected) == len(scenario['slots']), 'scenario post IDs do not match CSV fixture')
        csv_path = out / 'insights.synthetic.csv'
        with csv_path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(selected)
        for slot in scenario['slots']:
            row = next(row for row in selected if row['post_id'] == slot['post_id'])
            publication = {key: row[key] for key in ('account', 'post_id', 'format', 'distribution', 'published_at')}
            publication.update(content_id=slot['content_id'], reference='Kurgusal yayın bildirimi; gerçek platform yayını yapılmadı.')
            source = out / (slot['content_id'] + '-publication.json'); dump(source, publication)
            workflow.call('record-' + slot['variant'], tool('ig-account/publication.py'), 'record', source,
                          '--account', account, '--root', data)
        reconciled = workflow.call('reconcile', tool('ig-account/publication.py'), 'reconcile', csv_path, '--account', account, '--root', data)
        require(len(reconciled['matched']) == 2 and not any(reconciled[key] for key in ('identity_conflicts', 'csv_without_record', 'records_without_csv')), 'publication/CSV identity mismatch')
        ledger_file = Path(context['paths']['publications'])
        ledger_hash = hashlib.sha256(ledger_file.read_bytes()).hexdigest()
        workflow.call('duplicate-publication-rejected', tool('ig-account/publication.py'), 'record', source,
                      '--account', account, '--root', data, codes=(2,), json_output=False)
        require(hashlib.sha256(ledger_file.read_bytes()).hexdigest() == ledger_hash, 'duplicate attempt modified the ledger')
        conflicting_csv = out / 'conflicting.synthetic.csv'
        with conflicting_csv.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader()
            writer.writerows([{**selected[0], 'distribution': 'paid'}, selected[1]])
        conflict = workflow.call('conflicting-csv-disclosed', tool('ig-account/publication.py'), 'reconcile', conflicting_csv,
                                 '--account', account, '--root', data)
        require(len(conflict['identity_conflicts']) == 1 and
                'distribution' in conflict['identity_conflicts'][0]['fields'], 'distribution conflict was hidden')
        probe = workflow.call('wrong-account-rejected', tool('ig-account/publication.py'), 'check', source,
                              '--account', other, '--root', data, codes=(2,), json_output=False)
        require('account' in probe['stderr'], 'cross-account rejection has no useful explanation')
        saved = workflow.call('save-audit', tool('ig-audit/analyse.py'), csv_path, '--account', account,
                              '--primary-metric', 'shares_per_reach', '--root', data, '--save')
        require(Path(saved['saved_to']).is_relative_to(Path(context['directory'])), 'audit saved outside selected account')
        audit_report = json.loads((Path(saved['saved_to']) / 'report.json').read_text(encoding='utf-8'))
        require(audit_report['account'] == account and audit_report['post_count'] == 2, 'audit scope drift')
        require(audit_report['posts'][0]['metrics']['shares_per_reach'] == .02 and audit_report['posts'][1]['metrics']['shares_per_reach'] == .04, 'incorrect rates across the handoff')
        final = dict(original, assignments=[{'post_id': s['post_id'], 'variant': s['variant']} for s in scenario['slots']])
        final_path = out / 'experiment-after.json'; dump(final_path, final)
        waiting = workflow.call('review-before-date', tool('ig-plan/experiment.py'), final_path,
                                '--account', account, '--csv', csv_path, '--as-of', '2026-09-11T12:00:00+03:00')
        require(waiting['status'] == 'waiting_for_review' and waiting['review']['minimum_effect_met'] is None, 'premature comparison')
        saved = workflow.call('save-test-review', tool('ig-plan/experiment.py'), final_path, '--account', account,
                              '--csv', csv_path, '--as-of', scenario['as_of'], '--root', data, '--save')
        require(Path(saved['saved_to']).is_relative_to(Path(context['directory'])), 'test saved outside selected account')
        result = json.loads((Path(saved['saved_to']) / 'report.json').read_text(encoding='utf-8'))
        require(result['status'] == 'ready_descriptive' and result['review']['variant_minus_control'] == .02, 'incorrect test comparison')
        require(result['review']['source_sha256'] == audit_report['source_sha256'], 'audit/test input mismatch')
        partial_csv = out / 'partial.synthetic.csv'
        with partial_csv.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerow(selected[0])
        incomplete = workflow.call('incomplete-review-blocked', tool('ig-plan/experiment.py'), final_path,
                                   '--account', account, '--csv', partial_csv, '--as-of', scenario['as_of'])
        require(incomplete['status'] == 'incomplete' and incomplete['review']['minimum_effect_met'] is None,
                'missing observation produced a final criterion')
        require(hashlib.sha256(other_voice.read_bytes()).hexdigest() == sentinel and not Path(second['paths']['publications']).exists(), 'another account was modified')
        require([p for p in Path(second['directory']).rglob('*') if p.is_file()] == [other_voice], 'unexpected files in second account')
        require(len(list((Path(context['directory']) / 'experiments').glob('*/report.json'))) == 2, 'prospective plan snapshot was overwritten')
        require(Path(context['paths']['plan']).read_text(encoding='utf-8') == plan, 'saved plan was overwritten')
        handoff = ('# Kurgusal değerlendirme ve sonraki plan için not\n\n'
                   'Kaynak: aynı CSV, iki organik karusel, içerik başına 168 saat.\n'
                   'Gözlem: 16/800 = %2 ve 40/1000 = %4 paylaşım/erişim; fark 2 yüzde puan.\n'
                   'Her grupta yalnızca bir kurgusal içerik var. Konu, zaman ve kitle etkileri ayrıştırılamaz.\n'
                   'Otomatik ölçekleme kararı yok. Gerçek kullanımda kullanıcıyla devam/revizyon kararı verilir.\n'
                   f"Sonraki planın kapasite sınırı korunur: {scenario['weekly_minutes']} dakika.\n"
                   'Bu not sabit bir test çıktısıdır; modelin strateji üretimini doğrulamaz.\n')
        Path(context['paths']['results']).write_text(handoff, encoding='utf-8')
        (out / 'handoff.tr.md').write_text(handoff, encoding='utf-8')
        report['checks'].append({'stage': 'publication-audit-test', 'matched_posts': 2, 'rates': [.02, .04], 'difference': .02, 'comparison': 'descriptive-only'})
        report['checks'].append({'stage': 'isolation-and-history', 'second_account_unchanged': True, 'plan_snapshots': 2, 'early_comparison_blocked': True})
        report['checks'].append({'stage': 'failure-paths', 'duplicate_rejected': True,
                                 'identity_conflict_disclosed': True, 'incomplete_review_blocked': True,
                                 'wrong_account_rejected': True})
        report['status'] = 'passed_with_manual_review'
    except Exception as error:
        report.update(status='failed', error=str(error))
        raise
    finally:
        report['command_count'] = len(workflow.steps)
        report['artifacts'] = {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted(out.rglob('*')) if p.is_file() and 'skills' not in p.relative_to(out).parts
                               and p.name not in ('report.json', 'report.md') and '__pycache__' not in p.parts}
        dump(out / 'report.json', report)
        lines = ['# Uçtan uca doğrulama', '', f"Sonuç: {report['status']}", '',
                 'Bu rapor kurgusal verilerle yerel araç entegrasyonunu sınar.', '',
                 '## Kontroller', '']
        for check in report['checks']:
            if check['stage'] == 'plan-fixture':
                lines.append(f"- Plan örneği: {check['minutes']}/{check['capacity']} dakika; kapasite sınırı korundu.")
            elif check['stage'] == 'content-and-exports':
                lines.append(f"- İçerik: {check['exports']} karusel, {check['slides']} PNG; açıklama sonucu {check['caption_verdict']}.")
            elif check['stage'] == 'publication-audit-test':
                lines.append('- Yayın–CSV–deneme eşleşmesi: 2 içerik; paylaşım/erişim %2 ve %4, fark 2 yüzde puan. Betimsel sonuç.')
            elif check['stage'] == 'isolation-and-history':
                lines.append('- Diğer hesap korundu, iki plan sürümü saklandı ve erken karşılaştırma engellendi.')
            elif check['stage'] == 'failure-paths':
                lines.append('- Yanlış hesap ve yinelenen kayıt reddedildi; çelişkili CSV gösterildi; eksik veriyle nihai değerlendirme yapılmadı.')
        lines += ['', '## İnsan incelemesi', '']
        lines += ['- ' + item.get('detail', str(item)) for item in report['editorial_reviews']]
        lines += ['', '## Sınırlar', ''] + ['- ' + item for item in report['limitations']]
        if report.get('error'):
            lines += ['', 'Hata: ' + report['error']]
        (out / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='new directory; never reuses installed skills or account data')
    parser.add_argument('--font', required=True, type=Path)
    args = parser.parse_args()
    try:
        report = run(args.out, args.font)
    except (ValueError, OSError, subprocess.SubprocessError, ImportError) as error:
        parser.exit(2, f'error: {error}\n')
    print(json.dumps({'status': report['status'], 'report': str(args.out.absolute() / 'report.json')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
