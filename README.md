# The Instagram agent skill

Fourteen Claude skills that run an Instagram account. Free, MIT, no signup, no
API key, nothing to connect.

One of them writes your Reels off 26 hook formulas and scores the hook before
you waste a take on it. One goes and finds the reels that are actually working
in your niche and ranks them by how far each beat its own account. One writes
the caption and shows you exactly what the feed shows before the "... more".
One scores your profile out of 100 and rewrites what lost points. One plans the
week.

And one is the humanizer. It cleans stock vocabulary and copy-paste artefacts
while preserving meaningful Unicode, then reports the applicable checks from
a five-check panel. Typography normalization is optional.

**Nothing gets posted until you say yes.** These skills write. You post.

## Install

Paste this into Claude:

```
https://github.com/ebru-create/instagram-agent-skill

Install this skill, then confirm /ig-reel works.
```

Or do it yourself, in Claude Code:

```bash
git clone https://github.com/ebru-create/instagram-agent-skill.git
cd instagram-agent-skill
python3 scripts/install.py --dry-run
python3 scripts/install.py
python3 scripts/install.py --check
```

Or as a plugin:

```
/plugin marketplace add ebru-create/instagram-agent-skill
/plugin install instagram-agent
```

Project-local instead of global: pass `--skills-dir /your/project/.claude/skills`
to the installer and the check command. No Claude Code at all? Paste any single
`SKILL.md` at the top of a chat and it runs as a mode. You lose the five Python tools, which is most
of the point of `/ig-reel` and `/ig-human`, but the rest works.

Then spend ten minutes on `templates/voice.md`. Copy it to
the `voice` path returned by `skills/ig-account/account.py show` and fill it
in, or send Claude three of your own
reels and say "write my voice.md from these". Each skill uses the selected
account’s file. It
matters more here than on other platforms, because you have to say the words
out loud.

## Install and update checks

The installer targets `~/.claude/skills` by default, or the explicit directory
passed with `--skills-dir`. It installs all fourteen `ig-*` folders together,
including the shared language helper and Turkish catalogues. Voice and strategy
templates are bundled under `ig-account/assets/templates/` so they remain
available after installation without the repository checkout.

`--dry-run` checks sources and conflicts without creating directories or running
tools. A real install stages files and runs thirteen functional checks: six
text tools in both languages plus the account resolver with a scratch profile.
It only activates the staged folders after these pass. `--check` verifies the
installed file hashes against the manifest and this checkout, then runs the
same tool checks. It does not modify installed files or real account profiles;
functional checks use temporary input, not your saved content.

To update from a newer checkout, run from the repository root:

```bash
git pull --ff-only
python3 scripts/install.py --update --dry-run
python3 scripts/install.py --update
python3 scripts/install.py --check
```

For a custom destination, repeat the same `--skills-dir` in every command.
The installer records package-owned files in `.instagram-agent-install.json`.
It preserves extra files in skill folders and unrelated skills. Modified
package-owned files stop an update; missing files can be repaired. Account
profiles under `~/.claude/instagram/` are not installed, copied or migrated.

Old folders copied manually have no installation manifest. To replace those,
or deliberately replace local edits, use the explicit option below only when
you want the checkout's packaged versions to become active:

```bash
python3 scripts/install.py --update --replace-existing --dry-run
python3 scripts/install.py --update --replace-existing
```

Every update that replaces existing folders retains the old folders and manifest
under `.instagram-agent-backups/` within the chosen skills directory. The result
prints the backup path. Nonconflicting extra files stay in the active copy as
well. Move intentional brand-specific lexicon edits into that account's override before
updating, so future updates need not replace custom vocabulary.

A caught activation error rolls the previous folders back. An abrupt power loss
or process termination is not a globally atomic transaction: retain the hidden
backup/staging directories for recovery if interrupted. To restore a
completed update manually, close active skill work, move the affected current
folders aside, then restore the corresponding backed-up folders and manifest.
Do not blindly merge old and new code. The installer never deletes old backups.
Concurrent installer runs are blocked by `.instagram-agent-install.lock`; after an abrupt interruption, inspect the
installation and backups before removing a stale lock directory and retrying.

These commands install local files; they do not log into Instagram, publish
content, install Python packages, or automatically reload a running agent.
Restart/reload the host's skill session if it still shows the old instructions.

## Separate publishing accounts

