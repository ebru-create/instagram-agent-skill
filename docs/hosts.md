# Codex, Claude Code ve genel ajanlarla kullanım

## Ortak çekirdek

`instagram-agent.json` paket kimliğini ve sürümünü tanımlar. `skills/` altındaki
14 beceri, ortak Python yardımcıları ve şablonlar bütün ortamlarda aynıdır.
Kurucu Claude eklenti dosyalarına ihtiyaç duymaz. `.claude-plugin/` yalnızca
Claude marketplace dağıtımı içindir; sürüm paketleyicisi iki sürümün eşleşmesini
ayrıca kontrol eder. Kurulum model, API anahtarı veya model sağlayıcısı seçmez.

Python araçları model çağırmadan yerel dosyalar üzerinde çalışır. Taslak üretmek
için bir model ve onu yöneten ajan gerekir. Ajanın `SKILL.md` ve referansları
okuyabilmesi, dosyalarla çalışabilmesi ve Python 3.10+ komutlarını çalıştırabilmesi
tam akış için gereklidir. Yalnızca sohbet eden modellerde talimatlar kullanılabilir;
komutlar kullanıcı tarafından çalıştırılır ve sonuçlar modele geri verilir.

## Kurulum hedefi

Komutları depo veya açılmış kaynak ZIP'inin kökünde çalıştırın:

| Ortam | Komut | Varsayılan hedef |
| --- | --- | --- |
| Codex | `python3 scripts/install.py --host codex` | `~/.agents/skills` |
| Claude Code | `python3 scripts/install.py --host claude-code` | `~/.claude/skills` |
| Genel ajan | `python3 scripts/install.py --host generic --skills-dir /tam/yol/skills` | Açık hedef zorunlu |

Önce aynı komuta `--dry-run` ekleyin; kurulumdan sonra aynı hedefle `--check`
çalıştırın. `--skills-dir` her ortamda varsayılanı geçersiz kılar. `--host`
verilmezse önceki sürümlerdeki Claude hedefi korunur.

Mevcut kurulumu güncellemek için **aynı hedefi** kullanıp `--update --dry-run`,
ardından `--update` çalıştırın. Önceden `~/.codex/skills` altına kurulduysa:

```bash
python3 scripts/install.py --host codex --skills-dir ~/.codex/skills --update --dry-run
python3 scripts/install.py --host codex --skills-dir ~/.codex/skills --update
python3 scripts/install.py --host codex --skills-dir ~/.codex/skills --check
```

Yeni hedefe ikinci kopya kurmak yerine eski hedefi koruyun. Kurucu başka hedefleri
silmez veya otomatik taşımaz. Yerel değişiklikler, yedekler ve geri dönüş için
[kurulum rehberini](installation.md) izleyin. Kurucu ajanı yeniden başlatmaz;
yeni beceriler görünmezse yeni bir oturum açın veya ajanı yeniden başlatın.

Codex keşif konumları ve beceri çağırma davranışı için
[resmî rehber](https://learn.chatgpt.com/docs/build-skills).

## Ortak hesap kökü

Bütün araçlarda kök seçimi şu sırayladır:

1. Komuta verilen `--root`, `--data-root` veya Türkçe `--kok`.
2. Boş olmayan `INSTAGRAM_AGENT_HOME` ortam değişkeni.
3. Varsa önceki `~/.claude/instagram` kökü.
4. Yeni kurulumlarda `~/.local/share/instagram-agent`.

İki varsayılan klasör de varsa eski kök önceliklidir. Yeni kökü seçmek için açık
kök veya ortam değişkeni kullanın. Kurulum hesap verisini taşımaz. Bir hesap
seçilen kökte yoksa başka kök aranmaz; aynı hesabı bütün adımlara açıkça geçirin.
Özel kökteki eski hesaplar için ortam değişkenini veya komut seçeneğini kullanın.

```bash
export INSTAGRAM_AGENT_HOME="$HOME/.local/share/instagram-agent"
python3 skills/ig-account/turkce.py hesap ekle hesabim
python3 skills/ig-account/turkce.py hesap goster --hesap hesabim
```

`export` yalnızca ilgili terminal ve oradan başlatılan süreçlere geçer. Masaüstü
ajanına otomatik geçtiğini varsaymayın; ajanınızın ortam ayarını kullanın veya
komutlara açık kökü verin. Kalıcı bağlam için daima hesap aracının döndürdüğü
yolları kullanın. Model seçimi, hesap seçimini değiştirmez.

## Beceri çağırma

Talimatlardaki `ig-plan`, `ig-caption` gibi adlar beceri adlarıdır; evrensel
terminal komutları değildir. Codex'te `$ig-plan`, Claude Code'da `/ig-plan`
gibi ortamın sunduğu çağırma biçimini veya beceri adını belirten doğal dili kullanın.
Genel ajanlarda beceri keşfi ortamınıza bağlıdır; kurucu bunu otomatik yapılandırmaz.

Örnek istek:

```text
Kurulu ig-plan becerisinin SKILL.md dosyasını ve gerekli referanslarını oku.
@hesabim için Türkçe haftalık içerik planı hazırla.
Hedefim atölye başvurusu; haftada 90 dakikam ve iki paylaşım kapasitem var.
Hesap bağlamını ig-account aracıyla çöz; eksik sonuçları uydurma.
```

Kaynak depoda araçlar `skills/ig-account/turkce.py` gibi yollardadır. Kurulu
kopyada seçilen hedefin altındaki aracın tam yolunu kullanın; kardeş becerilerin
birlikte bulunması gerekir. Yalnızca `SKILL.md` kopyalamak yeterli değildir.

## Yerel ve açık ağırlıklı modeller

Ollama veya llama.cpp gibi bir çalıştırıcının üstünde, yukarıdaki dosya/Python
yeteneklerini sağlayan bir ajanla ortak çekirdek kullanılabilir. Bu sürüm böyle
bir çalıştırıcı kurmaz, model indirmez ve sağlayıcı API adaptörü içermez.
Yerel modelle uçtan uca davranış henüz doğrulanmış değildir. Kurulum ve Python
testlerinin geçmesi her modelin Türkçe içerik veya araç kullanımında aynı kaliteyi
vereceği anlamına gelmez. Gerçek model desteği iddiasından önce aynı senaryoyu,
hesap izolasyonunu ve araç sonuçlarının doğru yorumlanmasını o ortamda sınayın.
