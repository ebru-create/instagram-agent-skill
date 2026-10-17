# Instagram agent skill pack

Fourteen skills for account-specific Instagram planning, drafting, research and
review, with local Python tools for text checks, carousel export, publication
records, CSV analytics and content experiments. English and Turkish are supported.

[**Türkçe hızlı başlangıç**](docs/quickstart.tr.md) ·
[Turkish walkthrough](docs/walkthrough.tr.md) ·
[Installation and updates](docs/installation.md) ·
[Release preparation](docs/release.md) · [Changes](CHANGELOG.md)

The scripts operate on supplied local files. They have no Instagram login or
publishing client. An agent host uses the skill instructions to draft content;
the pack does not include a language model. Review drafts, then publish through
your own chosen workflow. A draft approval is separate from a reported publication.

## Requirements

- Python 3.10 or later; CI checks 3.10, 3.12 and 3.14.
- Git for a repository checkout. A prepared source ZIP also supports installation.
- The text, account, CSV and installer tools use the Python standard library.
- PNG carousel export additionally needs the [optional Pillow requirement](skills/ig-carousel/requirements.txt)
  and a user-supplied TTF/OTF font covering the content's characters.

No API key is required by these scripts. Your agent host's setup is separate.
The core metadata is `instagram-agent.json`; Claude marketplace metadata is an
optional host adapter. See [host-independent setup](docs/hosts.md) for Codex,
Claude Code and generic agents using local/open-weight models.

## Install

From a checkout:

```bash
git clone https://github.com/ebru-create/instagram-agent-skill.git
cd instagram-agent-skill
python3 scripts/install.py --host codex --dry-run
python3 scripts/install.py --host codex
python3 scripts/install.py --host codex --check
```

`--host codex` selects `~/.agents/skills`; `--host claude-code` selects
`~/.claude/skills`. Omitting `--host` keeps the old Claude destination.
`--host generic --skills-dir PATH` installs the same complete bundle for another
agent; it does not configure or download a model. For a project-local installation,
pass `--skills-dir /path/to/project/.agents/skills` for Codex, or the host's
project skill directory, consistently. Install all
fourteen folders together: executable tools share helpers and data files.

The repository also includes marketplace metadata for plugin installation:

```text
/plugin marketplace add ebru-create/instagram-agent-skill
/plugin install instagram-agent
```

See [installation and updates](docs/installation.md) for managed-file checks,
local edits, backups and recovery. Account data is separate from installed skills.

## Start with a publishing account

Commands below run from the repository root. In an installed pack, use the
corresponding installed tool's full path.

```bash
python3 skills/ig-account/turkce.py hesap ekle YOUR_HANDLE
python3 skills/ig-account/turkce.py hesap goster --hesap YOUR_HANDLE
python3 skills/ig-account/turkce.py --help
```

Use the returned voice/strategy paths to record your own examples, audience,
goal, language and production capacity. [Voice](templates/voice.md) and
[strategy](templates/strategy.md) templates are also bundled by the installer
under `ig-account/assets/templates/`. Account creation does not invent profiles
or populate results.

Each named account has separate context and records under
the resolved root's `accounts/HANDLE/` directory. `--root`/`--data-root` (Turkish
`--kok`) overrides `INSTAGRAM_AGENT_HOME`. Without an override, an existing
`~/.claude/instagram` is retained, otherwise `~/.local/share/instagram-agent` is
used. Roots are never merged or searched for a missing account. Select it explicitly; there is no global
active-account setting or fallback to another brand. Legacy paths still resolve
without an account only when no named accounts exist. See [account setup](skills/ig-account/SKILL.md).

## The workflow

| Step | Skill/tool | Result |
| --- | --- | --- |
| Set the brief | `/ig-account`, `/ig-plan` | Voice, goal, capacity and a feasible plan |
| Draft | `/ig-reel`, `/ig-carousel`, `/ig-story`, `/ig-caption` | Copy and accessibility text for review |
| Check text | `/ig-human`, caption/hook/beat tools | Editorial diagnostics, including unavailable checks |
| Export | [Carousel renderer](skills/ig-carousel/references/rendering.md) | Numbered PNGs, caption, alt text and overview |
| Record execution | [Publication records](skills/ig-account/references/publications.md) | User-reported real post ID/time linked to local content |
| Prepare data | [CSV importer](skills/ig-audit/references/csv-import.md) | Explicit mapping, preview and validated canonical CSV |
| Interpret | `/ig-audit`, [CSV analyser](skills/ig-audit/references/csv-analysis.md) | Comparable observations with coverage and limits |
| Learn | `/ig-plan`, [experiment review](skills/ig-plan/references/experiments.md) | Descriptive test result and next review criteria |

Nothing in that chain schedules or posts content. A local publication record is
user-reported; it is not platform verification. Account isolation is a workflow
convention, not access control between mutually untrusted users.

## The fourteen skills

