# Content experiment records and CSV review

Use `experiment.py` to connect a specific hypothesis from `/ig-plan` to observed
post results from `/ig-audit`. It is a local descriptive comparison, with no
posting, reminders, login or platform calls. No extra Python packages are needed.
Use the same publishing account throughout. The tool reuses the account helper
and CSV analyser; install the full bundle.

## Define the test

Start with the user's goal, feasible production budget and available evidence.
Agree what changes, what stays reasonably similar, the primary metric, direction,
observation age, review date and a practically meaningful absolute difference.
Record confounders. Do not invent a success target or demand extra posts solely
to make a test fit. If no criterion has been agreed, keep a prose draft; the
structured tool requires an explicit criterion.

Use `example.experiment.tr.json` as a schema example. It is **entirely fictional**,
including its hypothesis, threshold and one-post-per-variant target. Those numbers
are not recommendations or evidence of adequate sample size. For an unpublished
plan use `assignments: []`; add actual published IDs as they become available,
without representing draft labels as published observations. Save revised plans
as new snapshots and disclose whether assignments/criteria changed after seeing results.
If a local [publication ledger](../../ig-account/references/publications.md)
exists, reconcile its latest identities against the CSV before assigning or
reviewing those IDs. Resolve conflicts with supplied facts; the ledger remains
user-reported and cannot verify creative execution or external publication.

| Field | Contract |
| --- | --- |
| schema_version | Integer `1` |
| account | Publishing handle matching `--account` |
| experiment_id | 1–64 lowercase letters/digits/hyphens/underscores, first alphanumeric |
| hypothesis, change | Nonempty text; separate the explanation being tested from the change |
| held_similar, confounders | Nonempty lists of notes; these are user assertions, not verified controls |
| primary_metric | A supported CSV analyser metric (e.g. `shares_per_reach`, `bookings`, `views`); video metrics need reel format |
| direction | `higher` or `lower`, chosen for this metric |
| minimum_effect | Positive finite absolute difference in metric units; `0.01` in a fraction means **one percentage point**, not 1% relative growth |
| format | `reel`, `carousel`, `image` or `story` |
| distribution | Known `organic` or `paid`; do not group unknown treatment |
| observation_hours | Positive elapsed hours after publication; measured timestamps must match exactly |
| review_at | ISO timestamp with explicit timezone, e.g. `2026-09-12T12:00:00+03:00` |
| min_posts_per_variant | Positive integer selected for this test's capacity; bookkeeping target, never a power/significance claim |
| assignments | List of `{ "post_id": "...", "variant": "control" }` or `"variant": "variant"`; unique real post IDs, possibly empty initially |

No extra/misspelled fields or duplicate JSON keys are accepted. Text notes may be
English or Turkish; stable JSON field names remain English. Interpret the report
in the user's language.

## Validate, then review

Commands from the repository root (use equivalent installed paths):

```bash
# Validate the plan; no account directory is needed, nothing is saved.
python3 skills/ig-plan/experiment.py skills/ig-plan/example.experiment.tr.json --account ornek_studyo

# Review the fictional sample with an explicit, reproducible as-of time.
python3 skills/ig-plan/experiment.py skills/ig-plan/example.experiment.tr.json --account ornek_studyo --csv skills/ig-audit/example.synthetic.csv --as-of 2026-09-13T12:00:00+03:00
```

Real input must follow [the canonical CSV contract](../../ig-audit/references/csv-analysis.md).
Use cumulative post snapshots, consistent definitions and matching attribution.
`--as-of` defaults to current UTC time and is recorded. It is supplied context,
not independent proof of when a review actually occurred. Future captures are
excluded from a historical review. Wrong-account or malformed CSV rows fail the
whole operation, even if they were not assigned to the test.

A review reports every assigned post as usable or excluded with a reason: missing
post, unavailable primary metric, capture after as-of, mismatched format/treatment,
or different observation age. Unassigned input IDs are disclosed and ignored.
Every assigned observation must be usable, and both variants must meet the target:
extra incomplete assignments cannot be silently dropped after seeing results.
A measured zero is usable; an undefined rate stays unavailable.

- `waiting_for_review`: as-of is before `review_at`; any group medians are provisional.
- `incomplete`: review time has arrived, but counts or assigned observations are incomplete.
- `ready_descriptive`: both conditions are met; this says nothing about statistical certainty.

Only `ready_descriptive` includes `variant_minus_control` (difference between
per-post medians) and `minimum_effect_met` (signed difference meets the chosen
threshold in the requested direction). Missing/before-date comparisons return
`null` for both. Group observations, assigned and usable counts remain visible.
Rates are fractions, not percentages. Median rates are not pooled event rates.
Threshold decisions use exact count ratios to avoid float rounding at boundaries;
displayed values are JSON numbers.

Do not call a result a causal winner or automatically scale it. Sample size,
selection, publication timing, topics and audiences may explain the difference.
The script verifies neither randomization nor actual creative execution. Use the
result and limitations to discuss continuing, revising, stopping or gathering
more evidence; preserve the user's goal and capacity in the next `/ig-plan`.

## Persist without overwriting

Add `--save` to either command for an initialized account; `--root PATH` selects
a custom account-data root. Every invocation creates a fresh
`accounts/HANDLE/experiments/experiment-UUID/report.json`. It includes the plan,
original-plan SHA-256, and review/input SHA-256 when applicable, plus save time.
Keep original input files separately to reproduce hashes. Identical experiment IDs
can have multiple snapshots; compare plan hashes when reviewing revisions.
`plan.md`, `results.md`, audit snapshots and earlier experiment records are preserved.
Symlink account/experiments paths are refused.

A saved plan is a record, not proof of prospective registration or a tamper-proof
log. It does not schedule a follow-up. Integrate interpreted findings into
`results.md` through `/ig-audit` and carry the same account to the next plan.
