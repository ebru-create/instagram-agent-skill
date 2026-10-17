# Türkçe hızlı başlangıç

Bu paket; içerik planlama, taslak hazırlama, karusel dosyası üretme ve sağladığınız
sonuçları değerlendirme araçları sunar. CLI araçları yerel dosyalarla çalışır.
İçerik yazmak için becerileri yükleyen bir asistan kullanılır; pakette model yoktur.
Taslağı inceleyip kendi yayın akışınızda paylaşırsınız.

## 1. Kur

Python 3.10 veya üzeri gerekir. Depo kökünde:

```bash
git clone https://github.com/ebru-create/instagram-agent-skill.git
cd instagram-agent-skill
python3 scripts/install.py --host codex --dry-run
python3 scripts/install.py --host codex
python3 scripts/install.py --host codex --check
```

Codex hedefi `~/.agents/skills` klasörüdür. Claude Code için `--host claude-code`
kullan; `--host` verilmezse eski `~/.claude/skills` hedefi korunur.
Genel ajanlar için `--host generic --skills-dir PATH` kullan.
[Ortam seçimi ve yerel modeller](hosts.md) gereksinimleri açıklar. Projeye özel kurulum için her
komuta aynı `--skills-dir /path/to/proje/.claude/skills` eklenir.
İndirilen hazırlanmış ZIP'te klasörü açıp aynı kurulum komutlarını çalıştırın;
`git clone` gerekmez. [Güncelleme ve yedekleme](installation.md) ayrıntıları.

## 2. Hesabını seç

Aşağıda `HESAP_ADI` yerine kendi yayın hesabını yaz:

```bash
python3 skills/ig-account/turkce.py hesap ekle HESAP_ADI
python3 skills/ig-account/turkce.py hesap goster --hesap HESAP_ADI
```

Gösterilen `voice.md` yoluna kendi metinlerinden örnekler, içerik dili ve sen/siz
tercihini; `strategy.md` yoluna hedef, zaman bütçesi, üretilebilir formatlar ve
ölçüm ölçütünü kaydet. [Ses](../templates/voice.md) ve
[strateji](../templates/strategy.md) şablonları başlangıç içindir. Bilinmeyen
bilgileri boş bırak; hesap oluşturmak bu dosyaları otomatik doldurmaz.

Birden fazla hesapta aynı hesabı tüm adımlara açıkça geçir. Araştırılan veya
mesaj yazılan hesap, yayın hesabını değiştirmez. Asistana örneğin şöyle yaz:

```text
ig-plan becerisini kullan: @HESAP_ADI için gelecek haftayı planla.
Hedefim nitelikli atölye başvurusu. Haftada 90 dakikam var, en fazla iki paylaşım.
Kamera karşısına geçmeden üretebilirim. Bilmediğin sonuçları veya müşteri hikâyelerini uydurma.
```

Bu bir istek örneğidir; bütçe veya hedef varsayılanınız değildir.

## 3. Metni kontrol et

Komutlar depo kökünden çalışır; kurulu kopyada aracın tam yolunu kullan.

```bash
python3 skills/ig-account/turkce.py --help
python3 skills/ig-account/turkce.py aciklama /path/to/aciklama.txt --kelimeler "atölye,uygulama"
python3 skills/ig-account/turkce.py metin /path/to/taslak.txt
python3 skills/ig-account/turkce.py giris --metin "Üç günde iki saat kazandım"
python3 skills/ig-account/turkce.py ritim /path/to/senaryo.txt --hiz 140
```

Örnek girişteki sayıyı yalnızca gerçek deneyiminse kullan. `--dil en` İngilizce
içeriği seçer; arayüz Türkçe kalır. [Komut kılavuzu](../skills/ig-account/references/turkce-kullanim.md)
tüm seçenekleri açıklar. Uyarı, değerlendirme gerektirir; sıfır çıkış kodu tek
başına onay değildir. Desteklenmeyen kontroller N/A kalır. Puanlar yazarlık veya
izlenme başarısı kanıtı değildir.

## 4. İhtiyacın olan akışa geç

| İhtiyaç | Kılavuz |
| --- | --- |
| Karusel PNG'leri, yazı tipi, açıklama ve alternatif metin | [Karusel dışa aktarma](../skills/ig-carousel/references/rendering.md) |
| Kaynak CSV'yi eşleştirme ve önizleme | [CSV içe aktarma](../skills/ig-audit/references/csv-import.md) |
| Kullanıcının bildirdiği gerçek yayın kimliğini kaydetme | [Yayın kayıtları](../skills/ig-account/references/publications.md) |
| Oranlar, eksik veri ve karşılaştırılabilir gruplar | [CSV analizi](../skills/ig-audit/references/csv-analysis.md) |
| Hipotez, ölçüt, gözlem süresi ve değerlendirme | [İçerik denemesi](../skills/ig-plan/references/experiments.md) |

Türkçe [baştan sona örnek](walkthrough.tr.md) bu adımların bağlantısını gösterir.
Örnek dosyaların tamamı kurgusaldır; hesabının sonuçları yerine kullanılmaz.

## Sık karşılaşılan durumlar

- **Hesap bulunamadı:** aynı kökte `hesap ekle` çalıştır; özel kökte ilgili komutlara
  aynı `--kok` değerini geçir.
- **Açıklama inceleme istiyor:** uyarıyı ve metni incele. `--ayrinti` özgün teknik
  tanıları gösterir; bu mesajlar İngilizce olabilir.
- **CSV engellendi:** satır/alan hatalarını ve eşleştirmeyi düzelt. Eksik değerleri
  sıfır yapma; aktarılabilen satırları tek başına sonuç gibi kullanma.
- **Karusel üretilmedi:** isteğe bağlı Pillow'u kur ve uygun yazı tipi seç;
  mevcut çıktı klasörünü yeniden kullanma. [Yerleşim kılavuzunu](../skills/ig-carousel/references/rendering.md) incele.
- **Güncellemede yerel değişiklik bulundu:** [kurulum rehberindeki](installation.md)
  kuru çalıştırma ve yedek adımlarını izle.

## Ortak hesap verileri

Kurulum hedefi hesap verisinin yerini değiştirmez. `--kok PATH` açık kökü seçer;
yoksa `INSTAGRAM_AGENT_HOME` ortam değişkeni kullanılır. Bu da verilmezse mevcut
`~/.claude/instagram` korunur; yeni kurulumlarda `~/.local/share/instagram-agent`
kullanılır. İki kök varsa eski kök önceliklidir; diğerini seçmek için açık kök
veya ortam değişkeni kullan. Hesaplar otomatik taşınmaz ve kökler arasında aranmaz.
