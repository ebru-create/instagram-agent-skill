---
name: ig-human
description: >-
  Clean stock phrases and copy-paste artefacts from a draft, with optional
  punctuation normalization and a panel of local editorial signals. Use whenever
  text needs to sound human, when the
  user says humanize, "does this sound like AI", "remove the em dashes",
  "de-slop this", "this sounds like ChatGPT", or before any caption, script,
  comment, reply or DM is shown to the user.
---

# ig-human

## Content language

Use the language explicitly requested for this content, then the selected
account's voice profile; otherwise follow the supplied text or conversation.
Do not guess from a competitor's handle. For mixed content, ask for the main
language when it matters. Preserve Turkish characters, names, currency and the
brand's tone; do not translate English templates literally.
Pass `--language tr` or `--language en` explicitly to humanize, detect, hookscore,
beats, caption and swipe. The CLI default stays English for compatibility.
For Turkish, use `slop.tr.json` and `hooks.tr.json`; unavailable checks are N/A.
English contractions and explicit pronouns are not requirements for Turkish.
Use approved Turkish brand examples for manual voice review; do not rewrite
just to raise a score. Turkish scores are provisional editorial signals,
not validated performance predictions or AI-authorship detection.

## Account context

For account-specific work, resolve the user's publishing handle from the request
or established conversation, not a research target or message recipient. Run
`../ig-account/account.py show --account HANDLE` with Python from this skill's
folder (or use the helper's absolute installed path). Without an established
handle, run `show` without `--account`: legacy paths work only when no named
accounts exist; otherwise ask which publishing account to use.
Use only the returned paths, read that account's voice when relevant, and pass
the same handle to downstream skills. Missing files never fall back to another
account. On switching accounts, discard the previous account's context. Include
`account: @HANDLE` in receipts for saved work. Text-only edits need no selection
unless they use saved brand context. If the helper is unavailable, work from
supplied text without saved context or filesystem writes; install the full pack
for persistent profiles. See [account setup](../ig-account/SKILL.md).

Two tools live in this folder and they both actually run. Use them. Do not
eyeball this.

```bash
python3 humanize.py draft.txt --report        # clean it, show what changed
python3 detect.py draft.txt                    # score it, five checks
python3 detect.py before.txt after.txt         # prove the delta
```

Both read `slop.json`: 154 stock words and phrases with plain-English
replacements, 11 cleanup character classes, 11 typographic substitutions and
16 structural tells. The last block of each list is Instagram-specific, the
vocabulary that only shows up in captions and voiceovers. It is meant to be
edited. Use the resolved `lexicon_tr` path for Turkish or `lexicon` for English.
If that language's override exists, pass it via `--lexicon` to both scripts.
Otherwise use the bundled lexicon for that language. If a brand needs an
exception, copy the matching bundled lexicon to its resolved override path and
edit the copy. Keep `language: tr` in Turkish overrides; unmarked old lexicons
are English and are rejected with `--language tr`. Do not edit
the shared lexicon for a brand preference; generic text edits can use defaults.

## Why this matters more on Instagram than it looks

Captions are short and scripts get said out loud. A written-sounding line in a
600-character caption is a larger share of the text than the same line in an
essay, and a voiceover that nobody could say naturally is obvious in the first
take. The tell here is not a detector flagging the post. The tell is a person
scrolling past something that reads like a brand, or a creator stumbling over
their own script.

## What gets fixed automatically

**1. Copy-paste cleanup.** Removes zero-width spaces, word joiners, soft
hyphens, byte-order marks and invisible separators; normalizes unusual spaces.
Joiners, non-joiners, direction controls, Mongolian separators and emoji tag
characters are preserved. Unlisted format characters are left unchanged.
Invisible characters alone are not evidence of AI authorship or watermarks.

**2. Typography.** Em dash to comma, en dash to hyphen, curly quotes to
straight, ellipsis to three dots, bullet character to hyphen. If punctuation
is part of the user's voice, pass `--preserve-typography` to both scripts.
This keeps typography and excludes those punctuation penalties from scoring.

**3. The slop lexicon.** delve, leverage, robust, seamless, crucial, testament
to, "in today's fast-paced world", plus the Instagram block: "stop scrolling",
"in today's video", "follow for more", "tag someone who needs this", "the
algorithm loves", "run don't walk". Each swapped for a plain word or deleted,
with capitalisation preserved and URLs left untouched.

## What does NOT get fixed automatically

Structural tells get **flagged, not rewritten**, because changing the shape of
a sentence needs judgement:

- "It's not just X, it's Y" and "not only X but also Y"
- Rule-of-three triads
- Rhetorical one-word question lines: "The result?"
- The video preamble: "in this video I'm going to show you"
- Emoji bullet lists
- Three or more shouted words in a row
- Hashtag walls
- Reflex bait: "follow for more", "tag someone who", "double tap if"

That list is your job. Rewrite each flagged line by hand, keeping the meaning,
then re-run `detect.py`. This is the part that moves the score from REVIEW to
PASS, and it is the part a script cannot do.

## The five checks

`detect.py` scores five signals 0-100, higher is more human:

| check | what it measures | machine looks like |
| --- | --- | --- |
| BURSTINESS | sentence-length variation | every sentence the same length |
| SPECIFICITY | numbers, names, concrete markers per 100 words | abstract nouns, no figures |
| SLOP DENSITY | lexicon hits per 100 words | stock vocabulary |
| FINGERPRINT | invisible chars, em dashes, curly quotes per 1k chars | typographically perfect |
| VOICE | contractions, person, structural tells | no contractions, staged reveals |

Checks without enough text report `N/A` (JSON `null`) and are excluded.
The verdict weights the mean of applicable checks at 60% and the weakest
applicable check at 40%. PASS needs an overall of 70+ with no applicable check
below 55. Always show coverage: a short DM may pass only two of five checks.
Empty text or text without words gets `INSUFFICIENT TEXT`, not a pass.
For Turkish, VOICE stays N/A and requires manual review. These heuristics do
not establish human authorship.

## Say this honestly

These are local editorial heuristics, not validated authorship detection.
They run entirely on the user's machine without uploading text or calling
GPTZero, Originality, Copyleaks, Winston or Turnitin. No supplied evaluation
establishes agreement with those services or predicts changes in their verdicts.
Do not present a score as proof of authorship, detector performance or
undetectability. Review edits against the user's meaning and voice.

## Order of operations

1. `humanize.py draft.txt -o clean.txt --report`
2. Read the structural flags. Rewrite those lines yourself.
3. `detect.py draft.txt clean.txt` to show the before and after.
4. Make at most two revision rounds after the initial check. Fix relevant
   findings while preserving meaning and voice. Never pad short copy, invent
   numbers or change meaningful Unicode to raise a score. N/A is not a defect.
   If concerns remain, show them with the draft instead of repeating the loop.
   For `INSUFFICIENT TEXT`, skip score-driven rewriting and review manually.
5. Show the user the cleaned text and the score. Never the score alone.
