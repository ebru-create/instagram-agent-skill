#!/usr/bin/env python3
"""
detect.py - a five-check panel that scores how machine-written a draft looks.

What this is:  five local heuristics modelled on the signals public AI
detectors actually measure - sentence-length variation, concreteness, stock
vocabulary, typographic fingerprint, and voice. Every score is computed on
your machine from the text alone. Nothing is uploaded.

What this is NOT:  GPTZero, Originality, Copyleaks, Winston or Turnitin.
It does not call their APIs and it cannot promise their verdict. It catches
the things they all key on, which is why fixing them tends to move their
numbers too - but the only honest claim is the one on this line.

Each check returns a HUMAN score from 0 to 100. Higher is better.

Usage
  python3 detect.py draft.txt
  pbpaste | python3 detect.py -
  python3 detect.py draft.txt --json
  python3 detect.py before.txt after.txt      # compare two drafts
"""

import argparse
import json
import os
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ig-account"))
from ig_language import (words as unicode_words, lower, PROPER_RE as UNICODE_PROPER, TR_NUMBERS, TR_MONEY, phrase_pattern, match_text, language_argument)

HERE = os.path.dirname(os.path.abspath(__file__))
LEX = os.path.join(HERE, "slop.json")

SENT_RE = re.compile(r"[^.!?\n]+[.!?]*")
CONTRACTIONS = re.compile(r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.IGNORECASE)
PRONOUNS = re.compile(r"\b(i|me|my|mine|we|us|our|you|your)\b", re.IGNORECASE)
NUMBERS = re.compile(r"\b\d[\d,.]*%?\b|\$\d")


def clamp(n):
    return max(0.0, min(100.0, n))


def scale(value, human, machine):
    """Map value onto 0-100 where `human` -> 100 and `machine` -> 0."""
    if human == machine:
        return 50.0
    return clamp((value - machine) / (human - machine) * 100)


def sentences(text):
    return [s.strip() for s in SENT_RE.findall(text) if len(s.split()) > 2]


def words(text):
    return unicode_words(text)


def check_burstiness(text):
    """Humans vary sentence length hard. Models write even."""
    lens = [len(s.split()) for s in sentences(text)]
    if len(lens) < 4:
        return None, "too short to judge"
    mean = statistics.mean(lens)
    cv = statistics.pstdev(lens) / mean if mean else 0
    score = scale(cv, human=0.70, machine=0.22)
    return score, f"variation {cv:.2f} across {len(lens)} sentences (want 0.55+)"


def check_specificity(text, language="en"):
    """Numbers, names and concrete nouns. Slop is abstract."""
    w = words(text)
    if len(w) < 25:
        return None, "too short to judge"
    per100 = 100 / len(w)
    hits = len(NUMBERS.findall(text)) + len(set(UNICODE_PROPER.findall(text)))
    if language == "tr":
        hits += sum(lower(token, language) in TR_NUMBERS | TR_MONEY for token in w)
    density = hits * per100
    score = scale(density, human=6.0, machine=0.5)
    return score, f"{hits} concrete markers, {density:.1f} per 100 words (want 4+)"


def check_slop(text, lex, language="en"):
    """Stock vocabulary density against the lexicon."""
    w = words(text)
    if not w:
        return None, "no words to assess"
    hits, found = 0, []
    for entry in lex["words"] + lex["phrases"]:
        pattern = phrase_pattern(entry["find"], language)
        n = len(pattern.findall(match_text(text, language)))
        if n:
            hits += n
            found.append(entry["find"])
    density = hits * 100 / len(w)
    score = scale(density, human=0.0, machine=4.0)
    detail = f"{hits} stock terms, {density:.1f} per 100 words"
    if found:
        detail += " (" + ", ".join(sorted(found)[:4]) + (", ..." if len(found) > 4 else "") + ")"
    return score, detail


def check_fingerprint(text, preserve_typography=False):
    """Cleanup candidates, excluding meaningful joining/direction characters."""
    invisible = sum(text.count(c) for c in "\u200b\u2060\ufeff\u00ad\u2063")
    em = 0 if preserve_typography else text.count("—")
    curly = 0 if preserve_typography else sum(text.count(c) for c in "‘’“”")
    ellip = 0 if preserve_typography else text.count("…")
    nbsp = sum(text.count(c) for c in "   ")
    total = invisible * 4 + em * 2 + curly + ellip + nbsp
    per1k = total * 1000 / max(len(text), 1)
    score = scale(per1k, human=0.0, machine=12.0)
    detail = (f"{invisible} invisible, {em} em dash, {curly} curly quote, "
              f"{ellip} ellipsis, {nbsp} hard space")
    return score, detail


def check_voice(text, lex, language="en"):
    """Contractions, person, and the shapes models default to."""
    if language == "tr":
        return None, "Turkish voice needs manual brand review; no English contraction/pronoun penalty"
    w = words(text)
    if len(w) < 25:
        return None, "too short to judge"
    per100 = 100 / len(w)
    contractions = len(CONTRACTIONS.findall(text)) * per100
    person = len(PRONOUNS.findall(text)) * per100
    tells = 0
    names = []
    for s in lex["structures"]:
        try:
            n = len(re.compile(s["regex"], re.MULTILINE).findall(text))
        except re.error:
            continue
        if n:
            tells += n
            names.append(s["id"])
    bullets = [len(b.split()) for b in re.findall(r"(?m)^\s*[-*•]\s+(.+)$", text)]
    uniform = (len(bullets) >= 3 and statistics.pstdev(bullets) < 1.6)
    score = (scale(contractions, human=3.0, machine=0.0) * 0.35
             + scale(person, human=8.0, machine=1.0) * 0.35
             + clamp(100 - tells * 22) * 0.30)
    if uniform:
        score -= 12
        names.append("uniform-bullets")
    detail = (f"{contractions:.1f} contractions, {person:.1f} personal pronouns "
              f"per 100 words, {tells} structural tell(s)")
    if names:
        detail += " [" + ", ".join(names[:4]) + "]"
    return clamp(score), detail


