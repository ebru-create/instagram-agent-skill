#!/usr/bin/env python3
"""Mevcut yerel Instagram araçları için Türkçe komut arayüzü."""
import argparse
import json
import math
from pathlib import Path
import re
import subprocess
import sys

SKILLS = Path(__file__).resolve().parent.parent
STATUS = {'READY': 'Hazır', 'REVIEW': 'İnceleme gerekiyor', 'FIX': 'Düzeltme gerekiyor',
          'PASS': 'Kontrol geçti', 'WARN': 'Uyarı', 'FAIL': 'Kontrol başarısız',
          'FLAGGED': 'İnceleme gerekiyor', 'BORDERLINE': 'Sınırda; inceleyin',
          'INSUFFICIENT TEXT': 'Değerlendirmek için metin yetersiz',
          'STRONG': 'Güçlü editoryal sinyal', 'OK': 'Orta editoryal sinyal', 'WEAK': 'Zayıf editoryal sinyal',
          'waiting_for_review': 'Değerlendirme tarihi bekleniyor', 'incomplete': 'Veriler eksik',
          'ready_descriptive': 'Betimsel karşılaştırma hazır', 'validated_plan': 'Plan biçimi geçerli',
          'recorded': 'Yayın bildirimi kaydedildi', 'revised': 'Düzeltme yeni sürüm olarak kaydedildi',
          'valid': 'Girdi biçimi geçerli', 'exported': 'Dosyalar oluşturuldu', 'checked': 'Yerleşim kontrol edildi'}
CHECKS = dict(zip(('LENGTH', 'FIRST LINE', 'HOOK IS CONCRETE', 'HASHTAGS', 'TAG PLACEMENT', 'LINKS',
                  'ONE ASK', 'EMOJI', 'SEARCH TERMS', 'SPECIFICITY', 'SLOP DENSITY', 'BURSTINESS',
                  'VOICE', 'ARTIFACTS', 'CONCRETE', 'TENSION', 'ADDRESS', 'CURIOSITY'),
                 ('Uzunluk', 'İlk satır', 'Girişin somutluğu', 'Etiketler', 'Etiket konumu', 'Bağlantılar',
                  'Tek eylem çağrısı', 'Emoji', 'Arama sözcükleri', 'Somutluk', 'Kalıp ifade yoğunluğu',
                  'Cümle çeşitliliği', 'Marka sesi', 'Biçim izleri', 'Somutluk', 'Merak gerilimi',
                  'Hitap', 'Merak')))
METRICS = {'paylasim_orani': 'shares_per_reach', 'kaydetme_orani': 'saves_per_reach',
           'takip_orani': 'follows_per_reach', 'goruntuleme': 'views', 'erisim': 'reach',
           'basvuru': 'enquiries', 'rezervasyon': 'bookings'}
