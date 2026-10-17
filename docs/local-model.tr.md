# Ollama ile yerel model kullanımı

Bu ilk bağlantı **tek bir Instagram açıklaması** üretir: seçilen hesabı çözer,
`voice.md` ve `strategy.md` dosyalarını okur, `ig-caption` ve `ig-human`
talimatlarını yerel modele verir, ardından Python temizleme ve metin denetimlerini
çalıştırır. Genel amaçlı otonom ajan değildir. Model kendi başına dosya okuyamaz,
komut çalıştıramaz, hesap değiştiremez veya içerik yayımlayamaz.

## Gereksinimler

- Python 3.10+ ve tam kaynak paketi veya birlikte kurulmuş 14 beceri.
- Çalışan yerel Ollama sunucusu ve açıkça seçilmiş, indirilmiş bir model.
- Seçilen hesapta boş olmayan `voice.md` ve `strategy.md`; konu, içerik türü,
  kullanılabilecek gerçek bilgiler, istenen tek çağrı ve arama sözcükleri olan bir brief.

Bağlantı Python standart kütüphanesini kullanır; API anahtarı gerekmez. Ollama'yı
resmî dağıtımından kurup çalıştırın. Model edinme işlemi kurucudan ve taslak
komutundan ayrıdır; örneğin bir kez `ollama pull qwen3:4b` çalıştırabilirsiniz.
Donanımınıza ve kullanımınıza uygun model ve lisansı seçin. Model ağırlıkları
bu deponun MIT lisansının kapsamına girmez.

## Bağlantıyı kontrol et

Depo kökünde:

```bash
python3 skills/ig-account/local_model.py doctor --model qwen3:4b
```

Bu komut yerel model adını, tam digest değerini, Ollama sürümünü ve lisans
metninin hash'ini döndürür; taslak üretmez. Eksik modeli indirmez. Bağlantı yalnızca
HTTP loopback adreslerini kabul eder (`127.0.0.1`, `localhost`, `::1`); proxy,
yönlendirme, uzak URL ve bilinen cloud/remote model tanımları reddedilir.
Özel yerel port için `--base-url http://127.0.0.1:11435` seçeneğini alt komuttan
önce verin. Bu kısıt, yerel sunucunuzun güvenilir yapılandırmasının yerini tutmaz.

## İlk açıklamanı üret

[Hesap kurulumu](quickstart.tr.md) adımlarından sonra `brief.txt` hazırlayın:

```text
Türkçe, Job B: tek fotoğrafın açıklaması.
Fotoğrafta boş ajanda ve kalem var. Bir sonraki gün için tek öncelik yazmayı öner.
Arama sözcüğü: ajanda. Tek çağrı: kaydet. En fazla 100 kelime.
Fiyat, müşteri hikâyesi, tarih veya başarı sonucu ekleme.
```

```bash
python3 skills/ig-account/local_model.py caption \
  --model qwen3:4b --account hesabim \
  --brief /tam/yol/brief.txt --language tr --keywords ajanda --cta save \
  --out /tam/yol/yeni-taslak
```

Hesap kökü önceki araçlarla aynıdır: `--root PATH`, ardından
`INSTAGRAM_AGENT_HOME`, mevcut eski kök veya ortak yeni kök. Hesaplar arasında
arama veya otomatik seçim yapılmaz. Kurulu kopyada aracın tam yolunu kullanın;
örneğin `~/.agents/skills/ig-account/local_model.py`.

`--cta save|comment|share|dm|follow|none` açık eylem hedefini seçer. `save` kaydetme,
`comment` okuyucunun bu paylaşımın yorumuna kendi görüşünü yazmasıdır. `none`
eylem çağrısı istenmediğini belirtir; seçenek hiç verilmezse model briefi izler ve
raporda doğrulanmış bir çağrı hedefi varsayılmaz. Açık hedef, mevcut brief ile
tutarlı olmalıdır; eski profil tercihinden önce gelir. Türkçe üretim yönlendirmesi
yazara verilen görevi okuyucuya hazır metne dönüştürmeyi, anlamı ve sen/siz dilini
korumayı ister; bunların hepsi otomatik olarak doğrulanamaz.