For multiple brands, create a separate local folder for each handle. From the
repository root (or the corresponding installed skill paths):

```bash
python3 skills/ig-account/account.py init studio_one
python3 skills/ig-account/account.py init studio_two
python3 skills/ig-account/account.py list
python3 skills/ig-account/account.py show --account studio_one
```

Each folder under `~/.claude/instagram/accounts/HANDLE/` holds its own `voice.md`,
`strategy.md`, `plan.md`, `swipe.md`, `log.md` and `results.md`. Setup creates
the directory without importing or overwriting files. Fill in its voice profile from your own
examples, then say which publishing account a request is for:

```
/ig-plan for @studio_one: plan next week's posts
/ig-caption for @studio_two: caption this workshop photo
```

The selection stays in the conversation and is passed between skills. There is
no global active account that another chat can switch. A missing file never
loads another brand's data. When the publishing account is unclear, the agent
asks; accounts being researched or messaged do not change this selection.
This separates workflows on one computer; it is not a security boundary
between different users with filesystem access.

Existing single-account files at `~/.claude/instagram/` still work with `show`
when no named accounts exist. Once a named account exists, select it explicitly.
Old files are preserved. To migrate, identify their owner, then copy only that
account's files into its new folder without overwriting existing files. Mixed
history needs review before copying. Setup never migrates automatically.

Save research to the selected publishing account with:

```bash
python3 skills/ig-viral/swipe.py captured.tsv --account studio_one
```

`--account` and `--out` cannot be combined. For an alternative data root, use
`account.py --root /your/data init studio_one` and the matching
`swipe.py --data-root /your/data --account studio_one`. Named accounts require
the bundled `ig-account` folder; install all `ig-*` folders together.

## Turkish content

The six text tools support explicit `--language tr`; English remains the CLI
default. All skill workflows pass the content language from the request or the
selected account's voice profile. Add language, audience locale/timezone and
preferred `sen`/`siz` address to that profile.

```bash
python3 skills/ig-human/humanize.py draft.txt --language tr --report
python3 skills/ig-human/detect.py draft.txt --language tr --json
python3 skills/ig-reel/hookscore.py --hook "Üç günde iki saat kazandım" --language tr
python3 skills/ig-reel/beats.py script.txt --language tr --wpm 140
python3 skills/ig-caption/caption.py caption.txt --language tr --keywords "iş geliştirme,yaratıcılık"
python3 skills/ig-viral/swipe.py captured.tsv --language tr --account studio_one
```

Word counting keeps Turkish letters, apostrophes and written amounts together.
Matching handles Turkish `I/ı` and `İ/i`, Unicode hashtags and common actions
such as `kaydet`, `paylaş` and `Yorumlara REHBER yaz`. The Turkish cleaner uses
a small, conservative `slop.tr.json`; vocabulary like `strateji` is not banned.
Keep brand-specific overrides separate: the resolver returns `lexicon_tr` for
`slop.tr.json` and `lexicon` for English `slop.json`. An override's language must
match the command; old unmarked lexicons are treated as English.

Turkish VOICE scoring is N/A: English contractions and explicit pronouns are
not evidence for Turkish voice. Hook address is also N/A when person cannot
be inferred from the supported explicit cues. Review against real brand samples
instead. Turkish hook formulas are a limited starter catalogue; unknown hooks
stay unclassified. The English hook benchmark AUC does not validate Turkish
scores. All scores remain editorial heuristics, and speaking time is an estimate;
use your measured speaking rate with `--wpm`.

These are content-language improvements; command names and most diagnostic
labels remain English. Mixed-language statistical scoring and full Turkish
morphological analysis are not implemented. Research counts still require full
integers or the documented English K/M/B notation; convert Turkish display
abbreviations to full integers instead of guessing their magnitude.
Install the whole pack, including `ig-account/ig_language.py`, which the six
text tools now share. No third-party Python packages are required.

## Plans that fit the account

`/ig-plan` uses a confirmed goal, the time and resources available, format
constraints and relevant account results. There is no fixed weekly post count,
Reel minimum, daily Story requirement or compulsory engagement routine.
Preparation, production, publishing and any planned responses count toward the
same budget. If there is no capacity, a pause is a valid plan.

Use `templates/strategy.md` to record supplied or confirmed preferences at the
selected account's resolved `strategy` path. The brief is optional; unknown
fields stay unknown and provisional assumptions stay in the plan. A request can
also provide the information directly:

