---
name: ig-carousel
description: >-
  Build an Instagram carousel - the cover that earns the swipe, slide-by-slide
  copy, and the 1080x1350 files to upload. Use when the user says "carousel",
  "slides", "swipe post", "turn this into a carousel", or has a list-shaped or
  step-shaped idea that would die as a single image.
---

# ig-carousel

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

For a slot from `/ig-plan`, preserve its publishing account, goal, time budget,
post/frame count and camera constraints. These take precedence over this skill's
generic format suggestions. Read the resolved `strategy` brief if needed.

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

Use a carousel when a sequence, reference or visual explanation benefits from
separate slides. Each slide should contribute something; do not merely split
one long caption into arbitrary pieces. Use this account's results to evaluate
whether the format supports its current goal.

## When to use it instead of a Reel

Use a carousel when the idea has **sequence and needs to be re-read**: steps, a
framework with parts, a before and after, a list worth screenshotting. Use a
Reel when the idea has motion, a face, or a payoff that has to be seen
happening.

If the idea is one claim, it is neither. Hand it to `/ig-reel` and say so.

## Structure

Choose the count from the agreed plan and material. The exporter supports
2 to 20 slides, without a minimum cadence or a promise about completion. The
structure below is an adaptable example, not a required number of slides.

```
1         COVER     the hook. 6 words or fewer, at a size that is legible in
                    the grid at thumbnail. One line of promise under it.
2         THE STAKE why this matters, in one sentence. This slide is also a
                    second cover, so it cannot be setup.
3 to N    ONE IDEA PER SLIDE. A headline of 3 to 7 words, at most 25 words
                    under it. If a slide needs a paragraph, it is two slides.
N+1       RECAP     the whole thing as a list. This is the screenshot slide.
LAST      CTA       one action. Save, comment a keyword, or follow. One.
```

## Slide copy rules

- **Give the cover one clear promise.** Keep the title readable and specific;
  use a short headline when the meaning allows it.
- **Design for the grid crop.** The profile grid crops to a portrait rectangle
  that is taller than it is wide, and the exact ratio has moved more than once.
  Build at 1080x1350 and keep the cover text well inside the middle, clear of
  the outer 120 pixels on every side, and the crop stops mattering.
- **Number the slides** (3/8) so the reader can see the sequence.
- **No slide is a paragraph.** If it cannot be said in 25 words, split it.
- **Make a recap standalone when useful.** It can be a reference the reader
  saves or shares; evaluate those outcomes rather than promising them.
- **The handle on every slide**, small, bottom corner. Screenshots travel
  without you.
- **Write descriptive alt text for every slide.** The exporter requires it
  and stores it alongside the images for the user to enter when posting.

## Building the files

Use this folder's `render.py` to produce numbered RGB PNGs at 1080x1350, a review
overview, caption text and a manifest with per-slide alt text and hashes. Read
[references/rendering.md](references/rendering.md) for the JSON schema and font
options when generating files. `example.tr.json` is a fictional Turkish sample,
not the user's brand or approved factual copy.

PNG export needs optional Pillow and an explicit TrueType/OpenType font that
contains the text's glyphs. The other tools keep their standard-library-only
runtime. Do not install packages silently; use an available environment or
explain the exact optional requirement if missing. Use the brand's supplied
fonts/colors when available. Never download or distribute a font without the
appropriate permission.

Run `--check` first. If copy does not fit, shorten/split it without losing
meaning; the renderer does not shrink fonts, truncate text or silently replace
missing glyphs. Preserve account and language in the JSON. Use a fresh export
folder for each draft so old slide counts cannot mix with the new output.
Review the overview and full-size images, confirm copy/diacritics/line breaks,
and provide the image directory plus alt text and caption. Nothing is uploaded.

## Output

The slide-by-slide copy first, as a numbered list the user can read in ten
seconds and edit before anything is rendered. Then the **caption**, which for a
carousel is Job B in `/ig-caption`: the caption is doing work here, because the
cover has already used its six words.

Run both through `/ig-human` with the selected language. If the user requests
copy-only or an explicit copy-approval stage, stop at that stage. Otherwise
render the requested draft for review; local generation is not publishing.

```
CAROUSEL  ·  8 slides

1  COVER   THE $18,000 CLAUSE
           One line I now put in every contract.
2  STAKE   I approved the work. They asked for the money back nine days later.
3          WHAT IT SAYS
           Payment on delivery, not on approval.
...
7  RECAP   All four lines, in order.
8  CTA     Comment CONTRACT and I will send the full clause.

Caption: Job B, hook in line 1, one ask, 3 tags.
```

Nothing is uploaded. The user posts it.