CHECKS.update(FINGERPRINT='Biçim izleri', STAKES='Sonucun önemi', FRONTLOAD='Önemli bilginin konumu')
ERRORS = (
    ('unknown account', 'Hesap bulunamadı. Önce «hesap ekle HESAP_ADI» komutuyla yerel profili oluşturun.'),
    ('choose the publishing account', 'Yayın hesabını --hesap ile açıkça seçin.'),
    ('account does not match', 'Dosyadaki hesap, --hesap ile seçtiğiniz hesapla uyuşmuyor.'),
    ('post_id is already', 'Bu paylaşım kimliği daha önce kaydedilmiş.'),
    ('content_id is already', 'İçerik referansı zaten kayıtlı. Düzeltme için --duzelt seçeneğini kullanın.'),
    ('post_id already belongs', 'Bu paylaşım kimliği başka bir içerik kaydına ait.'),
    ('--revise requires', 'Düzeltme için aynı content_id ile mevcut bir kayıt gerekir.'),
    ('locked', 'Kayıt kilitli; başka bir yazma işlemi sürüyor olabilir. İşlem bitince yeniden deneyin.'),
    ('in the future', 'Yayın tarihi gelecekte. Planlanan içerikler, yayımlanmış olarak kaydedilemez.'),
    ('explicit UTC offset', 'Tarihe saat dilimi ekleyin. Örnek: 2026-09-01T12:00:00+03:00'),
    ('captured_at must be after', 'Ölçüm tarihi, yayın tarihinden sonra olmalıdır.'),
    ('post_id must be nonempty and unique', 'Her satırda benzersiz, dolu bir post_id olmalı; aynı paylaşımı iki kez eklemeyin.'),
    ('unknown CSV columns', 'CSV sütunları tanınmıyor. Sütunları template.csv şemasına eşleştirin.'),
    ('unique headers and all identity columns', 'CSV başlıkları benzersiz olmalı; hesap, kimlik, format, dağıtım ve tarih sütunları eksiksiz bulunmalı.'),
    ('CSV contains no posts', 'CSV içinde değerlendirilecek içerik yok.'),
    ('column count', 'CSV satırındaki hücre sayısı başlık sayısıyla uyuşmuyor.'),
    ('requires a nonnegative full number', 'Sayısal hücrelere negatif olmayan tam sayı yazın; eksik veriyi boş bırakın. K/M/B kısaltması kullanmayın.'),
    ('cannot exceed', 'Alt küme sayısı toplam sayıyı aşıyor; erişim veya izleyici sayılarını kontrol edin.'),
    ('schema_version', 'Dosyanın şema sürümünü kontrol edin; desteklenen değer 1.'),
    ('fields must match', 'JSON alanları beklenen şemayla uyuşmuyor. İlgili örnek dosyayı temel alın.'),
    ('duplicate JSON key', 'JSON içinde yinelenen alan adı var.'),
    ('invalid publication', 'Yayın kayıt dosyası bozuk veya biçimi geçersiz. Mevcut dosya korunmuştur.'),
    ('symbolic link', 'Hesap yolu sembolik bağlantı içeriyor; normal bir yerel klasör/dosya kullanın.'),
    ('regular file', 'Hesap yolu normal bir dosya olmalıdır.'),
    ('optional Pillow', 'Karusel için Pillow gerekir: python3 -m pip install -r skills/ig-carousel/requirements.txt'),
    ('existing TrueType', 'Türkçe karakterleri içeren mevcut bir TTF/OTF dosyasını --yazi-tipi ile seçin.'),
    ('new output directory', 'Mevcut dışa aktarma klasörü korunuyor. --cikti için yeni bir klasör seçin.'),
    ('overflow', 'Metin karta sığmıyor. Metni kısaltın veya yeni bir karta bölün.'),
    ('too wide', 'Bir sözcük karta sığmıyor. Sözcüğü veya kart metnini düzenleyin.'),
    ('contrast', 'Yazı ve arka planın kontrastı yetersiz; renkleri düzenleyin.'),
    ('no glyph', 'Yazı tipinde gerekli karakter yok; uygun bir yazı tipi seçin.'),
    ('nothing to score', 'Değerlendirilecek giriş cümlesi yok.'),
    ('empty script', 'Süre hesaplanacak metin boş.'),
    ('no usable rows', 'Araştırma dosyasında kullanılabilir satır yok; sekmeyle ayrılmış TSV biçimini kontrol edin.'),
    ('No such file', 'Dosya bulunamadı. Dosya yolunu kontrol edin.'),
    ('Permission denied', 'Dosyaya erişim izni yok. Okuma/yazma izinlerini kontrol edin.'),
    ('lexicon language', 'Sözcük listesi seçilen içerik diliyle uyuşmuyor.'),
    ('--data-root requires', '--kok seçeneğiyle birlikte --hesap seçilmelidir.'),
    ('unsupported primary metric', 'Ana ölçüt tanınmıyor. --olcut için geçerli bir ölçüt adı seçin.'),
)