```
/ig-plan for @studio_one: Türkçe atölye başvurusu hedefliyoruz. Haftada 90 dakika,
en fazla iki paylaşım, kamera karşısına çıkmadan. Geçmiş sonuç henüz yok.
```

Without results, the skill sets a baseline and a review point rather than
inventing a winning format or best posting time. With results, `/ig-audit`
separates observations from explanations and compares compatible formats,
post ages and organic/paid treatment. Zero/missing denominators stay N/A;
missing results are not zero and total shares are not relabelled as private
sends. Low views alone do not identify a hook problem, and reach without follows
does not prove a profile problem. Each suggested experiment names its metric,
observation window and the main uncertainty.

This update changes skill instructions and saved-context paths. It does not
add an automatic scheduler or a statistical causal-inference engine.

## The fourteen

| command | what it does |
| --- | --- |
| `/ig-account` | Separate local profiles for each publishing account, with explicit account selection. |
| `/ig-reel` | One idea into a Reel. Three hooks from [26 formulas](skills/ig-reel/hooks.json), scored, then the script, the on-screen text and a timed beat sheet. |
| `/ig-viral` | Goes and finds what is working in your niche, ranks it by multiple over each account's own median, names the formula, writes the swipe file. |
| `/ig-caption` | The caption, linted. Shows you the 125 characters the feed actually shows before the tap. |
| `/ig-carousel` | Swipe posts. The cover that earns the swipe, slide copy, and the 1080x1350 files. |
| `/ig-story` | A Story sequence sized to the plan, which sticker does which job, and the DM funnel that starts with them moving first. |
| `/ig-profile` | Scores your profile against a [12-part rubric](skills/ig-profile/rubric.json) out of 100, then rewrites in fix-first order. |
| `/ig-plan` | A week that fits the account’s goal, production capacity and relevant results, with optional engagement and a review point. |
| `/ig-human` | The humanizer. Two scripts that actually run. See below. |
| `/ig-comment` | Comments on other people's posts. Nine types, picked by what the post actually is. Never "🔥🔥🔥". |
| `/ig-reply` | The thread under your own post. Sorts into keyword / lead / substance / question / support / noise, then writes in that order. |
| `/ig-dm` | The keyword delivery, the first message, the collab pitch, and the two follow-ups. Two. |
| `/ig-repurpose` | One video, podcast or newsletter into a week of reels and carousels that each stand alone. |
| `/ig-audit` | Goal-based analysis with comparable cohorts, explicit missing data and testable explanations. |

## The five tools that actually run

No dependencies, no network, nothing uploaded. They run on your machine, on
your text.

### Hooks

```bash
python3 hookscore.py hooks.txt              # rank your options
python3 beats.py script.txt --target 30     # time it before you shoot it
```

```
HOOK RANKING
==============================================================================
->  85.6 STRONG  Nobody tells you that your first 30 reels are supposed to f...
        weakest: SPECIFICITY (75)
    81.4 STRONG  I lost $18,000 because of one missing contract.
        weakest: ADDRESS (70)
    54.4 OK      Stop scrolling if you want to grow on Instagram in 2026 🔥
        weakest: STAKES (70)
        dealbreaker: Opens with "stop scrolling". Asking for attention proves
                     you have not earned it.
     9.6 WEAK    Hey guys, today I wanted to talk about content strategy
        weakest: FRONTLOAD (0)
        dealbreaker: Greeting. Nobody came to the feed to be greeted.
```

`beats.py` estimates how long each line takes to say, stacks them into
timecodes, and flags the four things that kill a Reel in the edit: a hook that
runs past three seconds, a beat long enough for the viewer to leave, a run of
lines with nothing concrete in them, and no loop back to the first line.

```
BEAT SHEET  ·  73 words  ·  ~26.6s at 165 wpm  ·  target 30.0s
========================================================================
  0:00.0   2.9s  HOOK    I lost $18,000 because of one missing contract.
  0:02.9  14.6s  MID     Here is the exact clause I now put in every single...
                         ^ 14.6s on one beat
  0:17.4   2.9s          Section 4. Payment on delivery, not on approval.
  0:20.4   2.9s          Approval is a feeling. Delivery is a date.
  0:23.3   3.3s  CTA     That one word change is worth $18,000 to me.
------------------------------------------------------------------------
  - Beat 2 runs past 4s. Either split the line or change what is on screen
    inside it. A static frame is where people leave.
  - Loops: the last beat repeats "$18,000" from the hook. Second watches are
    free reach.
  - 3.5s under target. Either add 9 words or shoot it short. Short is usually
    right.
```