| Skill | Purpose |
| --- | --- |
| `/ig-account` | Separate local profiles and reported publications |
| `/ig-plan` | Goals, capacity, calendar and manageable experiments |
| `/ig-reel` | Script, hook and spoken pacing |
| `/ig-caption` | Caption, ask, search terms and editorial checks |
| `/ig-human` | Conservative cleanup and text diagnostics |
| `/ig-carousel` | Cover/slides, alternative text and optional PNG export |
| `/ig-story` | Story sequences and intended action |
| `/ig-viral` | Review supplied research; compare appropriate baselines |
| `/ig-audit` | Interpret supplied results with uncertainty |
| `/ig-profile` | Profile review using an editorial rubric |
| `/ig-comment` | Draft relevant comments |
| `/ig-reply` | Draft replies |
| `/ig-dm` | Draft direct-message flows |
| `/ig-repurpose` | Adapt supplied content to other formats |

Skill instructions are in each folder's `SKILL.md`. Pasting instructions into a
chat does not install their Python tools or shared resources.

## Executable tools

| Entrypoint | Purpose |
| --- | --- |
| `skills/ig-account/turkce.py` | Turkish commands, help, summaries and common errors |
| `skills/ig-account/account.py` | Account initialization, listing and paths |
| `skills/ig-account/publication.py` | Record/revise reported publications; reconcile CSV identities |
| `skills/ig-human/humanize.py` | Text cleanup with explicit content language |
| `skills/ig-human/detect.py` | Applicable editorial checks; unsupported checks stay null |
| `skills/ig-reel/hookscore.py` | Hook diagnostics |
| `skills/ig-reel/beats.py` | Speaking-time estimate and beat sheet |
| `skills/ig-caption/caption.py` | Caption checks and visible-text preview |
| `skills/ig-viral/swipe.py` | Supplied TSV research, separated baseline groups |
| `skills/ig-carousel/render.py` | Validated local PNG export |
| `skills/ig-audit/import_csv.py` | Inspect/map/preview/export source CSV |
| `skills/ig-audit/analyse.py` | Canonical CSV rates, coverage and comparable cohorts |
| `skills/ig-plan/experiment.py` | Validate a test plan and review assigned observations |

[Turkish command guide](skills/ig-account/references/turkce-kullanim.md) covers
`--dil`, `--hesap`, metric aliases and examples. `--json` preserves the delegated
machine payload and exit code. `--ayrinti` exposes original technical diagnostics,
which may be English. Individual CLIs keep their existing names and defaults.

## Data and interpretation limits

- Inputs labelled fictional/synthetic are development examples, never account results.
- Scores are editorial heuristics, not authorship detection, view predictions or causal evidence.
  Turkish voice scoring and other unsupported checks remain N/A. Keep natural copy
  rather than changing it to increase a score.
- A successful process or valid JSON is not editorial approval. Some JSON tools
  return exit 0 with a review state; read the verdict and coverage.
- Plans fit confirmed goals and capacity. Draft approvals do not prove publication.
- CSV import requires explicit field, locale and date mappings. Source semantics,
  cumulative measurement scope and business attribution remain user assertions.
  Missing values are not zero; conversion errors block export.
- Comparisons disclose format, treatment, measurement age and usable counts.
  Small/selected data and unverified controls limit conclusions. Practical test
  thresholds and readiness do not establish statistical significance.
- The pack does not include an Instagram connector, scraper, automated publishing,
  multilingual typesetting beyond the renderer's supported Latin-script scope,
  or full Turkish morphological analysis.

Platform behavior can change. Validate platform-specific advice against current
primary documentation when it matters; local lint rules are not authoritative
platform specifications. Original upstream benchmark claims are discussed as
unreproduced historical claims in the [evaluation guide](evaluation/README.md).

## Validation and packaging

```bash
python3 -m unittest discover -s tests -v
python3 validation/run_workflow.py --font /path/to/font.ttf --out /path/to/new-validation
```

Without optional Pillow/font support, rendering tests are skipped. Release
validation installs Pillow and provides a font so those tests run. The
[synthetic workflow](validation/README.md) checks a fresh installed pack through
localized CSV import, exports, records, audit and experiment review, plus failure
paths and a second account. It does not evaluate an independent model's creative
behavior or real account performance.

[Evaluation](evaluation/README.md) records dataset/source hashes and descriptive
metrics on explicit labels; bundled labels are synthetic pipeline fixtures.

From a clean committed checkout, prepare and verify a source ZIP:

```bash
python3 scripts/package_release.py --out /path/to/new-release
python3 scripts/package_release.py --verify /path/to/new-release/instagram-agent-skill-1.12.0.zip
```

The [release guide](docs/release.md) describes the inventory, checksums and final
publication procedure. A local candidate or CI artifact is not a published release.

## Credit and license

Maintained at [ebru-create/instagram-agent-skill](https://github.com/ebru-create/instagram-agent-skill).
Originally made by Jake Schincariol, [opusjake.ai](https://opusjake.ai), at
[Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill).

[MIT license](LICENSE). Preserve the upstream attribution when redistributing.
