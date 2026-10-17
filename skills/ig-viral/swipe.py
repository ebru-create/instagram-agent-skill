#!/usr/bin/env python3
"""
swipe.py - rank reels you collected by how far they beat their own account,
name the hook formula each one used, and write the swipe file.

The point of this script is one correction: raw views are not evidence. A
2,000,000-follower account doing 400,000 views had a quiet day. A 4,000-
follower account doing 400,000 views found something. This ranks on the
multiple over the account's own baseline, which is the only version of
"went viral" that tells you anything you can copy.

Input is a tab-separated file you fill in while you browse, one reel per row,
with a header line naming the columns:

    account   followers   median   views    hook
    @someone  48000       11000    412000   nobody tells you your first 30 flop

`median` is that account's typical recent views and is the better baseline.
If you only have `followers`, leave median out and the script says so.
`hook` is the first line of the reel, spoken or on screen, in their words.

Usage
  python3 swipe.py captured.tsv
  python3 swipe.py captured.tsv --account studio_one
  python3 swipe.py captured.tsv --out ~/.claude/instagram/swipe.md
  python3 swipe.py captured.tsv --json
"""

import argparse
from decimal import Decimal
import json
import os
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HOOKS = os.path.join(HERE, "..", "ig-reel", "hooks.json")
WORD_RE = re.compile(r"[A-Za-z0-9$%'’-]+")

try:                                              # optional: score the hooks too
    sys.path.insert(0, os.path.join(HERE, "..", "ig-reel"))
    from hookscore import run as score_hook       # noqa: E402
except Exception:                                 # ig-viral copied on its own
    score_hook = None


def load_formulas(path):
    try:
        with open(path, encoding="utf-8") as source:
            d = json.load(source)
    except Exception:
        return None
    by_id = {h["id"]: h for h in d["hooks"]}
    order = d.get("classify_order") or sorted(by_id)
    return [(by_id[i]["id"], by_id[i]["name"],
             re.compile(by_id[i]["match"], re.IGNORECASE)) for i in order if i in by_id]


def classify(hook, formulas):
    if not formulas:
        return None, "unclassified"
    for fid, name, pattern in formulas:
        if pattern.search(hook):
            return fid, name
    return None, "unclassified"


def parse_count(value):
    """Parse non-negative counts with comma grouping or decimal K/M/B suffixes.

    Decimal commas and locale-specific abbreviations are ambiguous; reject
    them instead of silently changing their magnitude.
    """
    value = value.strip()
    if not value:
        return None
    match = re.fullmatch(r"(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?\s*([kKmMbB])?", value)
    if not match or (match[2] and not match[3]):
        raise ValueError(f"invalid count {value!r}; use 1,200, 1.2K or 1.2M")
    number = Decimal(match[1].replace(",", "") + (match[2] or ""))
    number *= {None: 1, "k": 1000, "m": 1000000, "b": 1000000000}[
        match[3].lower() if match[3] else None]
    if number != number.to_integral_value():
        raise ValueError(f"count {value!r} does not resolve to a whole number")
    return int(number)


def read_rows(path):
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, encoding="utf-8") as source:
            raw = source.read()
    lines = [l for l in raw.splitlines() if l.strip() and not l.lstrip().startswith("#")]
    if not lines:
        return []
    head = [c.strip().lower() for c in lines[0].split("\t")]
    if "views" in head and "hook" in head:
        cols, body = head, lines[1:]
    else:
        cols, body = ["account", "followers", "views", "hook"], lines
    rows = []
    for line_number, line in enumerate(body, 2 if body is not lines else 1):
        cells = line.split("\t")
        if len(cells) < len(cols):
            cells += [""] * (len(cols) - len(cells))
        r = dict(zip(cols, [c.strip() for c in cells]))
        for key in ("views", "followers", "median"):
            try:
                r[key] = parse_count(r.get(key, ""))
            except ValueError as exc:
                raise ValueError(f"row {line_number}, {key}: {exc}") from exc
        if r["views"] is not None and r.get("hook"):
            rows.append(r)
    return rows


def analyse(rows, formulas):
    for r in rows:
        base = r.get("median") or r.get("followers") or 0
        r["baseline"] = base
        r["baseline_type"] = ("account median" if r.get("median") else
                              "follower count" if r.get("followers") else "unavailable")
        r["outlier"] = round(r["views"] / base, 2) if base else None
        r["formula_id"], r["formula"] = classify(r["hook"], formulas)
        r["words"] = len(WORD_RE.findall(r["hook"]))
        if score_hook:
            _, overall, verdict, _ = score_hook(r["hook"])
            r["hook_score"], r["hook_verdict"] = round(overall, 1), verdict
        else:
            r["hook_score"], r["hook_verdict"] = None, None
    groups = []
    for baseline in ("account median", "follower count", "unavailable"):
        cohort = [r for r in rows if r["baseline_type"] == baseline]
        if not cohort:
            continue
        ranked = sorted(cohort, key=lambda r: -(r["outlier"] or 0))
        groups.append(summarise(ranked, baseline))
    return {
        "baseline": groups[0]["baseline"] if len(groups) == 1 else "mixed (ranked separately)",
        "n": len(rows),
        "accounts": len({r.get("account", "") for r in rows}),
        "reels": [r for g in groups for r in g["reels"]],
        "groups": groups,
    }