def localized_error(message):
    if 'Pozitif, sonlu' in message:
        return 'Pozitif, sonlu bir sayı girin; ondalık ayırıcı olarak nokta kullanın.'
    if 'the following arguments are required:' in message:
        return 'Gerekli alanlar eksik: ' + message.split('required:', 1)[1].strip()
    if message.startswith('unrecognized arguments:'):
        return 'Tanınmayan seçenekler: ' + message.split(':', 1)[1].strip()
    if 'invalid choice:' in message:
        return 'Seçenek değeri tanınmıyor. Kullanılabilir değerler için ilgili komutu --help ile açın.'
    if 'expected one argument' in message:
        return 'Seçenekten sonra bir değer yazılmalıdır.'
    if 'not allowed with argument' in message:
        return 'Birlikte kullanılamayan seçenekler seçildi. --kontrol veya --cikti seçeneklerinden birini kullanın.'
    if "can't open" in message or 'FileNotFoundError' in message:
        return 'Dosya bulunamadı. Dosya yolunu kontrol edin.'
    if 'JSONDecodeError' in message or 'Expecting ' in message:
        return 'JSON okunamadı. Tırnakları, virgülleri ve dosya biçimini kontrol edin.'
    for fragment, translated in ERRORS:
        if fragment in message:
            line = re.search(r'CSV line (\d+)', message)
            return (f"CSV satırı {line[1]}: " if line else '') + translated
    return 'İşlem tamamlanamadı. Teknik ayrıntı için aynı komuta --ayrinti ekleyin.'


class TurkishParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs['add_help'] = False
        super().__init__(*args, **kwargs)
        self.add_argument('-h', '--help', action='help', help='bu yardım metnini göster')
    def format_help(self):
        return super().format_help().replace('usage:', 'Kullanım:').replace('positional arguments:', 'Konumsal alanlar:').replace('options:', 'Seçenekler:')
    def error(self, message):
        self.exit(2, 'Hata: ' + localized_error(message) + '\n')


def positive_float(value):
    try:
        number = float(value)
        if math.isfinite(number) and number > 0:
            return number
    except ValueError:
        pass
    raise argparse.ArgumentTypeError('Pozitif, sonlu bir sayı girin; ondalık ayırıcı olarak nokta kullanın.')