### The caption

```bash
python3 caption.py caption.txt --keywords "client contracts,freelance pricing"
```

Instagram gives a caption about 125 characters in the feed and hides the rest
behind a tap. Almost every caption that fails, fails there. So the first thing
this prints is that window, as a box, the way a scrolling stranger reads it:

```
  WHAT THE FEED SHOWS
  +------------------------------------------------------+
  | I lost $18,000 because of one missing clause in a    |
  | contract, and the worst part is that I had read the  |
  | thing twice before I si                              |
  +-------------------------------------------- ... more +

  PASS  LENGTH            389 / 2200 characters
  WARN  FIRST LINE        133 characters, so it gets cut at 125 mid-thought
  PASS  HOOK IS CONCRETE  2 numbers or names in the visible window
  PASS  HASHTAGS          3 tags: #freelance #contracts #agencyowner
  PASS  ONE ASK           one call to action: comment a keyword
  WARN  SEARCH TERMS      1/2 present. Missing: client contracts
```

It enforces the current hashtag cap, which is **five per post**, not thirty.
Instagram cut it on 18 December 2025.

### The humanizer

```bash
python3 humanize.py draft.txt --report      # clean it, show every change
python3 detect.py draft.txt                  # score it, five checks
python3 detect.py before.txt after.txt       # prove the delta
```

**What comes out automatically:**

- **Copy-paste cleanup.** Removes zero-width spaces, word joiners, soft
  hyphens, byte-order marks and invisible separators; normalizes unusual spaces.
  Preserves joiners, non-joiners, direction controls and emoji tag sequences.
  Invisible characters alone do not establish AI authorship.
- **Typography.** Em dash to comma, en dash to hyphen, curly quotes to
  straight, ellipsis to three dots. Use `--preserve-typography` with both
  `humanize.py` and `detect.py` when those characters belong to your voice.
- **The lexicon.** 154 stock words and phrases with plain-English replacements.
  The last block of it is Instagram-specific: "stop scrolling", "in today's
  video", "follow for more", "tag someone who needs this", "the algorithm
  loves", "run don't walk". It lives in
  [`slop.json`](skills/ig-human/slop.json) and it is meant to be edited.

**What gets flagged instead of fixed:** "It's not just X, it's Y", rule-of-three
triads, the video preamble, emoji bullet lists, three shouted words in a row,
hashtag walls, reflex follow bait, uniform sentence length. Changing the shape
of a sentence needs judgement, so those come back for a rewrite rather than
getting mangled by a regex.

Run against a caption written to be as bad as possible:

```
  BURSTINESS    ###################.....  78.4
  SPECIFICITY   #############...........  53.6    3.4 concrete markers per 100 words
  SLOP DENSITY  ........................   0.0    20 stock terms, 23.0 per 100 words
  FINGERPRINT   ################........  68.7    1 em dash
  VOICE         #################.......  70.0    9 structural tells
  ------------------------------------------------------------
  HUMAN SCORE   ########................  32.5   FLAGGED
```

After `humanize.py`, with the flagged structures still unrewritten:

```
  HUMAN SCORE   ###################.....  79.7   PASS    (+47.2)
```

### The swipe file

```bash
python3 swipe.py captured.tsv --out ~/.claude/instagram/swipe.md
```

That explicit path is for legacy single-account use. With named accounts, use
`--account HANDLE` instead so the result goes to that account's `swipe.md`.

Raw views are not evidence. A 2,000,000-follower account doing 400,000 views
had a quiet Tuesday. A 4,000-follower account doing 400,000 views found
something. `swipe.py` ranks on the multiple over each account's own median,
names the hook formula, and prints what separates the top third from the
bottom third.

```
SWIPE FILE  ·  4 reels  ·  4 accounts  ·  baseline: account median
==============================================================================
    60.0x  hook  57  #9  The Steal              @c                 180,000
           "steal this four line follow up it took me two years"
    37.5x  hook  86  #3  Nobody Tells You       @a                 412,000
           "nobody tells you that your first 30 reels are supposed to flop"
     1.3x  hook  13  -   unclassified           @b               1,200,000
           "in this video I am going to show you my morning routine"
```

