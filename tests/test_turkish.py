"""Turkish behavioral examples; these are not a quality benchmark corpus."""

import json
from pathlib import Path
import tempfile
import unittest
import unicodedata

from test_regressions import ROOT, cli, load


language = load("language_tests", "skills/ig-account/ig_language.py")
detect = load("detect_tr_tests", "skills/ig-human/detect.py")
humanize = load("humanize_tr_tests", "skills/ig-human/humanize.py")
hooks = load("hooks_tr_tests", "skills/ig-reel/hookscore.py")
beats = load("beats_tr_tests", "skills/ig-reel/beats.py")
caption = load("caption_tr_tests", "skills/ig-caption/caption.py")
swipe = load("swipe_tr_tests", "skills/ig-viral/swipe.py")
LEX = json.loads((ROOT / "skills/ig-human/slop.tr.json").read_text(encoding="utf-8"))


class TurkishTextTests(unittest.TestCase):
    def test_turkish_letters_are_not_split_into_fragments(self):
        text = "İstanbul’da üç öğrenciyle iş geliştirme çalışıyoruz."
        expected = ["İstanbul’da", "üç", "öğrenciyle", "iş", "geliştirme", "çalışıyoruz"]
        for module in (language, detect, hooks, beats):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.words(text), expected)

    def test_amounts_and_apostrophes_stay_together(self):
        self.assertEqual(language.words("İzmir'de ₺1.500,50 ödedim."),
                         ["İzmir'de", "₺1.500,50", "ödedim"])

    def test_dotted_and_dotless_i_remain_distinct(self):
        self.assertEqual(language.lower("İŞ IŞIK", "tr"), "iş ışık")
        self.assertEqual(language.upper("iş ışık", "tr"), "İŞ IŞIK")
        self.assertNotEqual(language.lower("I", "tr"), language.lower("İ", "tr"))

    def test_decomposed_characters_are_normalized_for_matching(self):
        original = "İş geliştirme ve öğrenme"
        self.assertEqual(language.words(unicodedata.normalize("NFD", original)), language.words(original))

    def test_clean_copy_preserves_brand_language_and_emoji(self):
        text = "İşimiz yaratıcılık. Strateji ve optimizasyon üzerine çalışıyoruz. 👩‍💻"
        clean, _ = humanize.humanize(text, LEX, language="tr")
        self.assertEqual(clean, text + "\n")

    def test_boilerplate_removal_uses_turkish_capitalization(self):
        clean, _ = humanize.humanize("GÜNÜMÜZÜN DİJİTAL DÜNYASINDA işler değişiyor.", LEX, language="tr")
        self.assertEqual(clean, "İşler değişiyor.\n")
        clean, _ = humanize.humanize("günümüzün dijital dünyasında işler değişiyor.", LEX, language="tr")
        self.assertEqual(clean, "işler değişiyor.\n")

    def test_custom_replacement_respects_turkish_case(self):
        lex = dict(LEX, phrases=[], words=[{"find": "ışık", "replace": "aydınlık", "family": "test"}])
        clean, _ = humanize.humanize("IŞIK ve İŞ", lex, language="tr")
        self.assertEqual(clean, "AYDINLIK ve İŞ\n")

    def test_urls_are_preserved_even_with_decomposed_characters(self):
        url = "https://example.com/" + unicodedata.normalize("NFD", "ışık")
        clean, _ = humanize.humanize("Bak: " + url, LEX, language="tr")
        self.assertIn(url, clean)

    def test_long_turkish_copy_does_not_need_english_contractions(self):
        text = ("Atölyeyi üç gün önce İstanbul'da yaptık. İlk bölümde iki örnek inceledik. "
                "Katılımcılar kendi sorularını yazdı ve küçük gruplarda çalıştı. "
                "Sonra herkes deneyimini paylaştı ve bir sonraki hafta için bir uygulama seçti.")
        checks, _, _ = detect.run(text, LEX, language="tr")
        self.assertIsNone(checks["VOICE"][0])
        self.assertIsNotNone(checks["SPECIFICITY"][0])
        self.assertIn("manual", checks["VOICE"][1])

    def test_short_turkish_copy_can_pass_with_limited_coverage(self):
        checks, _, verdict = detect.run("Üç örneği senin için hazırladım.", LEX, language="tr")
        self.assertEqual(verdict, "PASS")
        self.assertIsNone(checks["VOICE"][0])

    def test_turkish_hook_does_not_require_an_explicit_subject(self):
        checks, _, _, _ = hooks.run("Üç günde iki saat kazandım", language="tr")
        self.assertIsNone(checks["ADDRESS"][0])
        self.assertEqual(checks["SPECIFICITY"][0], 100)
        self.assertEqual(hooks.check_length("İki saat kazandım", "tr")[0], 100)

    def test_explicit_viewer_address_and_opening_filler(self):
        checks, _, _, flags = hooks.run("Merhaba sana üç hatayı anlatacağım", language="tr")
        self.assertEqual(checks["ADDRESS"][0], 100)
        self.assertTrue(flags)

    def test_turkish_names_can_be_payload_markers(self):
        checks, _, _, _ = hooks.run("Atölyemiz İzmir'de başlıyor", language="tr")
        # Proper names can be followed by Turkish apostrophe suffixes.
        self.assertIn("payload at word", checks["FRONTLOAD"][1])

    def test_beats_use_whole_turkish_words_and_measured_rate(self):
        text = "İstanbul’da üç öğrenciyle iş geliştirme çalışıyoruz."
        result = beats.analyse(text, wpm=120, language="tr")
        self.assertEqual(result["total_words"], 6)
        self.assertEqual(result["total_seconds"], 3)
        self.assertTrue(any("Türkçe" in note for note in result["notes"]))