def parser():
    root = TurkishParser(description='Instagram araçlarını Türkçe yardım ve özetlerle kullanın. Yerel dosyalarla çalışır; paylaşım yapmaz.')
    commands = root.add_subparsers(dest='command', required=True, title='Komutlar', metavar='KOMUT')
    labels = {'hesap': 'yerel hesap profilleri', 'aciklama': 'açıklama denetimi', 'temizle': 'metni temizle',
              'metin': 'metin için editoryal denetim', 'giris': 'giriş cümlesini değerlendir', 'ritim': 'konuşma süresi tahmini',
              'arastirma': 'TSV araştırmasını karşılaştır', 'karusel': 'PNG dışa aktar', 'analiz': 'CSV oranlarını hesapla',
              'deneme': 'içerik denemesini kontrol et', 'yayin': 'bildirilen yayınları kaydet/eşleştir'}
    for name, label in labels.items():
        sub = commands.add_parser(name, help=label, description=label.capitalize())
        if name in ('hesap', 'yayin'):
            nested = sub.add_subparsers(dest='action', required=True, title='İşlemler', metavar='İŞLEM')
            actions = {'listele': 'kayıtları listele', 'ekle': 'hesap oluştur', 'goster': 'hesap yollarını göster'} if name == 'hesap' else {'kontrol': 'JSON girdisini kontrol et', 'kaydet': 'yayın bildirimi kaydet', 'listele': 'son yayın kayıtları', 'eslestir': 'CSV kimliklerini eşleştir'}
            for action, description in actions.items():
                leaf = nested.add_parser(action, help=description, description=description)
                common(leaf)
                leaf.add_argument('--kok', help='yerel hesap verileri kök klasörü')
                if name == 'hesap' and action == 'ekle':
                    leaf.add_argument('hesap_adi', help='oluşturulacak yayın hesabı')
                elif action != 'listele' or name == 'yayin':
                    leaf.add_argument('--hesap', required=True, help='yayın hesabının adı')
                if name == 'yayin' and action in ('kontrol', 'kaydet', 'eslestir'):
                    leaf.add_argument('dosya', help='yayın JSON dosyası veya eşleştirilecek CSV')
                if name == 'yayin' and action == 'kaydet':
                    leaf.add_argument('--duzelt', action='store_true', help='aynı content_id için önceki sürümü koruyan düzeltme')
            continue
        common(sub)
        sub.add_argument('dosya', nargs='?' if name in ('aciklama', 'temizle', 'metin', 'giris', 'ritim', 'arastirma') else None,
                         default='-', help='girdi dosyası; metin araçlarında - standart girdiyi okur')
        if name in ('aciklama', 'temizle', 'metin', 'giris', 'ritim', 'arastirma'):
            sub.add_argument('--dil', choices=('tr', 'en'), default='tr', help='içerik dili; varsayılan tr, arayüz Türkçe kalır')
        if name == 'aciklama':
            sub.add_argument('--kelimeler', default='', help='virgülle ayrılmış arama sözcükleri')
        if name in ('temizle', 'metin'):
            sub.add_argument('--sozcuk-listesi', help='içerik diliyle eşleşen tam sözcük listesi JSON dosyası')
            sub.add_argument('--tipografiyi-koru', action='store_true', help='kullanıcının noktalamasını koru')
        if name == 'giris':
            sub.add_argument('--metin', help='dosya yerine tek bir giriş cümlesi')
        if name == 'ritim':
            sub.add_argument('--hiz', type=positive_float, default=140, help='dakikadaki sözcük sayısı; varsayılan 140, kendi ölçümünüzü kullanın')
            sub.add_argument('--hedef', type=positive_float, help='hedef süre, saniye')
        if name in ('analiz', 'deneme', 'arastirma'):
            sub.add_argument('--hesap', required=name != 'arastirma', help='yayın hesabının adı')
            sub.add_argument('--kok', help='yerel hesap verileri kök klasörü')
        if name in ('analiz', 'deneme'):
            sub.add_argument('--kaydet', action='store_true', help='başlatılmış hesapta yeni rapor kaydet')
        if name == 'analiz':
            sub.add_argument('--olcut', required=True, help='ör. paylasim_orani, kaydetme_orani, takip_orani, goruntuleme, erisim; özgün ölçüt adları da geçerli')
        if name == 'deneme':
            sub.add_argument('--csv', help='kanonik CSV; yoksa yalnızca plan kontrol edilir')
            sub.add_argument('--tarih', help='saat dilimli değerlendirme zamanı; ör. 2026-09-13T12:00:00+03:00')
        if name == 'karusel':
            sub.add_argument('--yazi-tipi', required=True, help='Türkçe karakterleri içeren TTF/OTF dosyası')
            sub.add_argument('--kalin-yazi-tipi', help='başlıklar için isteğe bağlı yazı tipi')
            mode = sub.add_mutually_exclusive_group(required=True)
            mode.add_argument('--kontrol', action='store_true', help='dosya üretmeden yerleşimi kontrol et')
            mode.add_argument('--cikti', help='yeni dışa aktarma klasörü')
    return root


def common(sub):
    sub.add_argument('--json', action='store_true', help='özgün JSON çıktısını ve çıkış kodunu koru; alan adları çevrilmez')
    sub.add_argument('--ayrinti', action='store_true', help='özgün teknik tanıları da göster; İngilizce olabilir')


