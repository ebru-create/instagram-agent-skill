# Uçtan uca yerel doğrulama

Bu senaryo, yeni kurulmuş paket üzerinde şu zinciri çalıştırır:

**Hesap → plan örneği → Türkçe açıklama kontrolleri → iki karusel → kurgusal
 yayın kayıtları → CSV eşleştirmesi → analiz → içerik denemesi → sonraki plan için not.**

Veriler tamamen kurgusaldır. Gerçek hesaplara erişmez, yayın yapmaz ve varsayılan
hesap klasörüne yazmaz. Her çalıştırmada yeni bir çıktı klasörüne paket kurar;
araçları depo dışındaki çalışma dizininden çağırır. Birincil hesapta işlem
yaparken ikinci hesabın örnek verisinin değişmediğini kontrol eder.

## Çalıştırma

Python ve karusel için isteğe bağlı Pillow ile Türkçe karakterleri içeren bir
TTF/OTF dosyası gerekir. Yazı tipi indirilmez veya pakete gömülmez.

```bash
python3 -m pip install -r skills/ig-carousel/requirements.txt
python3 validation/run_workflow.py --font /path/to/font.ttf --out /path/to/new-validation
```

Çıktı klasörü önceden varsa işlem reddedilir. Gerçek hesap klasörünü veya mevcut
kurulumu çıktı olarak kullanmayın. Başarılı çalıştırma `passed_with_manual_review`
döndürür. Hata durumunda işlem sıfır olmayan kodla çıkar; oluşturulmuş rapor ve
komut kayıtları inceleme için korunur. Eksik yazı tipi gibi başlangıç hataları
çıktı klasörü oluşturmaz.

## Neleri kontrol eder?

- Sabit plan örneğinin 90 dakikalık bütçeye sığması; modelin planlama kararı sınanmaz.
- Henüz paylaşım kimliği atanmamış deneme planının saklanabilmesi ve bu adımın yayın kaydı oluşturmaması.
- Türkçe temizleme/denetleme; desteklenmeyen marka sesi puanının N/A kalması.
- İki farklı kapak, toplam sekiz adet 1080×1350 RGB PNG, açıklama, alternatif metin ve dosya özetleri.
- Yerel içerik referanslarının iki kurgusal yayın kimliğiyle, sonra CSV kimlikleriyle eşleşmesi.
- Aynı CSV'nin analiz ve deneme değerlendirmesinde kullanılması; %2 ve %4 oranlarının doğru aktarılması.
- Değerlendirme tarihinden önce veya bir sonuç eksikken nihai karşılaştırma yapılmaması.
- Yanlış hesap ve yinelenen kayıt reddi; organik/ücretli uyuşmazlığının görünür olması.
- Diğer hesabın, mevcut planın ve ilk deneme kaydının korunması.

`scenario.tr.json` içindeki kimlikler, tarihler, bütçe ve metinler senaryo
girdileridir. Mevcut kurgusal CSV'den yalnızca bu iki sabit kimlik seçilir;
gözlenen performansa göre örnek seçimi yapılmaz. `--as-of` tarihleri tarihsel
senaryoyu tekrarlar; gerçek ön kayıt veya kronolojik saha deneyi kanıtı değildir.

## Çıktılar

| Dosya/klasör | Amaç |
| --- | --- |
| `report.md` | Türkçe kontrol özeti ve inceleme sınırları |
| `report.json` | Durum, kontrol sonuçları, senaryo/paket özeti ve dosya SHA-256 değerleri |
| `commands.json` | Çağrılan komutlar, çıkış kodları, stdout/stderr |
| `kurgusal-atolye-kapak-01/` ve `...-02/` | PNG'ler, açıklama, alternatif metinli manifest ve `review/overview.png` |
| `account-data/` | Yalnızca bu çalıştırmaya ait örnek hesaplar, yayın/analiz/deneme kayıtları |
| `experiment-before.json`, `experiment-after.json` | Kimlikler atanmadan önceki ve sonraki deneme girdileri |
| `insights.synthetic.csv`, `partial.synthetic.csv`, `conflicting.synthetic.csv` | Normal ve sorunlu veri yolları |
| `handoff.tr.md` | Gözlem, belirsizlik ve kapasiteyi sonraki plana taşıyan sabit örnek not |

## İnsan incelemesi ve sınırlar

Açıklama denetleyicisinin `REVIEW` sonucu, komut çalıştı diye `READY` sayılmaz.
Örneğin kapaktaki/açıklamadaki yazıyla belirtilen “üç” bazı sayısal özgüllük
kontrollerince tanınmaz; puan yükseltmek için doğal metin değiştirilmez. Rapor
uyarıları görünür tutar. JSON çıktısının veya sıfır çıkış kodunun tek başına
editoryal onay anlamına gelmediği dikkate alınır.

İki karuselin genel görünümünü ve gerçek boyuttaki kartlarını; Türkçe karakterler,
satır sonları, kontrast, alternatif metnin görsele uygunluğu ve marka dili için
inceleyin. Otomatik kontrol insan incelemesini tamamlamış saymaz.

Bu çalışma **yerel araçların entegrasyonunu** doğrular. Plan ve taslaklar elle
hazırlanmış örneklerdir; bağımsız bir model oturumunun beceri talimatlarına uyduğu,
gerçek içerik kalitesi, satış etkisi veya nedensellik doğrulanmış değildir.
Gerçek hesapla saha denemesi ayrıca kullanıcı verisi ve geri bildirimi gerektirir.

CI üç Python sürümünde testleri ve bu senaryoyu çalıştırır; çıktılar incelenebilir
artifact olarak saklanır. Yol, kayıt zamanı ve Pillow/yazı tipi sürümü gibi
farklar nedeniyle dosyalar her ortamda birebir aynı olmak zorunda değildir.