Her çalıştırmada yeni bir çıktı klasörü seçin. Varsayılan kullanımda model tek
sefer çağrılır. Açıkça `--revise-once` verirseniz ilk taslak, brief, profil ve
denetim sinyalleriyle yalnızca bir ek düzeltme çağrısı yapılır; toplam en fazla
iki çağrıdır. Sonuç yine kötü olsa da başka tur yapılmaz. Düzeltme metni daha iyi
yapmayabilir, hatta bozabilir; iki metni karşılaştırın. Otomatik onay verilmez.
Modelden yalnızca tek bir `caption` metin alanı olan JSON istenir; şema sunucuya
gönderilir ve yanıt yerelde ayrıca doğrulanır. Bu yapısal kontrol, metnin doğru
veya kaliteli olduğunu göstermez. Şemalı çıktı desteklemeyen modeller reddedilebilir.
Üretim sınırı `--max-tokens` (64–2048, varsayılan 800), bağlam 8192 token,
girdi uzunluğu ayrıca sınırlıdır. Düşünme yeteneği bildiren modellerde `think:false`
kullanılır. Bekleme süresi varsayılan 180 saniyedir; `--timeout` alt komuttan
önce verilerek en fazla 600 saniye seçilebilir. Çıktı sınırına ulaşan veya boş
yanıtlar başarısız sayılır; sınırı artırmadan önce hata ve ham yanıtı inceleyin.

## Çıktıyı incele

| Dosya | İçerik |
| --- | --- |
| `draft.raw.txt` | Modelin ilk metni |
| `draft.txt` | Yerel temizleme aracından geçen metin |
| `response.json` | Ollama'nın yanıtı ve süre/token bilgileri |
| `report.json` | Hesap, model digest'i, girdi/araç hash'leri, ayarlar, denetimler ve durum |

Tek düzeltme turunda `draft.initial.raw.txt`, `draft.initial.txt` ve
`response.initial.json` ilk durumu; `response.revision.json` ikinci model yanıtını
saklar. Normal `draft.txt`/`response.json` son geçerli yanıtı gösterir; en iyi
taslağın otomatik seçildiği anlamına gelmez. Raporun `initial` alanı ilk denetimleri,
`model_calls` çağrı sayısını, `revision_requested` açık seçimi kaydeder. İkinci
yanıt geçersizse ilk metin korunur ve çalışma `failed` olur.

Başarılı komutun durumu `draft_created_needs_review` olur. Çıkış kodu 0 teknik
akışın tamamlandığını söyler; metnin onaylandığını söylemez. `tools.caption` ve
`tools.detect` içindeki gerçek sonuçları okuyun. Uyarılar/başarısız metin denetimleri
raporda korunur. Türkçe ses puanı gibi desteklenmeyen kontroller N/A kalır.
Yanıt soruya dönüştüyse önce eksik bilgileri tamamlayın. Her durumda doğru bilgi,
doğal Türkçe, tek çağrı ve hesap dili açısından metni insan incelemelidir.

`quality` alanı ayrıca açık hedefin algılanmamasını (`requested_cta_missing`),
çağrı istenmezken algılanmasını (`unexpected_cta`), birden fazla eylem türünü
(`multiple_actions`) ve bazı yönerge kopyalarını (`instruction_like_text`)
gösterir. Açıklama denetimindeki uyarı/hatalar da `caption_lint_review` olarak
görünür. Bu sinyaller tek başına metni değiştirmez veya yeni model çağrısı yapmaz.
`no_supported_issues` yalnızca bu dar kontrollerin sinyal üretmediğini söyler;
anlamın, dilin veya bütün brief şartlarının doğruluğunu kanıtlamaz. Örneğin model
bir olumlu öneriyi olumsuza çevirebilir ve bu kontroller yine sessiz kalabilir.

