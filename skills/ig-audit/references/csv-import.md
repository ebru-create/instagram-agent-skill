# CSV içe aktarma: incele → eşleştir → önizle → üret

`import_csv.py`, kullanıcının sağladığı CSV'yi mevcut analiz şemasına dönüştürür.
Harici paket, hesap girişi veya ağ bağlantısı gerekmez. Kaynağı değiştirmez;
platform dışa aktarımlarının hepsini otomatik tanıyan bir araç değildir.
Ölçüm tanımlarını, dosyanın hangi hesaba ait olduğunu ve ilişkilendirmeyi kullanıcı
bağlamından doğrulayın. Sütun adı tek başına ölçütün anlamını kanıtlamaz.

## 1. Sütunları incele

```bash
python3 skills/ig-account/turkce.py ice-aktar /path/to/kaynak.csv --ayirici ';'
```

Eşleştirme verilmediğinde yalnızca başlıklar, kayıt sayısı ve ilk beş kaynak kayıt
gösterilir. Varsayılan ayırıcı virgül, kodlama `utf-8-sig` (BOM kabul eder).
Sekme için `--ayirici sekme`; gerektiğinde açık `--kodlama cp1254` kullanın.
Ayırıcı/kodlama tahmin edilmez. Bu inceleme henüz kanonik doğrulama değildir.

## 2. Eşleştirmeyi hazırla

`../import.mapping.example.tr.json` örneğini kopyalayın. Asistan kaynak başlıkları
inceleyip bu dosyayı hazırlayabilir; bilinen kullanıcı tercihlerini yeniden
sormayın, ancak belirsiz tarih/sayı biçimini veya ölçüm anlamını tahmin etmeyin.
Gereken bilgi yoksa önizleme ile sınırlı kalın. Sabit değerleri ve dışarıda kalan
sütunları kullanıcıya gösterin. Örnek CSV ve eşleştirme tamamen kurgusaldır.

| Alan | Açık seçim |
| --- | --- |
| schema_version | `1` |
| delimiter | `,`, `;` veya JSON'da `\t` |
| encoding | `utf-8`, `utf-8-sig` veya `cp1254` |
| number_format | `plain`, `tr` veya `en`; otomatik seçim yok |
| date_format | `iso`, `%d.%m.%Y %H:%M`, `%d/%m/%Y %H:%M`, `%m/%d/%Y %H:%M` veya `%Y-%m-%d %H:%M:%S` |
| timezone | `null` veya açık sabit UTC farkı, ör. `+03:00`; saat dilimsiz tarihler için gerekir |
| measurement_scope | `cumulative_since_publication`: sayılar yayından ölçüm anına kadar birikimli olmalı |
| columns | Kanonik alan → kaynak sütun adı; ör. `"views": "Görüntüleme"` |
| constants | Yalnızca bilinen `account`, `format`, `distribution`, `captured_at` sabitleri; metrik sabiti yok |
| value_maps | Yalnızca format/dağıtım etiketlerinin açık eşleştirmesi; ör. `"Karusel": "carousel"` |
| missing_values | Sayısal alanlardaki eksik veri simgeleri, ör. `["", "—"]`; rakam içeren simgeler reddedilir |
| attribution | `enquiries` veya `bookings` eşleniyorsa `post_level_confirmed` beyanı gerekir |

Tüm zorunlu kimlik alanları eşlenmeli veya izin verilen açık sabitlerden gelmelidir.
`post_id` ve `published_at` kaynak sütunlardan gelmelidir. Aynı kaynak sütun iki
farklı ölçüte atanamaz; bir hedef hem sütun hem sabit olamaz. Başlıkların dış
boşlukları temizlenir; diğer eşleştirmeler büyük/küçük harf dahil açık adlarla yapılır.

- Türkçe sayı biçiminde `1.234` → `1234`, `15,5` → `15.5`; İngilizce biçimde
  `1,234` → `1234`, `15.5` → `15.5`. Gruplamalar üçlü olmalıdır. `plain` noktalı
  ondalığı kabul eder, binlik ayırıcı kabul etmez.
- Adetler tam sayı olmalıdır. `1.234,0` açık Türkçe biçiminde tam sayıysa kabul
  edilir; `1,2` adet olarak reddedilir. `1.2K`, `1,2 B`, negatif ve bilimsel
  gösterimler genişletilmez veya tahmin edilmez.
