"""Turkish CLI summaries must preserve machine data, cautions and account routing."""
import json
from pathlib import Path
import tempfile
import unittest

from test_regressions import ROOT, cli, load
from test_carousel import FONT, HAS_PILLOW

ui = load('turkish_cli_tests', 'skills/ig-account/turkce.py')
UI = 'skills/ig-account/turkce.py'
CSV = str(ROOT / 'skills/ig-audit/example.synthetic.csv')
PLAN = str(ROOT / 'skills/ig-plan/example.experiment.tr.json')
PUBLICATION = str(ROOT / 'skills/ig-account/example.publication.tr.json')


class TurkishUiTests(unittest.TestCase):
    def test_root_and_subcommand_help_are_turkish(self):
        for args in [[], ['aciklama'], ['hesap', 'ekle'], ['yayin', 'kaydet'], ['analiz']]:
            result = cli(UI, *args, '--help')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Kullanım:', result.stdout)
            self.assertNotIn('show this help message', result.stdout)
            self.assertNotIn('usage:', result.stdout)

    def test_caption_warning_stays_review_and_keeps_exit_code(self):
        text = 'Bir sonraki atölyen için bu üç soruyu kaydet.'
        result = cli(UI, 'aciklama', text=text)
        self.assertEqual(result.returncode, 1)
        self.assertIn('İnceleme gerekiyor', result.stdout)
        self.assertIn('Somutluk kontrolü sınırlıdır', result.stdout)
        self.assertNotIn('CAPTION READY', result.stdout)

    def test_json_is_the_original_payload_and_preserves_the_backend_exit_code(self):
        for command, backend in [('aciklama', 'ig-caption/caption.py'), ('temizle', 'ig-human/humanize.py'),
                                 ('metin', 'ig-human/detect.py'), ('giris', 'ig-reel/hookscore.py')]:
            text = 'Üç örneği senin için hazırladım. Kaydet.'
            with self.subTest(command=command):
                original = cli('skills/' + backend, '--language', 'tr', '--json', text=text)
                wrapped = cli(UI, command, '--json', text=text)
                self.assertEqual(wrapped.returncode, original.returncode)
                self.assertEqual(wrapped.stdout, original.stdout)
                self.assertEqual(wrapped.stderr, original.stderr)

    def test_english_content_keeps_turkish_interface_and_english_analysis(self):
        result = cli(UI, 'aciklama', '--dil', 'en', '--json', text='Save these 3 examples.')
        self.assertEqual(json.loads(result.stdout)['language'], 'en')
        human = cli(UI, 'aciklama', '--dil', 'en', text='Save these 3 examples.')
        self.assertIn('Açıklama:', human.stdout)

    def test_unsupported_turkish_voice_remains_unavailable(self):
        result = cli(UI, 'metin', text='Üç örneği senin için hazırladım.')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Marka sesi: Veri yok / hesaplanamıyor', result.stdout)
        self.assertIn('yazarlık veya izlenme başarısı kanıtı değildir', result.stdout)

    def test_hook_and_beat_summaries_have_localized_labels(self):
        hook = cli(UI, 'giris', '--metin', 'Üç günde iki saat kazandım')
        self.assertEqual(hook.returncode, 0, hook.stderr)
        self.assertIn('Sonucun önemi:', hook.stdout)
        self.assertNotIn('Ek denetim', hook.stdout)
        beat = cli(UI, 'ritim', '--hiz', '120', text='Bir iki üç dört beş altı.')
        self.assertEqual(beat.returncode, 0, beat.stderr)
        self.assertIn('3,0 saniye', beat.stdout)

    def test_invalid_rates_and_missing_arguments_are_explained_in_turkish(self):
        for args in [('ritim', '--hiz', '0'), ('ritim', '--hiz', 'nan'), ('ritim', '--hiz', '-1')]:
            result = cli(UI, *args, text='Bir örnek.')
            self.assertEqual(result.returncode, 2)
            self.assertIn('Pozitif, sonlu', result.stderr)
            self.assertNotIn('Traceback', result.stderr)
        missing = cli(UI, 'analiz', CSV)
        self.assertEqual(missing.returncode, 2)
        self.assertIn('Gerekli alanlar eksik', missing.stderr)
        unknown = cli(UI, 'aciklama', '--bilinmeyen')
        self.assertEqual(unknown.returncode, 2)
        self.assertIn('Tanınmayan seçenekler', unknown.stderr)

    def test_missing_input_file_and_wrong_account_have_actionable_errors(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = cli(UI, 'aciklama', str(Path(temp) / 'absent.txt'))
            self.assertEqual(missing.returncode, 2)
            self.assertIn('Dosya bulunamadı', missing.stderr)
        mismatch = cli(UI, 'yayin', 'kontrol', PUBLICATION, '--hesap', 'other')
        self.assertEqual(mismatch.returncode, 2)
        self.assertIn('uyuşmuyor', mismatch.stderr)
        self.assertNotIn('Traceback', mismatch.stderr)

    def test_analytics_shows_percentages_coverage_and_separate_cohorts(self):
        result = cli(UI, 'analiz', CSV, '--hesap', 'ornek_studyo', '--olcut', 'paylasim_orani')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('fictional-1: %2,00', result.stdout)
        self.assertIn('fictional-2: %4,00', result.stdout)
        self.assertIn('Karusel · Ücretli', result.stdout)
        self.assertIn('Reels · Organik', result.stdout)
        self.assertIn('168,0 saat', result.stdout)
        self.assertIn('kullanılabilir ölçüm', result.stdout)
        self.assertIn('nedensellik kanıtı değildir', result.stdout)

    def test_experiment_reports_percentage_points_without_claiming_significance(self):
        result = cli(UI, 'deneme', PLAN, '--hesap', 'ornek_studyo', '--csv', CSV,
                     '--tarih', '2026-09-13T12:00:00+03:00')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Fark (yüzde puan): 2,0', result.stdout)
        self.assertIn('Betimsel karşılaştırma hazır', result.stdout)
        self.assertIn('istatistiksel anlamlılık', result.stdout)
        early = cli(UI, 'deneme', PLAN, '--hesap', 'ornek_studyo', '--csv', CSV,
                    '--tarih', '2026-09-11T12:00:00+03:00')
        self.assertIn('Değerlendirme tarihi bekleniyor', early.stdout)
        self.assertIn('Değerlendirilemedi', early.stdout)

    def test_account_creation_publication_and_reconciliation_use_the_selected_root(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'data'
            created = cli(UI, 'hesap', 'ekle', 'ornek_studyo', '--kok', str(root))
            self.assertEqual(created.returncode, 0, created.stderr)
            self.assertIn('Yayın kayıtları:', created.stdout)
            recorded = cli(UI, 'yayin', 'kaydet', PUBLICATION, '--hesap', 'ornek_studyo', '--kok', str(root))
            self.assertEqual(recorded.returncode, 0, recorded.stderr)
            self.assertIn('Yayın bildirimi kaydedildi', recorded.stdout)
            self.assertTrue((root / 'accounts/ornek_studyo/publications.json').exists())
            report = cli(UI, 'yayin', 'eslestir', CSV, '--hesap', 'ornek_studyo', '--kok', str(root))
            self.assertEqual(report.returncode, 0, report.stderr)
            self.assertIn('Eşleşen yayın: 1', report.stdout)
            self.assertIn('Kaydı olmayan CSV içeriği: 3', report.stdout)

    def test_saved_analytics_receipt_remains_account_scoped(self):
        with tempfile.TemporaryDirectory() as temp:
            cli(UI, 'hesap', 'ekle', 'ornek_studyo', '--kok', temp)
            saved = cli(UI, 'analiz', CSV, '--hesap', 'ornek_studyo', '--olcut', 'erisim', '--kok', temp, '--kaydet', '--json')
            self.assertEqual(saved.returncode, 0, saved.stderr)
            report = json.loads(saved.stdout)
            self.assertTrue(Path(report['saved_to']).is_relative_to(Path(temp).resolve() / 'accounts/ornek_studyo/audits'))

    def test_research_keeps_different_baseline_groups_labeled(self):
        text = 'account\tviews\tmedian\tfollowers\thook\n@a\t1000\t100\t100\tÜç örnek\n@b\t1000\t\t200\tÜç örnek\n'
        result = cli(UI, 'arastirma', text=text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Hesabın medyanına göre', result.stdout)
        self.assertIn('Takipçi sayısına göre', result.stdout)

    def test_cleanup_reports_event_counts_instead_of_rule_counts(self):
        result = cli(UI, 'temizle', text='A\u200bB\u200bC\u200b')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Görünmez karakterler: 3', result.stdout)

    def test_technical_details_are_opt_in(self):
        plain = cli(UI, 'yayin', 'kontrol', PUBLICATION, '--hesap', 'other')
        detailed = cli(UI, 'yayin', 'kontrol', PUBLICATION, '--hesap', 'other', '--ayrinti')
        self.assertNotIn('publication account does not match', plain.stderr)
        self.assertIn('publication account does not match', detailed.stderr)

    @unittest.skipUnless(FONT and HAS_PILLOW, 'carousel UI check needs optional Pillow and a suitable font')
    def test_carousel_control_uses_the_original_renderer_and_reports_the_account(self):
        result = cli(UI, 'karusel', str(ROOT / 'skills/ig-carousel/example.tr.json'),
                     '--yazi-tipi', FONT, '--kontrol')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Hesap: @ornek_studyo', result.stdout)
        self.assertIn('Kart sayısı: 4', result.stdout)
        self.assertIn('Yerleşim kontrol edildi', result.stdout)

    def test_invalid_carousel_output_modes_fail_before_writing(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / 'not-created'
            result = cli(UI, 'karusel', str(ROOT / 'skills/ig-carousel/example.tr.json'),
                         '--yazi-tipi', 'absent.ttf', '--kontrol', '--cikti', str(output))
            self.assertEqual(result.returncode, 2)
            self.assertIn('Birlikte kullanılamayan', result.stderr)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