def invocation(args):
    name = args.command
    if name == 'hesap':
        command = ['account.py']; options = ['--root', args.kok] if args.kok else []
        options += [{'listele': 'list', 'ekle': 'init', 'goster': 'show'}[args.action]]
        options += [args.hesap_adi] if args.action == 'ekle' else (['--account', args.hesap] if args.action == 'goster' else [])
        return SKILLS / 'ig-account' / command[0], options
    if name == 'yayin':
        options = [{'kontrol': 'check', 'kaydet': 'record', 'listele': 'list', 'eslestir': 'reconcile'}[args.action]]
        if hasattr(args, 'dosya'):
            options.append(args.dosya)
        options += ['--account', args.hesap]
        if args.kok:
            options += ['--root', args.kok]
        if getattr(args, 'duzelt', False):
            options += ['--revise']
        return SKILLS / 'ig-account/publication.py', options
    paths = {'aciklama': 'ig-caption/caption.py', 'temizle': 'ig-human/humanize.py', 'metin': 'ig-human/detect.py',
             'giris': 'ig-reel/hookscore.py', 'ritim': 'ig-reel/beats.py', 'arastirma': 'ig-viral/swipe.py',
             'karusel': 'ig-carousel/render.py', 'analiz': 'ig-audit/analyse.py', 'deneme': 'ig-plan/experiment.py'}
    options = [args.dosya]
    if name in ('aciklama', 'temizle', 'metin', 'giris', 'ritim', 'arastirma'):
        options += ['--language', args.dil, '--json']
    for attribute, flag in (('kelimeler', '--keywords'), ('sozcuk_listesi', '--lexicon'), ('hiz', '--wpm'),
                            ('hedef', '--target'), ('metin', '--hook'), ('yazi_tipi', '--font'),
                            ('kalin_yazi_tipi', '--font-bold'), ('cikti', '--out'), ('csv', '--csv'), ('tarih', '--as-of')):
        value = getattr(args, attribute, None)
        if value is not None and value != '':
            options += [flag, str(value)]
    for attribute, flag in (('tipografiyi_koru', '--preserve-typography'), ('kaydet', '--save'), ('kontrol', '--check')):
        if getattr(args, attribute, False):
            options.append(flag)
    if getattr(args, 'hesap', None):
        options += ['--account', args.hesap]
    if getattr(args, 'kok', None):
        options += ['--data-root' if name == 'arastirma' else '--root', args.kok]
    if name == 'analiz':
        options += ['--primary-metric', METRICS.get(args.olcut, args.olcut)]
    return SKILLS / paths[name], options


def number(value, percent=False):
    if value is None:
        return 'Veri yok / hesaplanamıyor'
    if percent:
        return f'%{value * 100:.2f}'.replace('.', ',')
    return str(round(value, 3) if isinstance(value, float) else value).replace('.', ',')


def is_rate(metric):
    return metric.endswith('_rate') or metric.endswith('_per_reach') or metric == 'hold_3s'


