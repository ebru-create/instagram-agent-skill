# Türkçe komutlarla kullanım

`turkce.py`, kurulu araçları Türkçe yardım ve kısa sonuç özetleriyle çalıştırır.
Komut adları kolay yazım için Türkçe karakter içermez. Arayüz Türkçedir; metin
araçlarında içerik dili varsayılan `tr`, `--dil en` ile İngilizcedir. Dil veya
yayın hesabı tahmin edilmez. Bütün beceri paketini kurun; bu dosya tek başına yetmez.

Depo kökünden aşağıdaki yolu kullanın. Kurulu pakette aynı dosya `ig-account/`
klasöründedir; onun tam yoluyla çalıştırın.

```bash
python3 skills/ig-account/turkce.py --help
python3 skills/ig-account/turkce.py aciklama --help
```

## Metinle başlama

```bash
# Standart girdiden kısa bir açıklama; bitirmek için Ctrl-D.
python3 skills/ig-account/turkce.py aciklama --kelimeler "atölye,uygulama"

# Dosyadan metin temizleme ve editoryal kontrol.
python3 skills/ig-account/turkce.py temizle /path/to/taslak.txt --tipografiyi-koru
python3 skills/ig-account/turkce.py metin /path/to/taslak.txt

# Örnek giriş ve kendi konuşma hızınızla süre tahmini.
python3 skills/ig-account/turkce.py giris --metin "Üç günde iki saat kazandım"
python3 skills/ig-account/turkce.py ritim /path/to/senaryo.txt --hiz 140 --hedef 30

# İngilizce içerik, Türkçe arayüz.
python3 skills/ig-account/turkce.py aciklama /path/to/caption.txt --dil en
```

Giriş cümlesindeki sayı örnektir; gerçek içerikte yalnızca size ait doğrulanmış
bilgileri kullanın. Puanlar editoryal ipuçlarıdır; performans, yazarlık veya marka
sesi doğruluğu kanıtı değildir. Desteklenmeyen Türkçe marka sesi puanı
“Veri yok / hesaplanamıyor” olarak gösterilir. Doğal metni puan artırmak için
uzatmayın veya sayılar uydurmayın.

“Hazır”, aracın çalıştırdığı denetimlerin sonucu; “İnceleme gerekiyor”, mevcut
uyarıların görünür kalmasıdır. Somutluk gibi kontroller yazıyla belirtilen sayıları
ve bağlamı tam tanımaz. Kısa özet; denetim durumları, sayılar ve uygulanabilir
Türkçe öneriler gösterir. Bütün teknik tanılar için `--ayrinti` kullanın.

## Hesap ve karusel

```bash
python3 skills/ig-account/turkce.py hesap listele
python3 skills/ig-account/turkce.py hesap ekle HESAP_ADI
python3 skills/ig-account/turkce.py hesap goster --hesap HESAP_ADI

# Kurgusal örneğin yerleşimini kontrol et; isteğe bağlı Pillow ve yazı tipi gerekir.
python3 skills/ig-account/turkce.py karusel skills/ig-carousel/example.tr.json --yazi-tipi /path/to/font.ttf --kontrol
python3 skills/ig-account/turkce.py karusel skills/ig-carousel/example.tr.json --yazi-tipi /path/to/font.ttf --cikti /path/to/yeni-karusel
```

Karusel JSON'undaki hesap/language bilgisi kullanılır; bu komut onu otomatik
olarak değiştirmez. Örnekler kurgusaldır. Görselleri, alternatif metinleri ve
hesap adını inceleyin. Hiçbir komut Instagram'da yayın yapmaz.

## Yayın bildirimi, analiz ve deneme

```bash
python3 skills/ig-account/turkce.py yayin kontrol /path/to/yayin.json --hesap HESAP_ADI
python3 skills/ig-account/turkce.py yayin kaydet /path/to/yayin.json --hesap HESAP_ADI
python3 skills/ig-account/turkce.py yayin listele --hesap HESAP_ADI
python3 skills/ig-account/turkce.py yayin eslestir /path/to/insights.csv --hesap HESAP_ADI
python3 skills/ig-account/turkce.py analiz /path/to/insights.csv --hesap HESAP_ADI --olcut paylasim_orani
python3 skills/ig-account/turkce.py deneme /path/to/deneme.json --hesap HESAP_ADI --csv /path/to/insights.csv
```

İlgili komutlarda `--kok /path/to/veri` özel hesap kökünü seçer. Analiz ve denemede
`--kaydet`, önceki raporları koruyan yeni kayıt oluşturur; başlatılmış hesap gerekir.
Yayın kaydında `--duzelt`, aynı content_id altında açık bir düzeltmeyi yeni sürüm
olarak saklar. Kullanıcının bildirdiği yayın, platform tarafından doğrulanmış sayılmaz.
Denemede `--tarih` saat dilimli değerlendirme anını belirtir; verilmezse mevcut UTC
zamanı kullanılır. Deneme planının alanları çevrilmez; kendi JSON şemasını korur.

