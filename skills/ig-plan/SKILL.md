---
name: ig-plan
description: >-
  Plan Instagram content around the selected account’s goals, production
  capacity and available evidence, with optional engagement and a review point. Use when the user says "plan my week", "what should I post",
  "content calendar", "I have nothing to post about", or wants a posting
  schedule and an engagement list.
---

# ig-plan

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

Build a plan the selected account can actually execute and evaluate. Cadence,
format mix and engagement time are choices derived from the brief, not fixed
requirements for every account.

## Establish the brief

Read the resolved `strategy`, `voice`, `results`, `log` and `swipe` paths when
present. Prefer the user's current request over older saved preferences. Use
account results relevant to the current goal before competitor research; a
swipe file suggests creative hypotheses, not proven outcomes for this account.
Check source dates and label stale or incomplete evidence.

Establish the following from available context without asking again for answers
already given:

- Primary goal for this period: awareness, useful engagement, qualified enquiries,
  bookings/sales, or another explicit outcome. Choose one primary measure that
  the user can actually observe; do not equate views with bookings.
- Audience, current offer/campaign, themes and usable true stories or examples.
- Weekly time budget, maximum number of posts if specified, people/resources,
  formats they can make, camera preferences and existing reusable assets.
- Audience timezone, any available posting windows and relevant deadlines.
- Recent comparable results and their observation window, if any.

If a missing goal or capacity prevents a useful plan, ask one short batched
question while preparing angles from supplied material. If the user requests a
quick draft, state provisional assumptions and offer a small editable plan.
Do not pretend those assumptions are confirmed preferences or analytics.
Record supplied or confirmed preferences in the resolved `strategy` path;
`templates/strategy.md` (or installer-bundled
`../ig-account/assets/templates/strategy.md`) is an optional starting format.
Preserve unrelated preferences when updating it. Keep provisional assumptions in the plan only.

## Choose a feasible mix

Use these as decision criteria, not quotas:

| goal | possible content | observable measure, when available |
| --- | --- | --- |
| Awareness | a clear introduction, useful demonstration or relevant story | non-follower reach at a consistent post age |
| Useful engagement | a reference, tutorial, discussion or carousel | saves or shares per reach, labelled separately |
| Qualified enquiries | a relevant problem, proof and a clear next step | attributable qualified enquiries or enquiry rate |
| Bookings or sales | an offer, objection answer, case example or product demonstration | attributable bookings/sales; unavailable attribution stays unknown |

Choose formats from this account's evidence, assets and constraints. A faceless
account may use voiceover, a carousel or images; do not require to-camera Reels.
Do not claim only one format reaches non-followers. There is no compulsory
Reel minimum, daily Story sequence, alternating content type, or offer quota.
Consecutive posts of one format can be appropriate. Each slot needs a specific
angle, the true supporting material, one intended action and its role in the goal.
Use a language-appropriate hook formula only when it fits; an unclassified hook
is acceptable. Do not invent a personal cost or number to fit a formula.

## Budget before scheduling

Estimate effort for each proposed item using the user's own timings when
available. Label other estimates. Count research, scripting, recording/design,
editing, captioning, accessibility, publishing and planned responses. Include
batch preparation once; do not double-count it or hide it outside the budget.

Show the total against the time budget and any post cap. Reduce the number,
complexity or formats until the plan fits. When capacity is zero, offer a pause
or reuse-only option within what the user allows. Do not exceed their budget
in pursuit of a default cadence. Include an optional cut-first item when useful.

Engagement is optional. If it supports the goal and the user wants it, allocate
it inside the same budget and pick a manageable list relevant to that account.
There is no mandatory 20 minutes a day, list of ten, or requirement to comment
before posting. Draft through `/ig-comment` only when requested; nothing is sent.

## Timing and learning

Use audience activity evidence and feasible user availability when supplied.
Without timing evidence, choose a practical test window, show the timezone and
label it a starting assumption. Do not call it the account's best posting time.
Timing, topic, format, creative and audience may interact; do not declare one
irrelevant without evidence. Use actual dates for the requested week.

For sparse/no results, start a baseline rather than inventing winners. Pick one
small test that fits the budget and addresses the primary goal. Specify what
changes, what is held reasonably similar, the primary measure, a consistent
observation age and a review date/window. State what could confound the result.
A couple of posts can guide a next experiment; they do not establish causality.
If evidence remains weak, continue or revise the test rather than automatically
scaling the highest-view post. Track actual execution separately from a draft.

## Output

Give the brief and evidence basis, then a calendar showing angle, format,
intended action, effort and the measurement to review. Include a budget total,
explicit assumptions, the experiment and a sensible review point. Scale the
format to the request; a simple plan needs no large reporting template.

Illustrative Turkish output with supplied capacity (not a default schedule):

```
HESAP: @studio_one
HEDEF: nitelikli atölye başvurusu
KAPASİTE: haftada 90 dakika, en fazla 2 paylaşım
KANIT: karşılaştırılabilir sonuç henüz yok; bu hafta başlangıç ölçümü

SALI  Karusel  Atölye öncesi yanıtlanacak üç soru  35 dk  Başvuru bağlantısı
CUMA  Hikâye   Bir önceki soruya gerçek bir örnek  15 dk  Mesajla soru sor

Ortak hazırlık: 20 dk; yanıtlar: 10 dk; pay: 10 dk. Toplam: 90/90 dk.
Saat: izleyici bölgesinde kullanıcının uygun olduğu pencere; henüz test edilmedi.
Ölçüm: içerikle ilişkilendirilebilen nitelikli başvurular, her içerikten 7 gün sonra.
Bu örnekte formatlar farklı; sonuç farkını yalnızca giriş cümlesine bağlamayız.
```

Save the plan to the resolved `plan` path, including account, period, goal,
capacity and review criteria. Pass those constraints and the publishing account
to downstream drafting skills. Nothing is scheduled or posted. The user can
ask for any slot to be drafted next.