class TurkishCaptionResearchTests(unittest.TestCase):
    def test_unicode_hashtags_are_counted_in_full(self):
        result = caption.analyse("Üç örneği kaydet.\n#gelişim #yaratıcılık #öğrenme #iş #çalışma #eğitim", language="tr")
        self.assertEqual(len(result["hashtags"]), 6)
        self.assertIn("#yaratıcılık", result["hashtags"])
        self.assertEqual(next(c for c in result["checks"] if c["check"] == "HASHTAGS")["status"], "FAIL")

    def test_turkish_calls_to_action(self):
        for text, count in [("Bunu kaydet.", 1), ("Yorumlara REHBER yaz.", 1),
                            ("DM'den yaz.", 1), ("Beni takip edin.", 1),
                            ("Kaydet ve paylaş.", 2)]:
            with self.subTest(text=text):
                self.assertEqual(len(caption.analyse(text, language="tr")["asks"]), count)

    def test_keyword_matching_uses_turkish_case_rules(self):
        result = caption.analyse("İŞ GELİŞTİRME için IŞIK üzerine çalışıyoruz.",
                                 keywords=["iş geliştirme", "ışık"], language="tr")
        check = next(c for c in result["checks"] if c["check"] == "SEARCH TERMS")
        self.assertEqual(check["status"], "PASS")

    def test_formula_matching_uses_turkish_catalogue_and_abstains(self):
        formulas = swipe.load_formulas(str(ROOT / "skills/ig-reel/hooks.tr.json"), "tr")
        self.assertEqual(swipe.classify("KİMSE SANA ÜÇ HATAYI SÖYLEMİYOR", formulas, "tr")[0], 3)
        self.assertEqual(swipe.classify("Bugün bahçedeki çiçekleri suladım", formulas, "tr"),
                         (None, "unclassified"))

    def test_all_six_clis_accept_turkish_and_report_language(self):
        inputs = {
            "skills/ig-human/humanize.py": "İşimiz yaratıcılık.",
            "skills/ig-human/detect.py": "Üç örneği senin için hazırladım.",
            "skills/ig-reel/hookscore.py": "Üç günde iki saat kazandım",
            "skills/ig-reel/beats.py": "İstanbul’da üç öğrenciyle çalışıyoruz.",
            "skills/ig-caption/caption.py": "Üç örneği kaydet.",
            "skills/ig-viral/swipe.py": "account\tfollowers\tmedian\tviews\thook\n@ornek\t1000\t100\t500\tKimse sana bunu söylemiyor\n",
        }
        for path, text in inputs.items():
            with self.subTest(path=path):
                result = cli(path, "--language", "tr", "--json", text=text)
                report = json.loads(result.stdout)
                self.assertEqual(report["language"], "tr")
                self.assertNotIn("Traceback", result.stderr)

    def test_english_lexicon_is_rejected_in_turkish_mode(self):
        for path in ("skills/ig-human/humanize.py", "skills/ig-human/detect.py"):
            with self.subTest(path=path):
                result = cli(path, "--language", "tr", "--lexicon",
                             str(ROOT / "skills/ig-human/slop.json"), text="İşimiz yaratıcılık.")
                self.assertEqual(result.returncode, 2)
                self.assertIn("lexicon language does not match", result.stderr)

    def test_account_turkish_lexicon_does_not_change_other_profiles(self):
        account = load("account_tr_tests", "skills/ig-account/account.py")
        with tempfile.TemporaryDirectory() as directory:
            a = account.initialize(directory, "studio_one")
            b = account.initialize(directory, "studio_two")
            Path(a["paths"]["lexicon_tr"]).write_text(json.dumps(LEX, ensure_ascii=False), encoding="utf-8")
            self.assertFalse(Path(b["paths"]["lexicon_tr"]).exists())
            self.assertFalse(Path(a["paths"]["lexicon"]).exists())
            result = cli("skills/ig-human/humanize.py", "--language", "tr", "--lexicon",
                         a["paths"]["lexicon_tr"], text="İşimiz yaratıcılık.")
            self.assertEqual(result.stdout, "İşimiz yaratıcılık.\n")


if __name__ == "__main__":
    unittest.main()