Türkçe açıklama denetimi `Yorumda seçiminizi belirtin`, `Yorumlarda paylaşınız`
gibi yaygın emir biçimlerini tanır. Yakındaki soru + yorum istemi bir eylem türü
sayılır; `Yorumda belirtin ve paylaşın` iki tür sayılır. Alıntı, kod, etiket ve
bazı olumsuz/aktarılmış ifadeler ayıklanır. Bu bir Türkçe dilbilgisi çözümleyicisi
değildir: eş anlamlı, dolaylı, ironik veya karmaşık olumsuz cümleler insan incelemesi
gerektirir. `asks` bir eylem türü listesidir; tekrar edilen aynı eylemlerin sayısı değildir.

Model bağlamına becerilerin yalnızca ilgili yazım bölümleri verilir; hesap çözme,
dosya ve Python adımlarını model yerine kurucu akış yürütür. Tam beceri dosyalarının
hash'leri yine raporlanır; eksik yazım bölümü ön kontrolde hata verir.

Üretim veya denetim hatasında `failed` raporu saklanır; ön kontrolde reddedilen
hesap/girdi için çıktı klasörü oluşturulmaz. Başarılı ya da başarısız çalışma
hesap profilini, yayın kayıtlarını veya planı değiştirmez.

Raporlar yereldir; modele verilen brief, profil veya modelin ürettiği metin özel
bilgi içerebilir. Kendi hesap çıktılarınızı örnek doğrulama kaydı gibi depoya eklemeyin.

## Gerçek modelle doğrulama

```bash
python3 validation/local_model.py --model qwen3:4b --out /tam/yol/yeni-dogrulama
```

Bu işlem geçici amaçlı seçtiğiniz yeni dizine genel kurulum yapar, iki kurgusal
hesap ve brief oluşturur, iki gerçek yerel model çağrısını çalıştırır. Seçilen
profil hash'leri, yabancı hesap işareti sızıntısı, Türkçe denetimler ve bilinmeyen
hesabın reddedilmesi kontrol edilir. `commands.json` ve `report.json` kanıtı
saklar. `passed_with_manual_review` dar teknik senaryonun sonucudur; genel model
kalitesi, bütün Türkçe görevler veya otonom araç kullanımı için başarı iddiası değildir.

Tek düzeltme turunu da sınamak için doğrulama komutuna `--revise-once` ekleyin;
bu durumda iki hesap için toplam en fazla dört gerçek model çağrısı yapılır.

Normal testler Ollama gerektirmez; sahte yanıtlarla bağlantı sözleşmesini ve hata
yollarını sınar. Canlı doğrulama isteğe bağlıdır ve CI'da model indirmez.

17 Ekim 2026 tarihli [ilk canlı kayıt](../validation/local-model-result.tr.json)
Qwen3 4B ile teknik akışın tamamlandığını, iki çıktının da açıklama denetiminde
`REVIEW` kaldığını gösterir. İlk metin brief'teki yönergeyi kısmen kopyalayıp
kaydetme çağrısını atladı. İkinci metindeki gerçek yorum çağrısı yerel Türkçe
denetleyicinin sınırlı eşleştirmesiyle tanınmadı. Bunlar insan incelemesinin
gerektiğini gösterir; model veya denetleyici için genel başarı oranı değildir.
Önceki serbest metin denemelerinde Aya ve Qwen çıktı sınırına ulaştı; bu
başarısızlıklar da kayıtta belirtilmiştir.

1.15.0 karşılaştırması ve ara denemeler, ayrı
[kalite inceleme kaydında](../validation/local-model-quality.tr.json) tutulur.
Önceki kayıt değiştirilmez. Aynı iki kurgusal hesap/brief kullanılsa da yeni
yönlendirme ve açık çağrı hedefi birlikte değiştiği için bu izole bir A/B deneyi
veya bağımsız model kalite ölçümü değildir.

Kaynaklar: [Ollama Chat API](https://docs.ollama.com/api/chat),
[yerel model listesi](https://docs.ollama.com/api/tags),
[Qwen3 4B modeli ve lisansı](https://ollama.com/library/qwen3:4b).