## Carousel PNG export

`ig-carousel/render.py` turns supplied slide copy into `01.png`, `02.png`, …
at 1080x1350. It also writes a caption file, per-slide alt text/hashes in
`manifest.json`, and a review overview under `review/`. It never publishes.

This exporter alone needs optional Pillow plus a font file with Turkish/English
coverage; other text tools and the installer do not require Pillow. Install the
optional dependency into your chosen Python environment:

```bash
python3 -m pip install -r skills/ig-carousel/requirements.txt
python3 skills/ig-carousel/render.py skills/ig-carousel/example.tr.json --font /path/to/font.ttf --check
python3 skills/ig-carousel/render.py skills/ig-carousel/example.tr.json --font /path/to/font.ttf --out /path/to/new-export
```

Use `--font-bold /path/to/heading-font.ttf` for a separate heading font. Installed
copies include the renderer, dependency file and fictional sample inside
`ig-carousel/`. Fonts are user-supplied and are not bundled or downloaded.
Read the [export schema and workflow](skills/ig-carousel/references/rendering.md)
for account/language fields, colors, captions and alt text.

The layout uses measured text wrapping and fixed legible font sizes. Overflow,
missing font glyphs and low-contrast colors stop the export; copy is never
silently cut or shrunk. Existing output folders are refused. The supplied
layout supports Latin-script English/Turkish text; it is not a general
multilingual typesetting engine or an AI image generator. Inspect every draft
before posting and enter the supplied alt text in your publishing workflow.

## Local account analytics

`ig-audit/analyse.py` calculates rates and comparable peer baselines from a
user-mapped CSV. No login, network calls or additional Python packages are needed.
It requires an explicit account and primary metric:

```bash
python3 skills/ig-audit/analyse.py skills/ig-audit/example.synthetic.csv --account ornek_studyo --primary-metric shares_per_reach
```

The sample is fictional. Start real work with `skills/ig-audit/template.csv`;
native Instagram/Meta exports need mapping to this schema. Blank values stay
unknown; zero denominators give `null`. Rates include shares, saves and follows
per reach, non-follower reach and supported 3-second reel retention.

Comparisons separate format, organic/paid distribution and exact measurement age.
Relative views use other posts in the same cohort, with peer count disclosed.
Reports include coverage, input SHA-256 and interpretation limits. They describe
associations and do not diagnose causes or automatically attribute sales.

Default output is JSON. With an initialized account, `--save` writes a fresh
`accounts/HANDLE/audits/audit-UUID/report.json` under the account root; `--root`
selects a custom root. Prior snapshots and `results.md` are preserved. Explain
findings in English or Turkish through `/ig-audit`, then hand them to `/ig-plan`.
See the [CSV contract and interpretation guide](skills/ig-audit/references/csv-analysis.md).

## Reproducible evaluation

Run a local evaluation with explicit labels and dataset provenance:

```bash
python3 evaluation/evaluate.py evaluation/fixtures.json --out /tmp/hook-report.json
```

The runner reports AUROC separately for English and Turkish, pooled and within
account, plus formula coverage, abstentions and annotation agreement with their
sample counts. Tied scores receive half credit. Missing class pairs or missing
annotations produce `null` metrics instead of invented accuracy. Dataset and
source-file hashes plus the Python version make a run traceable.

The bundled 12 examples are synthetic development fixtures authored for this
repository. They test the pipeline and language routing; they are not observed
Instagram results, a held-out benchmark or independent validation. High fixture
scores do not establish real-world quality or performance. See the
[evaluation guide](evaluation/README.md), [dataset](evaluation/fixtures.json)
and [sample report](evaluation/example-report.json). CI publishes fresh fixture
reports for each supported Python version without a performance-score gate.

The upstream README reported a 74-hook YouTube Shorts corpus, AUROC 0.83 for
separating deliberately weak examples from real hooks, AUROC 0.56 for hits versus
misses, and formula coverage increasing from 8% to 49%. The original corpus and
measurement script are absent from this repository. Those are historical
upstream claims, not reproduced results for this fork's changed code or Turkish
support. The synthetic fixtures do not recover that missing evidence.

Use data you own or have permission to evaluate for a real study. Define the
label, observation window and sampling protocol, freeze holdout data before
tuning, and inspect account-level results. Text-only scores remain editorial
heuristics, not view predictions or proof that a change caused an outcome.

