# Installation, updates and recovery

Run commands from a full repository checkout or an extracted prepared source ZIP.
Python 3.10+ is required. The installer uses only the standard library and does
not install Python packages, create account profiles or reload the agent host.

```bash
python3 scripts/install.py --dry-run
python3 scripts/install.py
python3 scripts/install.py --check
```

Default destination: `~/.claude/skills`. Add the same `--skills-dir PATH` to every
command when using another destination. All fourteen `ig-*` folders and shared
assets install together. Voice/strategy templates are assembled under
`ig-account/assets/templates/`. Optional Pillow/fonts are separate; see
[carousel export](../skills/ig-carousel/references/rendering.md).

A real install stages the bundle and runs 13 functional checks: six text/research
tools in two languages and the account resolver with temporary inputs. The full
test suite covers additional installed tools and end-to-end behavior. `--check`
compares installed hashes with the manifest and current source, then runs the
same 13 checks. `--dry-run` checks source/conflicts without running tools or
creating a destination.

## Updating

For a checkout, first fetch the desired reviewed source version:

```bash
git pull --ff-only
python3 scripts/install.py --update --dry-run
python3 scripts/install.py --update
python3 scripts/install.py --check
```

For a source ZIP, extract the new version into a new folder, verify its release
manifest, and run the installer there with the same destination. An installed
copy may differ from an older checkout; use the matching source for `--check`.

The manifest `.instagram-agent-install.json` records package-owned file hashes.
Extra files and unrelated skills stay intact. Modified package-owned files stop
an update; missing files can be repaired. Account data normally lives separately
under `~/.claude/instagram/` and is not migrated or replaced by installation.

For a deliberate replacement of manually copied folders or package edits:

```bash
python3 scripts/install.py --update --replace-existing --dry-run
python3 scripts/install.py --update --replace-existing
```

Use replacement only when you intend the source package to replace those edits.
Keep brand vocabulary in the selected account's `slop.json`/`slop.tr.json` override
rather than editing installed package lexicons.

## Backups and recovery

Updates retain old folders/manifest under `.instagram-agent-backups/` inside the
chosen skills directory and print the backup path. A caught activation error
rolls back replaced folders. Abrupt process termination or power loss is not a
global transaction: inspect retained backups/staging folders before recovery.

To restore a completed update, close active skill work, move affected current
folders aside, and restore matching backed-up folders and manifest as one
version. Preserve needed extra files first; do not merge old/new executable code
blindly. Backups are not automatically deleted.

Concurrent installs are blocked by `.instagram-agent-install.lock`. Establish
that no writer is running and inspect an interrupted installation before
removing a stale lock. Reload the host's skill session after an update if it
still shows old instructions.
