# PNG export workflow

Use the local `render.py` beside this skill. The renderer generates a simple
text-first layout from approved or requested draft copy; it does not create
claims, brand fonts, illustrations or accessibility descriptions for you.

## Environment

Pillow is optional for the rest of the bundle and required only here. Use an
environment that already has it, or install from this folder's `requirements.txt`
when authorized. The installer copies that file but does not install packages.
The renderer reads explicit TrueType/OpenType font files supplied by the user.
Regular text and headings can use the same font, or separate files. No font is
bundled or downloaded. Pillow's [font API](https://pillow.readthedocs.io/en/stable/reference/ImageFont.html)
and [drawing API](https://pillow.readthedocs.io/en/stable/reference/ImageDraw.html)
provide the measurements and glyph rendering used here.

From the skill folder:

```bash
python3 render.py example.tr.json --font /path/to/regular.ttf --font-bold /path/to/bold.ttf --check
python3 render.py example.tr.json --font /path/to/regular.ttf --font-bold /path/to/bold.ttf --out /path/to/new-draft
```

Use absolute installed paths when running elsewhere. Do not assume the example
font path exists on a particular machine. Missing dependencies/fonts get an
actionable error; do not silently fall back to a font without Turkish glyphs.

## JSON input

`example.tr.json` is a fictional Turkish example. Replace its account, copy,
colors, caption and descriptions with the selected account's actual draft.

| field | contract |
| --- | --- |
| schema_version | integer `1` |
| language | `en` or `tr`; selected content language, not automatic detection |
| account | publishing handle, optionally starting with `@`; no path |
| theme | optional `background`, `text`, `accent` colors as `#RRGGBB` |
| caption | optional text, up to 2,200 characters; lint with `ig-caption` separately |
| slides | 2 to 20 objects, preserving intended sequence |
| slide.title | non-empty headline, at most 200 characters; must also fit visually |
| slide.body | optional body, at most 1,800 characters; newlines preserve paragraph breaks |
| slide.label | optional short section/brand label, at most 50 characters |
| slide.alt_text | required descriptive text for this slide, at most 1,500 characters |

Length caps do not guarantee visual fit. Labels, titles and body use fixed font
sizes: 32px labels/footer, 72px headings (96px on the cover), and 44px body.
The canvas is 1080x1350 with a 120px inset and reserved footer. Paragraphs wrap
by measured width; unbroken words wider than the available area are rejected.
Overflow is an error rather than a reason to shrink type, clip copy or remove
meaning. Title/body/label support Latin-script English/Turkish, not general
complex-script shaping. Unsupported format controls and missing glyphs are
rejected. Caption and alt-text metadata preserve emoji/other scripts but are
not burned into the images.

Foreground and accent text need a contrast ratio of at least 4.5 against the
background. This is a renderer guard, not a complete accessibility assessment.
Alt text must describe the actual card and relevant information; a non-empty
field alone does not prove the description is useful.

## Output and review

`--check` validates schema, font availability, glyphs, wrapping, contrast and
vertical fit without creating files. A real export uses a new output directory;
existing directories are refused so prior slides and account files are preserved.
Input/layout errors are detected before output staging. Save failures clean up
the temporary staging directory. Completed exports contain:

- `01.png` … `NN.png`: RGB slide images in upload order.
- `caption.txt`: separate copy to review and paste.
- `manifest.json`: publishing account/language, per-slide alt text and PNG hashes,
  source/font/renderer hashes, Pillow and FreeType versions.
- `review/overview.png`: a contact sheet for checking sequence; full-size PNGs
  still need inspection for type, diacritics, line breaks and visual balance.

The CLI hashes the original input bytes. Direct Python calls without raw bytes
hash the normalized job and label it `canonical-normalized-json`. Font/Pillow/
FreeType differences can change raster output, so compare hashes only within a
recorded environment. No output is posted automatically. The user must enter
the stored alt text through their publishing workflow; it is not an automatic
Instagram accessibility field embedded in PNG.