## The fine print, which is the honest part

**These skills do not post to Instagram.** There is a real Content Publishing
API for Professional accounts, and it needs a Meta developer app, a linked
Page, a long-lived token and app review, which is not a thing a skill can hand
you. Everything else people use to automate posting, commenting, following or
DMing is browser automation or a third-party tool, and both violate
[Instagram's Terms of Use](https://help.instagram.com/581066165581870) and get
accounts action-blocked. So every skill here ends the same way: a copy-ready
block, and you post it. That is not a limitation bolted on afterwards, it is
the design, and it is why the approval gate is real rather than a setting.

The one exception is keyword auto-replies in DMs, which Instagram supports
through its own tools and approved partners, and which only fire after somebody
comments first. `/ig-dm` says where that line is.

**`/ig-viral` reads, it does not scrape.** Ten accounts, a dozen reels each, at
human speed, with you driving your own browser. It never asks for your password
and never logs in as you. Automated collection at volume is the thing that gets
accounts restricted, and a crawler is not what this is.

**The five detection checks are local editorial heuristics.** They run on your
machine and do not call GPTZero, Originality, Copyleaks, Winston or Turnitin.
No supplied evaluation establishes agreement with those services or shows that
rewriting changes their verdicts. The scores are not evidence of human or AI
authorship and cannot promise undetectability.

**Unicode cleanup is conservative.** Joining and direction characters can
carry meaning in emoji and languages. They are preserved, as are unlisted
format characters. This cleanup is not watermark detection or removal.

**Short text gets limited coverage.** Checks that need more text report `N/A`
(JSON `null`) and are excluded from scoring. A PASS covers only the checks that
ran; empty text gets `INSUFFICIENT TEXT`. Do not lengthen copy to satisfy a score.

**Nothing here fabricates.** No invented metrics, clients or outcomes go under
your name. If a draft needs a number you have not given, it comes back with
`{{your number}}` in it and a flag, every time.

**Platform numbers go stale.** The hashtag cap moved from 30 to 5 in December
2025 while this repo was being written, and the linter had the old number in it
until the fact got checked. If something here contradicts what Instagram is
doing when you read it, Instagram is right.

## Files

```
skills/ig-reel/hooks.json          26 hook formulas: template, example, on-screen line,
                                   what it is for, how it gets ruined, and a match regex
skills/ig-reel/hookscore.py        the five-property hook panel
skills/ig-reel/beats.py            script to timed beat sheet
skills/ig-caption/caption.py       the truncation preview and the caption linter
skills/ig-account/account.py      account setup and explicit context paths
skills/ig-human/slop.json          the lexicon: 154 terms, 11 cleanup classes, 16 tells
skills/ig-human/humanize.py        the three cleaning passes
skills/ig-human/detect.py          the five-check panel
skills/ig-viral/swipe.py           outlier ranking and formula classification
skills/ig-profile/rubric.json      the 100-point profile score
scripts/install.py               complete-bundle install, update, backup and checks
skills/ig-carousel/render.py      optional PNG export with font/layout checks
templates/voice.md                 your voice profile. Fill this in first.
templates/strategy.md              confirmed goals, capacity and review criteria
evaluation/evaluate.py            local hook metrics with provenance and source hashes
evaluation/fixtures.json          synthetic English/Turkish pipeline examples
```

## Credit

This fork is maintained at [ebru-create/instagram-agent-skill](https://github.com/ebru-create/instagram-agent-skill).

Originally made by Jake Schincariol, [opusjake.ai](https://opusjake.ai).
Upstream: [Jakeschincariol/instagram-agent-skill](https://github.com/Jakeschincariol/instagram-agent-skill).

Sibling repo, same idea for a different platform:
[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill).

## Regression tests

Run the dependency-free suite from the repository root:

```bash
python3 -m unittest discover -s tests -v
```

Research counts accept `1,200`, `1.2K`, `1.2M` and `1.2B`. Ambiguous formats
such as `1,2M` are rejected with a row/field error. Median-based and
follower-based ratios are ranked in separate groups; follower ratios are
proxies, not account-median outliers. Missing baselines remain unranked.
`swipe.py --json` includes per-row `baseline_type` and per-cohort `groups`;
top/bottom summaries live inside each group, never across mixed baselines.

## License

MIT. Take it, change it, ship it.
