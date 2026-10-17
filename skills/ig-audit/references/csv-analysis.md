# Local CSV analysis

`analyse.py` computes descriptive metrics from **your mapped CSV**, with no login,
API calls or external packages. It is not a universal parser for native Instagram
or Meta exports. Map supplied fields to the template, preserving their definitions;
if a mapping is uncertain, leave the measure blank and describe the uncertainty.
Never infer missing post attribution. Screenshots and prose can still be audited
manually through the main skill.
For unfamiliar headers, Turkish/English numeric formatting or explicit date
conversion, use [the inspect/map/preview importer](csv-import.md) first. It exports
only a fully validated canonical file; existing canonical input needs no conversion.

From the repository root (use the equivalent installed skill path):

```bash
python3 skills/ig-audit/analyse.py skills/ig-audit/example.synthetic.csv --account ornek_studyo --primary-metric shares_per_reach
```

The bundled sample is **entirely fictional**, for calculations only. Copy
`template.csv` and add your own rows for real work. The sample does not demonstrate
that a strategy improves performance.

## CSV contract

UTF-8, comma-delimited, one header row; quote values containing commas. Headers
are English identifiers. Header order is flexible. Unknown/duplicate headers,
wrong accounts, duplicate post IDs and malformed values fail the whole input.
Counts must be cumulative from publication through capture, not a selected
calendar-range subtotal. One snapshot per published post per input; do not repeat captures or
sum cumulative metrics from multiple exports. Use a consistent metric definition
and collection method within an input; split files if definitions differ.

Required columns, nonempty in every row:

| Column | Value |
| --- | --- |
| account | Publishing handle; must match `--account` (optional leading @) |
| post_id | Unique post ID or URL, never a draft identifier |
| format | `reel`, `carousel`, `image`, `story` |
| distribution | `organic`, `paid`, `unknown`; boosted posts belong in paid |
| published_at, captured_at | ISO timestamps with explicit timezone offset, e.g. `2026-09-01T12:00:00+03:00`; capture must be later |

Optional columns (omit column or leave cell blank for unavailable):

- Full nonnegative integer counts: `views`, `reach`, `shares`, `saves`, `follows`,
  `non_follower_reach`, `starts`, `viewers_3s`, `enquiries`, `bookings`.
  No K/M/B suffixes, decimal commas or thousands separators. A recorded `0` is
  observed zero; blank is unknown. Shares remain total shares, not private sends.
- `duration_seconds`, `average_watch_seconds`: nonnegative decimal seconds with
  a dot; reels only, together with `starts` and `viewers_3s`. Other video formats
  need a future explicit schema extension. Watch time can exceed length due to loops.
- `enquiries`, `bookings`: only counts with confirmed post attribution and a
  consistent user-defined qualification rule; never allocate account totals.

`non_follower_reach` cannot exceed reach; `viewers_3s` cannot exceed starts.
Shares/saves/follows may include repeated events and are not capped at reach.

## Report interpretation

Choose `--primary-metric` to name the measure aligned to the account goal. It
labels the report; it does not create a winner ranking or establish causality.
JSON uses stable English keys; explain the findings in the conversation language,
including Turkish when requested.

Computed rates: shares/reach, saves/reach, follows/reach, non-follower reach/reach,
and viewers at 3 seconds/starts. Units are fractions (`0.04` = 4%). Retention needs
reported reel duration >=3 seconds. Missing numerator, missing denominator or
zero denominator gives JSON `null`. Raw values remain visible alongside rates.

Cohorts use format, distribution and **exact elapsed seconds** between publication
and capture. Different ages stay separate, even if that leaves singletons. Do not
round timestamps to force comparability. Equal ages still do not control topic,
audience, publication period or selection bias. Cohorts disclose publication
range, count, per-metric usable count and median of available post values
(not ratio of pooled totals). Unknown distribution gets descriptive medians but
no relative-view comparison.

Each post's relative views divide its views by the median views of **other** posts
in its cohort. The post itself is excluded. No peers or zero peer median gives
`null`. Missing peer views are excluded and peer n is disclosed; a single peer
is not strong evidence. Do not compare multiples from unrelated cohorts as a
universal ranking. Read `limitations` before proposing experiments.

The report includes input SHA-256; keep the source file separately for reproduction.
It does not verify whether supplied numbers came from the platform or whether
attribution is valid. There is no automatic sales attribution or causal diagnosis.

## Save a snapshot

Default operation prints JSON and does not require or create an account folder.
To persist, initialize/select the publishing account with `ig-account`, then add
`--save` (and `--root PATH` for a custom account root). This creates a fresh
`accounts/HANDLE/audits/audit-UUID/report.json` and returns its path. Existing
snapshots and `results.md` are preserved. Symlink account/audits paths are refused.
The report contains post identifiers and metrics: store/share it as account data.

Use the snapshot as calculation evidence for the audit narrative; update the
resolved `results.md` through the main skill only after interpreting coverage,
source definitions and limitations. Hand confirmed findings to `/ig-plan` with
the same account and agreed observation window.
