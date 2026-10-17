# Changes

Versions below describe development milestones in this fork. An entry is not
proof that a corresponding GitHub Release or tag has been published.

## [1.15.0] — Turkish draft and CTA review

- Recognize common Turkish comment imperatives and locations, distinguish quoted/negated action examples and avoid counting a comment question or comment-sharing phrase twice.
- Strengthen local caption prompts toward reader-facing copy, with an optional explicit `--cta` target.
- Supply only relevant writing guidance and record limited review signals for missing requested actions, multiple action categories, caption warnings and possible copied writer instructions.
- Add explicit opt-in `--revise-once` with a two-call ceiling, retained initial drafts/checks and failed-revision evidence; never auto-approve either draft.
- Recheck the original fictional local-model scenarios and retain the 1.14.0 evidence for comparison.

## [1.14.0] — bounded local model workflow

- Add a standard-library Ollama adapter for explicitly selected, already installed local models.
- Resolve one account's voice/strategy, load caption/human instructions, generate one draft and run the existing cleanup/lint tools.
- Record model digest, input hashes, raw response, draft hashes, timings and required manual review; preserve failed/incomplete run receipts.
- Add offline transport/workflow tests and an opt-in live validation using two fictional accounts and a fresh generic installation.
- Limit the first live integration to caption drafting; no autonomous tool calls, model downloads, account mutation or publishing in the runner.

## [1.13.0] — host-independent core

- Read core package identity/version from `instagram-agent.json`, independently of Claude plugin metadata.
- Add `--host codex`, `--host claude-code` and explicit-destination `--host generic` installation.
- Resolve account data through explicit CLI roots, `INSTAGRAM_AGENT_HOME`, existing legacy data or a neutral default.
- Preserve existing installations, local edits, backups and account selection; never auto-migrate account data.
- Document host capabilities and plain-language invocation for local/open-weight model agents; no model runner or provider adapter is bundled.

## [1.12.0] — release preparation

- Reorganize the README around the implemented workflow and current tool inventory.
- Add Turkish quick start and walkthrough, installation/recovery notes and a release procedure.
- Prepare deterministic source ZIPs from clean committed checkouts, with a per-file
  release manifest, SHA-256 checksums and an archive verifier.
- Test package integrity, exclusions, repeatability and installation from the extracted ZIP.
- Align marketplace descriptions with actual local capabilities and preserve upstream credit.
- Existing CLI names, JSON contracts and account data layouts are unchanged.

## [1.11.0] — explicit CSV import

Inspect source columns; map confirmed fields, numeric locale, dates and fixed
UTC offset; preview conversion errors; export only validated canonical CSV to a
new directory. Add Turkish import commands and end-to-end coverage.

## [1.10.0] — Turkish command interface

Add Turkish help, summaries, metric aliases and common error guidance through
`turkce.py`, preserving delegated JSON and exit-code behavior.

## [1.9.1] — end-to-end validation

Replay a fictional Turkish workflow from a fresh installed bundle through
exports, reported publications, analytics and experiment review, with failure paths.

## [1.9.0] — publication records

Separate user-reported publications from draft approvals; retain explicit
corrections and reconcile post identities against supplied CSV.

## [1.8.0] — content experiments

Record test criteria/assignments and review comparable observations with visible
missing data, dates and descriptive limits.

## [1.7.0] — account CSV analytics

Compute supported rates, coverage and self-excluded peer baselines from canonical CSV.

## [1.6.0] — carousel export

Generate numbered PNGs, captions, alt text, hashes and a review overview with
font, layout and contrast checks; Pillow/font support is optional.

## [1.5.0] — managed installation

Install/check/update the complete pack with manifests, local-edit protection,
backups, staged activation and caught-failure rollback.

## [1.4.0] — reproducible evaluation

Add explicit labelled fixtures, dataset/source hashes and per-language descriptive
metrics; distinguish synthetic pipeline checks from real-world validation.

## [1.3.0] — adaptive planning

Plan against confirmed goals, capacity and evidence; separate observations from
hypotheses and choose manageable review criteria.

## Earlier work

Reliability fixes, explicit account isolation and initial Turkish content support
preceded these milestones. See repository history for their exact changes.