- Süreler ondalık saniye olarak korunur. Kimlikler metindir; baştaki sıfırlar korunur.
  Eksik alan boş kalır, ölçülmüş sıfır sıfır kalır. Eksik veri simgeleri kimlikleri
  silmek veya satır filtrelemek için kullanılmaz.
- Tarih yalnızca gün bilgisi içeriyorsa saat uydurulmaz. Saat dilimsiz girdiye
  yalnızca açık timezone uygulanır; zaten saat dilimli ISO girdisinin farkı korunur.
  Dakikalık kaynak biçiminde saniye 00 olur; daha hassas ölçüm varmış gibi yorumlamayın.
  Sabit fark yaz/kış saati kurallarını otomatik çözmez.
- Kapsam veya ilişkilendirme beyanları kaynak verisini doğrulamaz. Takvim aralığı
  alt toplamlarını birikimli sonuç gibi aktarmayın; toplam paylaşımı özel mesaj
  gönderimiyle veya hesap geneli satışları içerik rezervasyonuyla eşlemeyin.
- Hesap sütunu varsa onu eşleyin. Sütun yokken account sabiti yalnızca dosyanın
  seçilen tek hesaba ait olduğu biliniyorsa kullanılabilir; karışık markalar
  sabit hesap adı atanarak birleştirilmez. Yanlış hesap ve yinelenen post_id engellenir.

## 3. Dönüşümü önizle

```bash
python3 skills/ig-account/turkce.py ice-aktar skills/ig-audit/import.example.tr.csv --esleme skills/ig-audit/import.mapping.example.tr.json --hesap ornek_studyo
```

Dosya yazılmaz. İlk beş dönüştürülmüş kayıt, kaynak/dönüştürülebilen kayıt sayısı,
eşlenmeyen sütunlar ve en çok 20 hata gösterilir. Hata sayısı tüm hataları kapsar;
bazı kayıtların dönüştürülmesi, dosyanın aktarılabilir olduğu anlamına gelmez.
Eksik veri sayıları dönüştürülebilen kayıtlar içindir. Satır numarası CSV kaydının
bittiği fiziksel kaynak satırını gösterir; tırnak içindeki çok satırlı hücrelere dikkat edin.

Hücre dönüşüm hatası yoksa bütün sonuç mevcut `analyse.py` doğrulamasından geçer:
hesap, kimlikler, format/tür tutarlılığı, tarihler ve sayısal ilişkiler kontrol edilir.
Kontrol bir sorun bulursa kısmi dosya üretilmez. Türkçe kısa açıklama için varsayılan
çıktıyı, özgün hata metinleri için `--ayrinti`, makine çıktısı için `--json` kullanın.
Eşleştirme ile dönüştürürken ayırıcı/kodlama komut satırından ayrıca verilemez;
bu seçimler eşleştirme dosyasının içinden alınır.

## 4. Yeni klasöre üret ve analiz et

```bash
python3 skills/ig-account/turkce.py ice-aktar skills/ig-audit/import.example.tr.csv --esleme skills/ig-audit/import.mapping.example.tr.json --hesap ornek_studyo --cikti /path/to/yeni-aktarim
python3 skills/ig-account/turkce.py analiz /path/to/yeni-aktarim/canonical.csv --hesap ornek_studyo --olcut paylasim_orani
```

`--cikti` yalnızca hatasız veride `canonical.csv` ve `import-report.json` oluşturur.
Mevcut klasör reddedilir. Yakalanan yazma hatalarında geçici klasör temizlenir.
Kaynak CSV ve eşleştirme dosyası korunur. Kayıtlar veya satırlar sessizce atılmaz.
Rapor; kaynak, eşleştirme, içe aktarma kodu ve kanonik dosyanın SHA-256 değerlerini,
kullanılan açık ayarları ve kapsama sınırlarını içerir. Kaynak dosyaları ayrı saklayın;
rapor/satır önizlemeleri hesap verisi içerebilir.

Özgün CLI eşdeğeri:

```bash
python3 skills/ig-audit/import_csv.py SOURCE.csv --mapping MAPPING.json --account HANDLE --out NEW_DIR
```

Mevcut kanonik CSV dosyaları doğrudan analiz edilebilir; yeniden içe aktarma gerekmez.
Dönüştürülmüş dosyayı aynı hesabın [yayın kaydıyla](../../ig-account/references/publications.md)
eşleştirin, sonra [analiz](csv-analysis.md) ve [deneme](../../ig-plan/references/experiments.md)
akışına geçin. Araç yeni hesap oluşturmaz, kaynak doğruluğu veya performans garantisi vermez.