def summary(args, data):
    if isinstance(data, list):
        return '\n\n'.join(summary(args, row) for row in data) if data else 'Kayıt bulunamadı.'
    lines = []
    owner = data.get('account') or data.get('owner_account') or data.get('publication', {}).get('account')
    if owner:
        lines.append('Hesap: @' + owner)
    if 'saved_to' in data:
        lines += [STATUS.get(data.get('status'), 'Rapor kaydedildi'), 'Kayıt konumu: ' + data['saved_to']]
        if args.command == 'yayin':
            lines.append('Kullanıcı bildirimi; platformdan doğrulanmadı.')
        return '\n'.join(lines)
    if args.command == 'hesap':
        if args.action == 'listele':
            return '\n'.join('@' + account for account in data['accounts']) or 'Kayıtlı hesap yok.'
        names = {'voice': 'Marka sesi', 'strategy': 'Strateji', 'plan': 'Plan', 'swipe': 'Araştırma',
                 'log': 'Taslak günlüğü', 'results': 'Sonuçlar', 'publications': 'Yayın kayıtları',
                 'lexicon': 'İngilizce sözcük listesi', 'lexicon_tr': 'Türkçe sözcük listesi'}
        lines += [f'{names.get(key, key)}: {value}' for key, value in data['paths'].items()]
        lines.append('Bunlar yerel dosya yollarıdır; dosyalar henüz oluşturulmamış olabilir.')
    elif args.command == 'aciklama':
        lines += ['Açıklama: ' + STATUS.get(data['verdict'], 'İnceleyin'), f"Karakter: {data['characters']}/{data['limit']}",
                  'Görünür bölüm: ' + data['visible'], 'Denetimler:']
        lines += [f"- {CHECKS.get(row['check'], 'Ek denetim')}: {STATUS.get(row['status'], 'İnceleyin')}" for row in data['checks']]
        advice = {'LENGTH': 'Metni uzunluk sınırı içinde düzenleyin.',
                  'FIRST LINE': 'İlk satırı ve görünür bölümdeki kesilmeyi kontrol edin.',
                  'HOOK IS CONCRETE': 'Somutluk kontrolü sınırlıdır; yazıyla belirtilen sayıları ve bağlamı elle inceleyin.',
                  'HASHTAGS': 'Etiket sayısını ve fazla genel etiketleri kontrol edin.',
                  'TAG PLACEMENT': 'Etiketlerin ilk satırdaki yerini kontrol edin.',
                  'LINKS': 'Bağlantıların içerikteki yerini ve amacını kontrol edin.',
                  'ONE ASK': 'İçeriğin tek bir eylem çağrısına odaklanmasını inceleyin.',
                  'EMOJI': 'Emoji yoğunluğunu gözden geçirin.',
                  'SEARCH TERMS': 'İstenen arama sözcüklerinin doğal biçimde metinde bulunduğunu kontrol edin.'}
        lines += [advice[row['check']] for row in data['checks'] if row['status'] != 'PASS' and row['check'] in advice]
        lines.append(f"Bulunan eylem çağrısı: {len(data['asks'])}; etiket: {len(data['hashtags'])}.")
        lines.append('Uyarılar yayın onayı değildir. Ayrıntılı tanılar: --ayrinti.')
    elif args.command == 'temizle':
        lines += ['Temizlenen metin:', data['text'].rstrip(), 'Değişiklik sayıları:']
        labels = {'invisible': 'Görünmez karakterler', 'typographic': 'Tipografi', 'lexical': 'Sözcük değişimleri', 'structures': 'İncelenecek yapılar'}
        lines += [f"{labels[key]}: {sum(row.get('count', 1) for row in value)}" for key, value in data['report'].items()]
    elif args.command in ('metin', 'giris'):
        lines += ['Sonuç: ' + STATUS.get(data['verdict'], 'İnceleyin')]
        if 'hook' in data:
            lines.append('Giriş: ' + data['hook'])
        lines += [f"- {CHECKS.get(key, 'Ek denetim')}: {number(value['score'])}" for key, value in data['checks'].items()]
        if data.get('flags'):
            lines.append(f"İncelenecek ek durum: {len(data['flags'])}; ayrıntılı tanılar için --ayrinti.")
        lines.append('Puanlar editoryal ipucudur; yazarlık veya izlenme başarısı kanıtı değildir.')
    elif args.command == 'ritim':
        lines += [f"Toplam: yaklaşık {number(data['total_seconds'])} saniye; {data['total_words']} sözcük.", f"Hız: {number(data['wpm'])} sözcük/dakika."]
        lines += [f"{number(row['start'])} sn · {number(row['dur'])} sn: {row['text']}" for row in data['beats']]
        lines.append(f"İncelenecek not: {len(data['notes'])}. Süre tahmindir; kendi sesli okumanızla kontrol edin.")
    elif args.command == 'arastirma':
        lines += [f"Araştırma: {data['n']} içerik; {data['accounts']} hesap.", 'Farklı karşılaştırma temelleri ayrı tutulur.']
        for group in data['groups']:
            baseline = {'account median': 'Hesabın medyanına göre', 'follower count': 'Takipçi sayısına göre (dolaylı ölçüt)', 'unavailable': 'Karşılaştırma temeli yok'}[group['baseline']]
            lines.append(f"{baseline}: {group['n']} içerik.")
            lines += [f"{row.get('account', '')}: {number(row.get('outlier'))} kat · {row['hook']}" for row in group['reels']]
        lines.append('Takipçi oranları, hesap medyanına göre hesaplanan katlarla aynı ölçü değildir; ayrıntı için --ayrinti.')
    elif args.command == 'karusel':
        lines += [STATUS[data['status']], f"Boyut: {data['width']} × {data['height']} piksel.",
                  f"Kart sayısı: {data.get('slide_count', len(data['slides']))}", 'Yayın yapılmadı; görselleri ve alternatif metinleri inceleyin.']
        if args.cikti:
            lines.append('Çıktı konumu: ' + args.cikti)
    elif args.command == 'analiz':
        metric = data['primary_metric']; rate = is_rate(metric)
        lines += [f"İçerik sayısı: {data['post_count']}", 'Ana ölçüt: ' + args.olcut]
        formats = {'reel': 'Reels', 'carousel': 'Karusel', 'image': 'Görsel', 'story': 'Hikâye'}
        distribution = {'organic': 'Organik', 'paid': 'Ücretli', 'unknown': 'Dağıtım bilinmiyor'}
        for group in data['cohorts']:
            lines.append(f"{formats[group['format']]} · {distribution[group['distribution']]} · {number(group['observation_seconds'] / 3600)} saat · {group['n']} içerik; kullanılabilir ölçüm {group['coverage'][metric]}.")
            lines += [f"  {row['post_id']}: {number(row['metrics'][metric], rate)}" for row in data['posts'] if row['cohort'] == group['id']]
        lines += [f"Karşılaştırma grubu sayısı: {len(data['cohorts'])}", 'Eksik değer sıfır değildir. Oranlar yüzde olarak gösterilir; sonuçlar nedensellik kanıtı değildir.']
    elif args.command == 'deneme':
        lines.append(STATUS[data['status']])
        if 'review' in data:
            review = data['review']
            lines += [f"Kontrol: {review['groups']['control']['usable_n']} kullanılabilir içerik.",
                      f"Diğer yaklaşım: {review['groups']['variant']['usable_n']} kullanılabilir içerik.",
                      f"Dışarıda kalan atama: {len(review['excluded_assignments'])}.",
                      ('Fark (yüzde puan): ' + number(review['variant_minus_control'] * 100 if review['variant_minus_control'] is not None else None)
                       if is_rate(data['plan']['primary_metric']) else 'Fark (özgün ölçüt biriminde): ' + number(review['variant_minus_control']))]
            criterion = review['minimum_effect_met']
            lines.append('Seçilen fark eşiği: ' + ('Değerlendirilemedi' if criterion is None else 'Karşılandı' if criterion else 'Karşılanmadı'))
        lines.append('Hazır olması veya eşiği aşması istatistiksel anlamlılık ya da nedensel üstünlük göstermez.')
    elif args.command == 'yayin':
        if args.action == 'kontrol':
            lines += ['Yayın girdisinin biçimi geçerli.', 'Platformdan doğrulanmadı.']
        elif args.action == 'listele':
            lines += [f"Yayın sayısı: {len(data['publications'])}; toplam kayıt sürümü: {data['revision_count']}."]
            lines += [f"{row['content_id']} → {row['post_id']} · sürüm {row['revision']}" for row in data['publications']]
            lines.append('Kullanıcı bildirimleri; platformdan doğrulanmadı.')
        else:
            lines += [f"Eşleşen yayın: {len(data['matched'])}", f"Kimlik uyuşmazlığı: {len(data['identity_conflicts'])}",
                      f"Kaydı olmayan CSV içeriği: {len(data['csv_without_record'])}", f"CSV'de olmayan kayıt: {len(data['records_without_csv'])}"]
            names = {'format': 'format', 'distribution': 'organik/ücretli dağıtım', 'published_at': 'yayın tarihi'}
            lines += [row['post_id'] + ': ' + ', '.join(names[key] for key in row['fields']) for row in data['identity_conflicts']]
            lines.append('Kaynaklar değiştirilmedi; eksik satır, yayının yapılmadığını göstermez.')
    return '\n'.join(lines)