def summarise(ranked, baseline):
    # A single row cannot be both the best and worst evidence.
    third = len(ranked) // 3 or 1
    can_compare = len(ranked) >= 2 and baseline != "unavailable"
    top = ranked[:third] if can_compare else []
    bottom = ranked[-third:] if can_compare else []

    def med(items, key):
        vals = [i[key] for i in items if i.get(key) is not None]
        return round(statistics.median(vals), 1) if vals else None

    counts = {}
    for r in top:
        counts[r["formula"]] = counts.get(r["formula"], 0) + 1
    return {
        "baseline": baseline,
        "n": len(ranked),
        "accounts": len({r.get("account", "") for r in ranked}),
        "reels": ranked,
        "top_formulas": sorted(counts.items(), key=lambda kv: -kv[1]),
        "top_hook_score": med(top, "hook_score"),
        "bottom_hook_score": med(bottom, "hook_score"),
        "top_words": med(top, "words"),
        "bottom_words": med(bottom, "words"),
        "unclassified": sum(1 for r in ranked if r["formula"] == "unclassified"),
    }


def render(a, out=sys.stdout):
    if "groups" in a:
        if a.get("owner_account"):
            print(f"Publishing account: @{a['owner_account']}", file=out)
        for group in a["groups"]:
            render(group, out)
        return
    head = (f"SWIPE FILE  ·  {a['n']} reels  ·  {a['accounts']} accounts  ·  "
            f"baseline: {a['baseline']}")
    print("\n" + head, file=out)
    print("=" * max(len(head), 78), file=out)
    for r in a["reels"]:
        mult = f"{r['outlier']:.1f}x" if r["outlier"] is not None else "   ?"
        score = f"{r['hook_score']:.0f}" if r["hook_score"] is not None else " -"
        fid = f"#{r['formula_id']:<2}" if r["formula_id"] else "-  "
        print(f"  {mult:>7}  hook {score:>3}  {fid} {r['formula'][:22]:<22} "
              f"{r.get('account', '')[:16]:<16} {r['views']:>9,}", file=out)
        print(f"           \"{r['hook'][:96]}\"", file=out)
    print("-" * max(len(head), 78), file=out)
    print("WITHIN THIS BASELINE GROUP", file=out)
    if a["baseline"] == "follower count":
        print("  Views / followers is a proxy, not an account-median outlier.", file=out)
    if not a["top_formulas"]:
        print("  Not enough comparable rows for a top/bottom comparison.", file=out)
    if a["top_formulas"]:
        print("  top third by outlier:  "
              + ", ".join(f"{n} x{c}" for n, c in a["top_formulas"][:4]), file=out)
    if a["top_hook_score"] is not None:
        print(f"  median hook score:     top {a['top_hook_score']:.0f}  "
              f"vs bottom {a['bottom_hook_score']:.0f}", file=out)
    if a["top_words"] is not None:
        print(f"  median hook length:    top {a['top_words']} words  "
              f"vs bottom {a['bottom_words']} words", file=out)
    print(f"  unclassified:          {a['unclassified']} of {a['n']}. Read those by hand, "
          "they are where a formula you do not have yet is hiding.", file=out)
    print("\n  A hand-collected batch is evidence, not proof. Twelve reels shows you "
          "nothing;\n  forty across six accounts shows you something. Collect more before "
          "you believe it.\n", file=out)


def to_markdown(a):
    lines = ["# Swipe file", "", f"{a['n']} reels across {a['accounts']} accounts.",
             "Ranked separately within each baseline type; groups are not comparable.", ""]
    if a.get("owner_account"):
        lines[2:2] = [f"Publishing account: @{a['owner_account']}", ""]
    for group in a["groups"]:
        lines += [f"## Baseline: {group['baseline']}", ""]
        if group["baseline"] == "follower count":
            lines += ["Views / followers is a proxy, not an account-median outlier.", ""]
        for r in group["reels"]:
            mult = f"{r['outlier']:.1f}x" if r["outlier"] is not None else "?"
            lines += [f"### {mult}  {r['formula']}  ({r.get('account', '')})",
                      f"- views: {r['views']:,}  baseline: {r['baseline']:,} ({r['baseline_type']})",
                      f"- hook score: {r['hook_score']}  words: {r['words']}",
                      f"- hook: \"{r['hook']}\"", ""]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Rank collected reels by outlier multiple.")
    ap.add_argument("input", nargs="?", default="-", help="TSV file, or - for stdin")
    ap.add_argument("--hooks", default=HOOKS, help="path to ig-reel/hooks.json")
    destination = ap.add_mutually_exclusive_group()
    destination.add_argument("--out", help="also write the swipe file as markdown here")
    destination.add_argument("--account", help="save swipe.md for this publishing account")
    ap.add_argument("--data-root", help="alternative account data root (requires --account)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.data_root and not args.account:
        ap.error("--data-root requires --account")
    account_context = None
    if args.account:
        sys.path.insert(0, os.path.join(HERE, "..", "ig-account"))
        try:
            from account import resolve
        except ImportError:
            ap.error("named accounts require the sibling ig-account skill; install the full pack")
        try:
            options = {"account": args.account}
            if args.data_root:
                options["root"] = args.data_root
            account_context = resolve(**options)
        except (ValueError, OSError) as exc:
            ap.error(str(exc))
        args.out = account_context["paths"]["swipe"]

    try:
        rows = read_rows(args.input)
    except ValueError as exc:
        ap.error(str(exc))
    if not rows:
        print("no usable rows. Need a tab-separated file with at least views and hook.",
              file=sys.stderr)
        sys.exit(2)
    formulas = load_formulas(args.hooks)
    a = analyse(rows, formulas)
    if account_context:
        a["owner_account"] = account_context["account"]
    if not formulas:
        print("note: hooks.json not found, formulas not named. Pass --hooks.", file=sys.stderr)
    if score_hook is None:
        print("note: hookscore.py not importable, hook scores skipped.", file=sys.stderr)

    if args.json:
        print(json.dumps(a, indent=2, ensure_ascii=False))
    else:
        render(a)
    if args.out:
        path = os.path.expanduser(args.out)
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as target:
            target.write(to_markdown(a))
        print(f"wrote {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
