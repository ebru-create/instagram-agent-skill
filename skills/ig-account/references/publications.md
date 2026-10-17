# Local publication records

`publication.py` links a local content reference to a **user-reported published
post**, separately from draft approvals in `log.md`. It does not log into
Instagram, publish, verify a URL, schedule content or collect analytics. It uses
the full bundle's account helper and canonical CSV analyser; no extra packages
are required.

Use this workflow when the user says a particular item was published and supplies
its actual post ID and publication time. A draft approval, generated carousel,
planned date or experiment assignment alone is not proof of publication. Obtain
missing facts from the user rather than converting a draft into a published row.
Keep the same publishing account across the plan, record, CSV and experiment.

## Input

Use `example.publication.tr.json` as a schema example only: **every fact in that
file is fictional**. All seven fields are required nonempty strings; unknown
fields and duplicate JSON keys are rejected.

| Field | Meaning |
| --- | --- |
| account | Publishing handle matching `--account`; optional @ and case are normalized |
| content_id | Stable local content reference, 1–64 lowercase letters/digits/hyphens/underscores, first alphanumeric |
| post_id | Actual supplied published ID or URL, using exactly the same string as CSV and experiment assignments |
| format | `reel`, `carousel`, `image` or `story` |
| distribution | `organic`, `paid` (including boosted), or `unknown` |
| published_at | Actual publication timestamp with UTC offset; future planned dates are rejected |
| reference | User-provided publication reference/context; can be a URL or note, never an invented verification claim |

Use one content_id per published item. A repost or second publication gets a new
content_id and post_id; record its connection in the reference if useful. The
reference is text, not an automatically read file/link or proof from Instagram.
Notes can be English or Turkish; JSON keys are stable English identifiers.

## Validate and record

From the repository root, or use equivalent installed paths:

```bash
# Read-only validation: does not create or require a saved account.
python3 skills/ig-account/publication.py check skills/ig-account/example.publication.tr.json --account ornek_studyo

# For real work, initialize the account, then record YOUR supplied publication.
python3 skills/ig-account/account.py init YOUR_HANDLE
python3 skills/ig-account/publication.py record /path/to/your-publication.json --account YOUR_HANDLE
python3 skills/ig-account/publication.py list --account YOUR_HANDLE
```

`--root PATH` on each publication command selects a custom account-data root.
`record` requires an initialized account; there is no global active-account
setting or fallback to another brand. It writes to the helper's resolved
`publications` path, `accounts/HANDLE/publications.json`. It does not modify
`plan.md`, `log.md`, `results.md`, audits or experiment snapshots.

Duplicate content references and post IDs are refused. To correct an existing
record, keep its stable content_id and run `record ... --revise`. This appends a
new revision instead of removing the earlier entry. The new revision may fix
post_id, date, format, distribution or reference, but cannot take another active
record's post_id. State the correction in the reference. Unknown content_id with
`--revise` fails. `list` shows latest revisions and the total historical entry
count; the JSON file preserves the full entry history and each original input
SHA-256. Keep source input files separately to reproduce those hashes.

Writes use an exclusive lock and atomic file replacement; caught write failures
preserve the previous ledger. An existing `.publications.lock` blocks writes.
If a process was interrupted, establish that no writer is running before removing
a stale lock. Symlinked account files and malformed ledgers are refused rather
than overwritten. This is local workflow isolation, not multi-user access control
or a tamper-proof publication log. Back up the file with other account data.

## Reconcile CSV identities before interpretation

```bash
python3 skills/ig-account/publication.py reconcile /path/to/insights.csv --account YOUR_HANDLE
```

The CSV must follow [the canonical CSV contract](../../ig-audit/references/csv-analysis.md).
This command reads the latest publication revisions and validates the complete
input CSV. It never rewrites either source or changes prior analysis snapshots.
It reports:

- `matched`: same post ID, format, distribution and publication instant, with
  local content_id and active revision for downstream use.
- `identity_conflicts`: differing format/distribution/time, showing both values.
  Equivalent timezone offsets for the same instant match. Unknown treatment is
  preserved and will conflict with a known value until the source is resolved.
- `csv_without_record`: CSV IDs without a local publication record.
- `records_without_csv`: recorded IDs absent from this CSV; a limited export
  window may explain this. Absence is not proof the post was unpublished.

Input CSV SHA-256 is over original bytes; ledger SHA-256 is over the complete
validated ledger serialized as sorted-key JSON with Unicode preserved (including
history). These identify the data used, not its external authenticity.

Discuss conflicts and source coverage in the user's language. Correct only facts
the user confirms, then rerun analysis or experiment review on the corrected CSV.
Do not silently drop conflicting posts, infer missing IDs, overwrite historical
experiment assignments, or turn identity matches into performance evidence.
Use actual post IDs for experiment assignments; content_id links back to the
local plan/draft, not to a measured result on its own.
