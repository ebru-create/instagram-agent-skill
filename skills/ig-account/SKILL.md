---
name: ig-account
description: >-
  Set up or select separate local Instagram account profiles. Use when the user
  manages multiple brands, adds an Instagram account, switches the publishing
  account, or asks which account's saved context is in use. This manages local
  files, not Instagram authentication or account settings.
---

# ig-account

Keep each publishing account's voice, plan, research, log and results under
`~/.claude/instagram/accounts/HANDLE/`. Handles are case-insensitive; a leading
`@` is accepted. Run this folder's helper by its installed absolute path:

```bash
python3 account.py list
python3 account.py init studio_one
python3 account.py show --account studio_one
```

`init` only creates the account directory, leaves existing files untouched,
and returns paths. Populate `voice.md` from the user's own examples or the
repository's `templates/voice.md`. Do not invent a voice or copy another brand.
Other context files are created only when the workflow produces their content.
`results.md` stores account-specific audit findings for later planning.
An optional `slop.json` lexicon override also stays in this directory; it never
changes another account's vocabulary rules.

Select the publishing account from the explicit request or clearly established
conversation context. A handle being researched, replied to or messaged is not
the publishing account. When ambiguous, list handles without reading their
content, then ask which publishing account to use. Keep this choice in the
conversation, never in a global "active account" file. Pass it explicitly to
every downstream skill and show `account: @HANDLE` in saved-output receipts.
If the user changes accounts, discard the previous account's context and
resolve fresh paths before drafting.

All persistent context reads and writes must use the returned `paths`. Missing
files stay missing: ask for the needed information or work from the current
request. Never fall back to a different account or legacy file. This is local
workflow separation, not OS access control for mutually untrusted users.

For an existing single-account installation, `python3 account.py show` still
returns the old `~/.claude/instagram/` paths when no named accounts exist.
Once any named account exists, require explicit selection even if there is
only one. `show` never creates files or silently picks an account.

To bring old data into a named account, first identify which publishing account
owns it with the user. Copy only the relevant voice, plan, swipe, log and results
files, preserving the originals. Review mixed history before importing it;
do not overwrite existing destination files. Do not auto-migrate during setup.

Research output can be saved directly to the selected account:

```bash
python3 ../ig-viral/swipe.py captured.tsv --account studio_one
```

`--account` and `--out` are mutually exclusive. `--data-root` allows an explicit
alternative root with `--account`; the helper's matching option is `--root`.
For a bundle installed without `ig-account`, reinstall the full pack to use
named accounts. The text-only tools still work independently.