CHECKS = ["BURSTINESS", "SPECIFICITY", "SLOP DENSITY", "FINGERPRINT", "VOICE"]


def run(text, lex, preserve_typography=False, language="en"):
    results = {}
    results["BURSTINESS"] = check_burstiness(text)
    results["SPECIFICITY"] = check_specificity(text, language)
    results["SLOP DENSITY"] = check_slop(text, lex, language)
    results["FINGERPRINT"] = check_fingerprint(text, preserve_typography)
    results["VOICE"] = check_voice(text, lex, language)
    if not words(text):
        results = {c: (None, "no words to assess") for c in CHECKS}
    scores = [results[c][0] for c in CHECKS if results[c][0] is not None]
    if not scores:
        return results, None, "INSUFFICIENT TEXT"
    # Unavailable checks do not penalise short text or trigger padding.
    overall = statistics.mean(scores) * 0.6 + min(scores) * 0.4
    verdict = "PASS" if overall >= 70 and min(scores) >= 55 else (
        "REVIEW" if overall >= 50 else "FLAGGED")
    return results, overall, verdict


def bar(score, width=24):
    if score is None:
        return " " * width
    filled = round(score / 100 * width)
    return "#" * filled + "." * (width - filled)


def render(results, overall, verdict, label=None, out=sys.stdout):
    title = "AI DETECTION PANEL" + (f"  -  {label}" if label else "")
    print("\n" + title, file=out)
    print("=" * max(len(title), 62), file=out)
    for name in CHECKS:
        score, detail = results[name]
        value = f"{score:5.1f}" if score is not None else "  N/A"
        print(f"  {name:<13} {bar(score)} {value}", file=out)
        print(f"  {'':<13} {detail}", file=out)
    print("-" * 62, file=out)
    value = f"{overall:5.1f}" if overall is not None else "  N/A"
    print(f"  {'HUMAN SCORE':<13} {bar(overall)} {value}   {verdict}", file=out)
    applicable = [c for c in CHECKS if results[c][0] is not None]
    print(f"  Coverage: {len(applicable)}/{len(CHECKS)} checks. N/A checks are excluded.", file=out)
    if verdict not in ("PASS", "INSUFFICIENT TEXT"):
        weakest = min(applicable, key=lambda c: results[c][0])
        print(f"\n  Weakest signal: {weakest}. Fix that first.", file=out)
    print("", file=out)


def main():
    ap = argparse.ArgumentParser(description="Score how machine-written a draft looks.")
    ap.add_argument("input", nargs="?", default="-", help="file, or - for stdin")
    ap.add_argument("compare", nargs="?", help="second file, to show before/after")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--lexicon", help="full lexicon override for the selected language")
    ap.add_argument("--preserve-typography", action="store_true",
                    help="do not penalise em dashes, curly quotes or ellipses")
    language_argument(ap)
    args = ap.parse_args()

    lexicon_path = args.lexicon or (str(Path(HERE) / "slop.tr.json") if args.language == "tr" else LEX)
    with open(lexicon_path, encoding="utf-8") as source:
        lex = json.load(source)
    if lex.get("language", "en") != args.language:
        ap.error("lexicon language does not match --language; use a matching account override")

    def read(path):
        if path == "-":
            return sys.stdin.read()
        with open(path, encoding="utf-8") as source:
            return source.read()

    targets = [(args.input, read(args.input))]
    if args.compare:
        targets.append((args.compare, read(args.compare)))

    payload = []
    for name, text in targets:
        results, overall, verdict = run(text, lex, args.preserve_typography, args.language)
        payload.append({
            "source": name,
            "language": args.language,
            "validation_note": "Editorial heuristics; Turkish scores are not corpus-validated." if args.language == "tr" else "Editorial heuristics, not authorship detection.",
            "checks": {k: {"score": round(v[0], 1) if v[0] is not None else None,
                            "detail": v[1]} for k, v in results.items()},
            "human_score": round(overall, 1) if overall is not None else None,
            "applicable_checks": sum(v[0] is not None for v in results.values()),
            "verdict": verdict,
        })

    if args.json:
        print(json.dumps(payload if args.compare else payload[0], indent=2))
        return

    if args.language == "tr":
        print("Dil: tr. Türkçe puanlar deneysel editörlük ipuçlarıdır; üslubu marka örnekleriyle inceleyin.")
    for (name, text), p in zip(targets, payload):
        results, overall, verdict = run(text, lex, args.preserve_typography, args.language)
        render(results, overall, verdict, label=os.path.basename(name) if args.compare else None)
    if args.compare:
        a, b = payload
        if a["human_score"] is not None and b["human_score"] is not None:
            delta = b["human_score"] - a["human_score"]
            print(f"  {a['human_score']:.1f} {a['verdict']}  ->  "
                  f"{b['human_score']:.1f} {b['verdict']}   ({delta:+.1f})\n")
        else:
            print("  Score delta unavailable: one draft has insufficient text.\n")

    sys.exit(0 if payload[-1]["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