def main():
    ap = parser(); args = ap.parse_args()
    program, options = invocation(args)
    if not program.is_file():
        ap.exit(2, 'Hata: Gerekli araç bulunamadı. Bütün beceri paketini yeniden kurun.\n')
    stdin = sys.stdin.read() if getattr(args, 'dosya', None) == '-' and not getattr(args, 'metin', None) else None
    try:
        result = subprocess.run([sys.executable, str(program), *options], input=stdin, text=True, capture_output=True)
    except OSError:
        ap.exit(2, 'Hata: Python aracı başlatılamadı. Kurulum ve dosya izinlerini kontrol edin.\n')
    if args.json:
        sys.stdout.write(result.stdout); sys.stderr.write(result.stderr)
        return result.returncode
    try:
        data = json.loads(result.stdout)
    except ValueError:
        print('Hata: ' + localized_error(result.stderr or result.stdout), file=sys.stderr)
        if args.ayrinti:
            print(result.stderr or result.stdout, file=sys.stderr, end='')
        return 2
    print(summary(args, data))
    if args.ayrinti:
        print('\nÖzgün teknik çıktı (İngilizce alanlar içerebilir):', file=sys.stderr)
        sys.stderr.write(result.stdout + result.stderr)
    elif result.stderr:
        print('Araç ek teknik not üretti; görmek için --ayrinti kullanın.', file=sys.stderr)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
