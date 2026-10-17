"""Turkish CTA behavior, including the actual missed local-model output."""
import json
import unittest

from test_regressions import cli, load

caption = load('turkish_cta_caption', 'skills/ig-caption/caption.py')


class TurkishCallTests(unittest.TestCase):
    def test_comment_locations_and_imperatives(self):
        texts = ['Yorumda seçiminizi belirtin.', 'Yorumlarda fikrinizi belirtiniz.',
                 'Seçiminizi yorumda paylaşın.', 'Fikrinizi yorumlarda paylaşınız.',
                 'Yoruma bir örnek bırakınız.', 'YORUMDA SEÇİMİNİZİ BELİRTİN.', 'Yorumda seçin.',
                 'Yorumda seçiminizi söyleyin.',
                 'Yorumlara "KAYDET" yazın.', "Yorumlara 'KAYDET' yazın."]
        for text in texts:
            with self.subTest(text=text):
                self.assertEqual(caption.analyse(text, language='tr')['asks'], ['yorum yaz'])

    def test_observed_caption_question_and_comment_are_one_action(self):
        text = 'Seramik taslağınız hangisi? Düz veya çizgili? Yorumda seçiminizi belirtin.'
        report = caption.analyse(text, language='tr')
        self.assertEqual(report['asks'], ['yorum yaz'])
        self.assertEqual(next(check for check in report['checks'] if check['check'] == 'ONE ASK')['status'], 'PASS')

    def test_question_and_comment_do_not_hide_an_additional_action(self):
        for text in ['Sizce hangisi? Yorumda belirtin ve paylaşın.',
                     'Sizce hangisi? Yorumda belirtin. Bunu kaydet.',
                     'Yorumda fikrini paylaş ve kaydet.']:
            with self.subTest(text=text):
                self.assertEqual(len(caption.analyse(text, language='tr')['asks']), 2)

    def test_negatives_past_tense_quotes_tags_and_reported_commands_are_not_calls(self):
        for text in ['Yorumda seçiminizi belirttiniz.', 'Yorumda yazmayın.', 'Yorumda seçmeyin.',
                     'Yorumda söylediniz.', 'Yorumda söylemeyin.',
                     'Yorumlarda önerileri okudum.', 'Bunu kaydetmeyin.',
                     'Bu paylaşımı kaydetmek istedim.', '“Kaydet” bir menü etiketidir.',
                     "'Kaydet' sözcüğünü inceledik.", '‘Yorumda belirtin’ ifadesi bir örnek.',
                     'Yorumda yazın demiyorum.', 'Kaydet değil.', '#kaydet #paylaş',
                     '`Kaydet` komutunu anlattık.']:
            with self.subTest(text=text):
                self.assertEqual(caption.analyse(text, language='tr')['asks'], [])

    def test_negation_does_not_remove_other_positive_action(self):
        self.assertEqual(caption.analyse('Kaydet değil paylaş.', language='tr')['asks'], ['paylaş'])
        self.assertEqual(caption.analyse('Bunu kaydetmeyin. Yorumda belirtin.', language='tr')['asks'], ['yorum yaz'])

    def test_apostrophes_inside_words_are_preserved(self):
        report = caption.analyse('İstanbul’da buluşuyoruz. DM’den yazın.', language='tr')
        self.assertEqual(report['asks'], ['mesaj gönder'])

    def test_sizce_question_without_comment_remains_a_question(self):
        self.assertEqual(caption.analyse('Sizce hangisi?', language='tr')['asks'], ['soruyu yanıtla'])

    def test_english_contract_and_turkish_cli_still_work(self):
        self.assertEqual(caption.analyse('Save this and share it.', language='en')['asks'], ['save this', 'share this'])
        result = cli('skills/ig-account/turkce.py', 'aciklama', '--json',
                     text='Seramik taslağınız hangisi? Yorumda seçiminizi belirtin.')
        self.assertIn(result.returncode, (0, 1))
        self.assertEqual(json.loads(result.stdout)['asks'], ['yorum yaz'])
