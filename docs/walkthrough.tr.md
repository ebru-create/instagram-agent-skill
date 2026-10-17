# Baştan sona kullanım örneği

Örnek hesap `@ornek_studyo`, hedef paylaşım/erişim oranını aynı gözlem süresinde
incelemek. Veriler, yayın bildirimleri ve kapak denemesi tamamen kurgusaldır.
Bu örnek bir büyüme önerisi veya gerçek hesap performansı iddiası değildir.

## Tek komutla yerel teknik prova

Depo kökünde, seçtiğin Python ortamına isteğe bağlı Pillow'u kur ve kendi Türkçe
karakterli TTF/OTF dosyanı seç:

```bash
python3 -m pip install -r skills/ig-carousel/requirements.txt
python3 validation/run_workflow.py --font /path/to/font.ttf --out /path/to/yeni-prova
```

Çıktı klasörü yeni olmalıdır. Araç bu klasörün içine temiz bir beceri paketi kurar,
örnek hesaplar oluşturur ve aşağıdaki zinciri çalıştırır. Gerçek hesabına veya
varsayılan hesabının dosyalarına yazmaz. Yazı tipi pakete dahil değildir.

| Aşama | Provada olan | Gerçek kullanımda gereken |
| --- | --- | --- |
| Brief/plan | Elle hazırlanmış 90 dakikalık plan | Senin hedefin, kapasiten, doğru örneklerin ve uygun tarihler |
| Deneme taslağı | Yayın kimlikleri boş ilk kayıt | Önceden belirlenen hipotez, ana ölçüt, pencere ve kriter |
| İçerik | Aynı metin üzerinde iki kapak yaklaşımı | Beceriyle üretilen taslakların dil, bilgi ve marka incelemesi |
| Karusel | İki dışa aktarma, toplam sekiz PNG | Tüm kartlar, açıklama ve alternatif metinlerin kontrolü |
| Kaynak veri | Türkçe başlıklı CSV'nin açık eşleştirmeyle dönüşümü | Hesabına ait, anlamını bildiğin birikimli ölçümler |
| Yayın kaydı | Kurgusal kimlik/tarih bildirimi | Gerçek yayının kullanıcı tarafından sağlanan kimliği ve zamanı |
| Eşleştirme | Kayıtların CSV kimlikleriyle uyuşması | Uyuşmazlıkları doğrulanmış bilgilerle düzeltme |
| Analiz | %2 ve %4 paylaşım/erişim | Eksik veri, format/dağıtım ve aynı ölçüm yaşını değerlendirme |
| Deneme | 2 yüzde puan fark, grup başına bir örnek | Belirsizliği koruyup devam/revizyon kararını kullanıcıyla verme |
| Sonraki plan | Gözlem ve sınırları taşıyan örnek not | Gerçek bulguları aynı hesap ve kapasiteyle plana aktarma |

## Çıktıları incele

Yeni prova klasöründe:

- `report.md`: Türkçe sonuç ve kapsam özeti.
- `commands.json`: komutlar, çıkış kodları ve özgün tanılar.
- İki `kurgusal-atolye-kapak-*/review/overview.png`: genel görünüm; kartları
  ayrıca gerçek boyutlarında açıp Türkçe karakterleri ve satır sonlarını kontrol et.
- `imported/canonical.csv` ve `imported/import-report.json`: kaynak eşleştirmesi
  ve dosya özetleri. Önceden belirlenen iki kimlik sonraki analiz için seçilir;
  diğer kayıtların performansına bakılarak seçim yapılmaz.
- `account-data/`: yalnızca provaya ait yayın, analiz ve deneme kayıtları.
- `handoff.tr.md`: gözlem, belirsizlik ve kapasiteyi sonraki plana taşıyan örnek not.

`passed_with_manual_review`, teknik kontrollerin geçtiğini ve editoryal/görsel
incelemenin hâlâ gerekli olduğunu belirtir. `failed` durumunda rapor ve mevcut
komut kayıtları hatayı incelemek için korunur. Prova ayrıca yanlış hesabı,
yinelenen kaydı, CSV çelişkisini ve erken/eksik deneme değerlendirmesini sınar.

## Kendi hesabına geçiş

[Hızlı başlangıç](quickstart.tr.md) ile kendi profilini oluştur. Sabit prova planı
ve metni yerine kendi doğrulanmış malzemeni kullan. CSV'yi önce
[incele ve eşleştir](../skills/ig-audit/references/csv-import.md); yayından ölçüm
anına kadar birikimli sayılarla takvim aralığı alt toplamlarını karıştırma.
[Yayın kaydı](../skills/ig-account/references/publications.md) yalnızca kullanıcı
bildirimidir. Ölçüt ve tarihleri [denemede](../skills/ig-plan/references/experiments.md)
açık seç; küçük veya seçilmiş sonuçları nedensel üstünlük sayma.

Bu prova yerel araç entegrasyonunu sınar. Bağımsız bir model oturumunun beceri
talimatlarına uyumu, yaratıcı kalite veya gerçek hesap etkisi değerlendirilmiş
sayılmaz. Gerçek kullanım geri bildirimleri sonraki düzeltmelerin dayanağıdır.
