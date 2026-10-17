# Release preparation

The prepared version is **1.13.0**. This document describes producing a local
candidate and a later publication procedure. Preparing a PR, ZIP or CI artifact
does not publish a GitHub Release or tag.

## Verify the source

Use the repository root and a clean committed checkout. Confirm the version in
`.claude-plugin/plugin.json` matches the corresponding [changelog entry](../CHANGELOG.md).
The builder checks marketplace identity, complete installer sources and local
links in the release-facing documentation.

```bash
python3 -m pip install -r skills/ig-carousel/requirements.txt
python3 -m unittest discover -s tests -v
python3 scripts/install.py --dry-run
python3 validation/run_workflow.py --font /path/to/font.ttf --out /path/to/new-validation
```

Provide a real suitable font so rendering/workflow tests run rather than skip.
Inspect the workflow's report and images. Bundled data remains synthetic; this
verifies technical integration, not real account performance or model creativity.

## Prepare the candidate

```bash
python3 scripts/package_release.py --out /path/to/new-release
python3 scripts/package_release.py --verify /path/to/new-release/instagram-agent-skill-1.13.0.zip
```

The output contains:

| File | Purpose |
| --- | --- |
| `instagram-agent-skill-1.13.0.zip` | Source, installer, all skills/assets, docs, tests and fictional examples |
| `release-manifest.json` | Version, source commit, skill list and per-file SHA-256 inventory; also inside the ZIP as RELEASE-MANIFEST.json |
| `SHA256SUMS` | SHA-256 for the ZIP and external manifest |

Only Git-tracked files in explicit source/documentation directories and named
root files are selected. Untracked local files, Git internals, environments,
caches, generated output and account roots outside those directories are not
included. Review what you commit: the builder does not scan tracked content for
secrets or verify authorship. Selected symlinks and dirty tracked files are refused.

For the same commit/files, the ZIP is byte-repeatable: members are sorted, dates
and permissions fixed, and entries stored without compression to avoid zlib
version differences. Runtime timestamps, absolute paths and Python versions are
not injected into the release manifest. The output directory must be new.

Verification reads the archive without extracting/running it and compares entry
inventory and file hashes. Checksums detect corruption; they do not constitute
a signature or independent source-authenticity proof.

## Check the distribution

Extract the candidate into a new folder. From that extracted package root:

```bash
python3 scripts/install.py --skills-dir /path/to/new-skills --dry-run
python3 scripts/install.py --skills-dir /path/to/new-skills
python3 scripts/install.py --skills-dir /path/to/new-skills --check
python3 /path/to/new-skills/ig-account/turkce.py --help
```

The installer must work without `.git` or the original checkout. The package
builder itself requires Git for source selection; use it from the checkout when
rebuilding. Existing users follow [the update/recovery guide](installation.md)
with their original skills destination. Installing never migrates account data.

## Publication after merge

After the release-preparation PR is merged and its checks pass, build again from
that clean merged commit; the candidate's manifest must identify the commit
actually being released. A pre-merge local candidate identifies the PR commit,
not the eventual merge commit.

Review the final ZIP, changelog, hashes and install check. Create a version tag
and GitHub Release only as a separately requested publication action, targeting
that verified commit. Attach the three prepared files and use the changelog as
the release-note basis. Mark publication status accurately; do not describe a
candidate artifact as an already published stable release.

CI builds/verifies a candidate after the test matrix passes and retains it as an
artifact. It contains no automatic tag creation or release publication step.
