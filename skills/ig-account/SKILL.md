---
name: ig-account
description: >-
  Set up separate local Instagram account profiles and track user-reported
  publications. Use when the user
  manages multiple brands, adds an Instagram account, switches the publishing
  account, asks which account's context is in use, records a published post, or
  reconciles publication identities against CSV data. This manages local
  files, not Instagram authentication or account settings.
---

# ig-account

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
repository's `templates/voice.md` (installer-bundled copies are at
`assets/templates/voice.md` beside this skill). Do not invent a voice or copy
another brand.
Other context files are created only when the workflow produces their content.
`results.md` stores account-specific audit findings for later planning.
The optional resolved `publications` path (`publications.json`) stores
user-reported published items separately from draft approvals. When the user
reports a publication, use [publication records](references/publications.md)
and `publication.py` with their actual post ID/time and a stable local content
reference. Missing facts stay unknown. This does not publish or verify Instagram
activity; setup does not auto-create a publication ledger.
`strategy.md` stores supplied or confirmed goals, production capacity and review
criteria; use `templates/strategy.md` from the repository or the installer-bundled
`assets/templates/strategy.md` if useful. It is optional and is not auto-created or populated with guessed preferences.
Optional `slop.json` (English) and `slop.tr.json` (Turkish) lexicon overrides
also stay in this directory; it never
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
named accounts. Text-only drafting can use supplied context; executable text
tools require the bundled `ig_language.py` helper.
