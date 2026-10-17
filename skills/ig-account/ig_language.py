"""Small shared English/Turkish text helpers; no language auto-detection."""

import re
import unicodedata


WORD_RE = re.compile(r"[$₺€£]?\d+(?:[.,]\d+)*%?|[^\W\d_]+(?:['’\-][^\W\d_]+)*")
PROPER_RE = re.compile(r"(?<!^)\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}\b")
CONCRETE_RE = re.compile(r"[$₺€£]\s?\d|\b\d[\d,.]*\b|(?<!^)\b[A-ZÇĞİÖŞÜ][a-zçğıöşü]{2,}\b")
TR_NUMBERS = {"sıfır", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz",
              "on", "yirmi", "otuz", "kırk", "elli", "altmış", "yetmiş", "seksen",
              "doksan", "yüz", "bin", "milyon", "milyar", "yarım", "yüzde"}
TR_MONEY = {"lira", "tl", "dolar", "euro", "gelir", "gider", "maaş", "kira", "bütçe"}


def normalize(text):
    return unicodedata.normalize("NFC", text)


def lower(text, language="en"):
    text = normalize(text)
    if language == "tr":
        text = text.translate(str.maketrans({"I": "ı", "İ": "i"}))
    return text.lower()


def upper(text, language="en"):
    if language == "tr":
        text = text.translate(str.maketrans({"i": "İ", "ı": "I"}))
    return text.upper()


def words(text):
    return WORD_RE.findall(normalize(text))


def phrase_pattern(phrase, language="en"):
    phrase = lower(phrase, language) if language == "tr" else phrase
    return re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b",
                      0 if language == "tr" else re.IGNORECASE)


def match_text(text, language="en"):
    return lower(text, language) if language == "tr" else text


def language_argument(parser):
    parser.add_argument("--language", choices=("en", "tr"), default="en",
                        help="content language; choose explicitly (default en)")