| Türkçe ölçüt seçeneği | Özgün anahtar |
| --- | --- |
| `paylasim_orani` | `shares_per_reach` |
| `kaydetme_orani` | `saves_per_reach` |
| `takip_orani` | `follows_per_reach` |
| `goruntuleme` | `views` |
| `erisim` | `reach` |
| `basvuru` | `enquiries` |
| `rezervasyon` | `bookings` |

Diğer desteklenen özgün ölçüt adları da `--olcut` ile geçerlidir. Oranlar insan
özetinde yüzde olarak, deneme farkları yüzde puan olarak gösterilir. JSON'da oran
birimi kesir olarak kalır (`0.02` = %2). Boş değer sıfıra çevrilmez. Farklı format,
dağıtım ve ölçüm yaşı grupları ayrı gösterilir. Hazır bir deneme veya karşılanan
eşik istatistiksel anlamlılık ya da nedensel üstünlük göstermez.

Araştırma için `arastirma dosya.tsv` kullanılır; `--hesap` verilirse aynı hesabın
swipe.md dosyasına kaydeder. `--kok` burada da hesabın kökünü seçer ve --hesap
ile birlikte kullanılmalıdır. Takipçi ve medyan temelleri ayrı tutulur.

## Teknik ayrıntılar ve uyumluluk

- `--json`: özgün aracın stdout/stderr ve çıkış kodunu aktarır. Alan adları,
  durum kodları, sayılar ve ayrıntılar çevrilmez. Aynı etkin seçeneklerle eski
  komutun ürettiği veridir; Türkçe metin araçları için --language tr eşdeğeridir.
- `--ayrinti`: kısa Türkçe özetin yanında özgün JSON tanılarını veya hata ayrıntısını
  stderr'e yazar. İngilizce alanlar, teknik mesajlar ve izler içerebilir.
- Bilinen dosya, hesap, CSV ve yerleşim hataları Türkçe açıklanır. Tanınmayan hata
  için Türkçe yönlendirme ve --ayrinti önerisi verilir; tam hata kataloğu çevrilmiş değildir.
- Başarılı JSON sonuçlarında özgün çıkış kodu korunur. Açıklama denetimindeki
  inceleme/düzeltme sonucu 1 olabilir. Türkçe insan arayüzünde çıktı üretilemeyen
  işlem hatası 2 olur. --json modunda kod özgün araçtan aynen gelir.
- Sıfır çıkış kodu tek başına editoryal onay değildir; bazı özgün JSON komutları
  geçerli bir uyarı sonucu için de 0 döndürür. Durum ve kapsamı okuyun.
- Gelişmiş, burada sunulmayan seçenekler için özgün komutları kullanın. Eski
  komutlar ve varsayılanları değişmedi. Bu arayüzde konuşma hızı varsayılanı
  açıkça 140 sözcük/dakikadır; kendi ölçümünüzü --hiz ile girin.

`ice-aktar` komutu, kaynak CSV için sütun incelemesi, açık sayı/tarih/saat dilimi
eşleştirmesi, salt okunur önizleme ve hatasız kanonik dosya üretimi sağlar.
Örnek: `ice-aktar kaynak.csv --esleme esleme.json --hesap HESAP_ADI`.
Kayıt için ayrıca `--cikti /path/to/yeni-aktarim` verin. Ayrıntılı
[CSV içe aktarma kılavuzunu](../../ig-audit/references/csv-import.md) izleyin.
Türkçe sayı kısaltmaları tahmin edilmez; Instagram bağlantısı eklenmez. Kanonik CSV ve JSON şemaları
için [CSV analizi](../../ig-audit/references/csv-analysis.md),
[yayın kaydı](publications.md) ve [deneme](../../ig-plan/references/experiments.md)
kılavuzlarını kullanın.

### Türkçe açıklamada eylem çağrıları

`aciklama`, `Yorumda seçiminizi belirtin`, `Yorumlarda fikrinizi paylaşınız`,
`Kaydedin` gibi yaygın emir biçimlerini tanır. Yakın bir soru ve aynı sorunun
cevabını yorumda istemek bir eylem türüdür; ayrıca kaydetmek/paylaşmak istenirse
diğer tür de raporlanır. `asks` listesindeki türler aynı türün tekrar sayısı değildir.
Alıntı ve örnek komutlar, etiketler, bazı olumsuz ve geçmiş zaman ifadeleri çağrı
olarak sayılmaz. Destek sınırlıdır; her Türkçe ifade veya niyet otomatik çözülemez.
