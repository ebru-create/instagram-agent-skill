---
name: ig-audit
description: >-
  Analyze published Instagram content against the account’s goal, compare
  supported metrics, state uncertainty and propose manageable next tests. Use when the user pastes their
  Instagram insights or past posts and asks "what's working", "why did this
  flop", "read my analytics", "audit my content", or wants to know what to do
  more of.
---

# ig-audit

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

Explain what this account's available evidence supports, what remains unknown,
and what to test next. An audit describes associations; it does not establish
a cause merely because two groups differ.

## Scope and input

Read the resolved `strategy`, `log` and previous `results` paths when present.
Use the user's current goal and period. If the goal is unknown, state what each
available metric can describe and ask only when a ranked recommendation needs
a goal choice. Do not silently rank a sales campaign by views.

Use whichever evidence is available: Insights exports, screenshots, retention
graphs, posts with view counts, or attributable enquiries/bookings. Record the
source and capture date, the publishing account, number of usable posts and
any missing fields. Confirm dates, format, organic/paid status and post age when
those materially affect comparison. A partial dataset can support a limited
first pass; it is not a complete account audit.

Drafts and approvals in `log` are not proof a post was published. Match results
to published post IDs/URLs where supplied and keep planned versus observed data
separate. Never fill missing results with zero or merge another brand's history.

If the account has a resolved `publications` ledger, use
[publication reconciliation](../ig-account/references/publications.md) to match
the CSV's post IDs, format, distribution and publication instants before
interpreting results. Disclose conflicts and unmatched IDs; resolve confirmed
corrections without silently dropping rows. A matching local record is still
user-reported identity context, not platform verification or performance evidence.

For supplied CSV data, use [the local CSV workflow](references/csv-analysis.md)
and `analyse.py` for calculations. Map confirmed source fields to `template.csv`;
native exports may need adaptation. Pass the publishing `--account` and a
goal-aligned `--primary-metric`. Default output is read-only JSON; `--save` creates
a fresh account-specific snapshot, preserving previous reports and `results.md`.
Read coverage and limitations before interpreting the numbers. Explain the JSON
in the user's language; its keys are stable English identifiers. The bundled
`example.synthetic.csv` is fictional and must never substitute for account data.

When evaluating a recorded content test, use
[the experiment workflow](../ig-plan/references/experiments.md) with the same
account and actual post assignments. Check original criteria and plan revisions;
do not select only successful posts for the comparison. `ready_descriptive`
means the recorded review date/data criteria are met, not that the result is
statistically reliable. Discuss the evidence and confounders before recommending
a next plan; a met practical threshold alone is not a scaling instruction.

## Calculate only supported measures

Choose a primary metric aligned to the goal and available data. Use other
metrics as diagnostics, without claiming one is universally strongest.

| measure | calculation | interpretation and limit |
| --- | --- | --- |
| Relative views | post views / comparable account-median views | descriptive relative exposure; state baseline window and n |
| Non-follower reach | reported proportion or non-follower reach / total reach | exposure beyond existing followers, not proof of qualified demand |
| Hold at 3 seconds | remaining viewers at 3s / starting viewers | early retention; only if starts, retention and duration support it |
| Average watch time | the reported duration with video length alongside it | can inform pacing; loops and length complicate cross-post comparisons |
| Shares per reach | reported shares / reach | sharing activity; do not relabel total shares as private sends |
| Saves or follows per reach | the corresponding count / reach | response/conversion diagnostic; preserve each metric's definition |
| Qualified enquiries/bookings | attributable counts or counts / a stated matching denominator | relevant business outcome only when attribution and qualification are available |

Show units and working for computed rates. Missing or zero denominators produce
N/A, not zero, infinity or a claim of failure. Missing attribution remains
unknown; do not allocate whole-account sales to individual posts. For videos
shorter than three seconds, do not invent a 3-second retention measure.
A zero baseline cannot produce an outlier multiple. A recent post with zero
views may simply not have a comparable observation window yet.

Use a disclosed, comparable baseline: similar format, post age/measurement
window and organic/paid treatment where possible. State included/excluded posts
and baseline n. Do not pool unrelated formats, promoted posts and fresh posts
into a single winner ranking. When matching data is unavailable, show separate
groups or raw observations and explain why a multiple/ranking is not supported.
Views-only input supports exposure analysis, not claims about sends or bookings.

## Separate observation, explanation and next action

For each material finding, report:

1. Observation: the actual values, denominators, group sizes and window.
2. Interpretation: a plausible explanation and confidence justified by the
   comparability and completeness of the evidence.
3. Alternatives/limits: topic, audience, offer fit, execution, distribution,
   promotion, timing or other plausible differences that could explain it.
4. Next test: a manageable change and the measure/window used to evaluate it.

Do not use a universal post-count threshold to declare a pattern proven or
meaningless. Small or unbalanced groups, one extreme post, missing metrics and
selection of only winners reduce confidence. Name those limitations and avoid
causal language. Show cohort medians or per-post values where helpful rather
than letting one unusually large result dominate an average.

Low views alone do not diagnose a hook problem. High reach with few follows
could reflect audience fit, the content promise, CTA or profile, among other
factors. Compare the available funnel evidence before suggesting `/ig-profile`
or `/ig-reel`. A retention gap does not rule out topic or first-frame effects.
Timing may be worth a test when relevant; neither prioritize nor dismiss it by
rule. If the evidence cannot distinguish explanations, say so.

## Output and handoff

Show scope, goal/primary metric and data coverage before any rankings. Label
rankings by the metric they use. Provide a small number of supported findings,
each with evidence and limits, then one or a few feasible next experiments.
Avoid blanket "stop this format" instructions based on a few observations.

Illustrative finding (numbers are examples, never substitute them for user data):

```
GÖZLEM: Aynı 7 günlük ölçümde iki içerik 40/2.000 ve 9/1.000 paylaşım/erişim
aldı: %2,0 ve %0,9. İkisi de organik karusel; örneklem iki içerik.
YORUM: İlk içerikte paylaşım oranı daha yüksek; nedenini henüz ayıramıyoruz.
SINIR: Konular ve kapaklar farklı. Satış veya nitelikli başvuru verisi yok.
SONRAKİ DENEME: Benzer konuda iki kapak yaklaşımı; ana ölçüt ve bütçe
hesabın hedefiyle birlikte /ig-plan içinde belirlenecek.
```

Save the completed audit to the resolved `results` path with account, goal,
period, sources/capture dates, coverage, metric definitions, observations,
hypotheses, uncertainties and review criteria. Preserve relevant prior findings
and mark what this audit supersedes. Pass the same publishing account and
supported findings to `/ig-plan`; optional `/ig-viral` research should explore
hypotheses rather than filter out everything not already labelled a winner.
Never combine publishing accounts unless the user explicitly requests comparison.
