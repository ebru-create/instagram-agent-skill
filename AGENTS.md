# instagram-agent-skill proje talimatları

## Git hedefi

Kullanıcının kalıcı tercihi: Bu depodaki çalışmaların commit ve push hedefi **Gitea**'dır.

- Depo sayfası: http://100.71.254.98:3033/ebru/instagram-agent-skill
- SSH adresi: `ssh://git@100.71.254.98:222/ebru/instagram-agent-skill.git`
- Tercih edilen uzak depo adı: `gitea`.
- `origin`, mevcut kurulumda GitHub deposudur; referans olarak korunur. Kullanıcı ayrıca istemedikçe GitHub'a push veya GitHub PR işlemi yapma.

Kullanıcı bu depoda değişiklik istediğinde ilgili doğrulamaları tamamla, yalnızca görev kapsamındaki dosyaları commit et ve çalışılan dalı Gitea'ya push et. Bu tercih için her seferinde yeniden izin isteme. Kaydedilecek değişiklik yoksa boş commit oluşturma. Başka görevlerin değişikliklerini dahil etme; force push yapma.

Push öncesi `git remote -v` ve dal durumunu kontrol et. Bu kurulumda açık hedefle `git push gitea HEAD` kullan. Gitea erişilemiyorsa kendiliğinden GitHub'a geçme; engeli bildir. Push sonrasında uzak dalın commit kimliğinin gönderilen yerel commit ile eşleştiğini doğrula.

Yeni bir checkout'ta uzak depo adları farklı olabilir. Yukarıdaki SSH adresine bağlı mevcut uzak depoyu kullan; yoksa `gitea` adıyla ekle. Yerel varsayılan push hedefini `remote.pushDefault=gitea` ile ayarla. `main` için `branch.main.pushRemote=gitea` kullan. Git geçmişi mevcutsa depoyu yeniden initialize etme; `gitea-init` komutunu körlemesine çalıştırma.

## Kapsam ve doğrulama

Bu talimatlar yalnızca `instagram-agent-skill` deposuna aittir. Üst klasördeki kampanyalar, `agency-agents-army`, sürüm paketleri ve diğer projeler bu deponun commit'lerine dahil edilmez. Parola veya erişim belirteci talimat dosyalarına yazılmaz.

Kod değişikliklerinde ilgili testleri ve depoda belgelenmiş doğrulamaları çalıştır. Yalnızca bu talimat dosyası gibi dokümantasyon değişikliklerinde diff ve biçim kontrolü yeterlidir. Başka bir görevden kalan hazırlanmış veya kaydedilmemiş değişiklikleri koru.
