# Reproducible hook evaluation

Run from the repository root with Python 3.10+; no third-party dependencies,
accounts, collection tools or network are needed:

```bash
python3 evaluation/evaluate.py evaluation/fixtures.json --out /tmp/hook-report.json
```

The 12 bundled English/Turkish examples are synthetic development fixtures,
authored for testing this pipeline. Their binary labels express an intended
editorial distinction. They are not independent human ratings, real outcomes,
a held-out benchmark, or the upstream 74-hook corpus. Even a perfect fixture
AUROC is not validation of real-world hook quality, reach or Turkish scoring.
The checked-in `example-report.json` is a sample run, with its exact inputs,
source hashes and Python version. CI produces a fresh fixture report per Python
version as an artifact. Numeric results may change when scorer/catalogues change;
CI checks the pipeline, not an arbitrary performance threshold.

## Dataset contract

Use the same JSON shape as `fixtures.json`: `schema_version: 1`, `metadata`
and non-empty `rows`. Required metadata fields are:

| field | meaning |
| --- | --- |
| id | stable dataset identifier/version |
| kind | `fixture` or `observational` |
| split | `development` or `holdout`; a declaration, not verified by the tool |
| task | what is evaluated, including collection/selection protocol |
| positive_label | exactly what label 1 means, metric/window/threshold when applicable |
| provenance | who collected/annotated the data, when and how |
| usage_rights | why this corpus can be used; do not publish a private corpus by default |

Each row needs a unique `id`, an `account` grouping identifier, `language`
(`en`/`tr`), non-empty `hook` and integer `label` (0/1). Labels are supplied by
the dataset owner; the evaluator does not invent outcomes or derive truth from
the scorer's own score. Observational rows also need a non-empty `source`
(for example the owned post reference) and `observed_at` capture date in
`YYYY-MM-DD` format. Keep
comparable observation windows, formats and organic/paid treatment in the
collection protocol. Record exclusions and avoid selecting only visible hits.

Optional `expected_formula` is a language-specific catalogue ID or `null`
when the human annotation expects abstention. Omit the field when unannotated.
These three cases are distinct. Duplicate IDs and identical hooks within the
same account/language are rejected so accidental repeats do not get extra weight.
Account IDs are grouped case-insensitively; keep aliases consistent yourself.

Freeze a holdout before tuning rules on development data. A file declared as
holdout is not proof it was independent. This script does not split data,
scrape platforms, verify ownership or make observational comparisons causal.

## Reading a report

- AUROC uses the supplied binary labels and raw, unrounded hook scores. Ties
  receive half credit. Higher scores are assumed to favor label 1.
- English and Turkish are reported separately. Pooled AUROC within a language
  can reflect account differences, so inspect each account and the unweighted
  mean of within-account AUROCs. Accounts with only one label are excluded from
  that mean and counted as unevaluable; an all-one-class result is `null`.
- Formula coverage measures how often the classifier names a formula. It says
  nothing about correctness by itself. Exact annotation agreement includes
  expected abstentions; agreement when classified uses only annotated rows on
  which a formula was predicted. Both show their own denominators. Missing
  annotations are excluded; an empty denominator yields `null`.
- Reports include class/sample counts, per-row IDs/scores/predictions, dataset
  SHA-256, hashes of the evaluator/scorer/classifier/helper/catalogues and Python
  version. Hook text is not copied into the report. No timestamp or network
  result makes repeated runs differ within the same environment.
- Small, selected or repeatedly tuned samples are weak evidence. Confidence
  intervals are not estimated here. Do not turn this report into a universal
  accuracy claim or promise that text alone predicts views.

The upstream README reported AUROC 0.83/0.56 and classification coverage 8%/49%.
The original corpus and measurement script are absent, so this fork cannot
reproduce those numbers. Current code has also changed. The new runner provides
a way to measure a supplied corpus honestly; its synthetic fixtures do not
recover the old evidence.
