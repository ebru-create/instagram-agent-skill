#!/usr/bin/env python3
"""Render approved English/Turkish slide copy into numbered 1080x1350 PNGs."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import tempfile
import unicodedata


WIDTH, HEIGHT, MARGIN = 1080, 1350, 120
DEFAULT_THEME = {"background": "#F4F0E8", "text": "#16231D", "accent": "#2C6E49"}


def pillow():
    try:
        from PIL import Image, ImageDraw, ImageFont, features
        import PIL
    except ImportError as exc:
        raise ValueError("PNG export needs optional Pillow: install with python3 -m pip install -r "
                         + str(Path(__file__).with_name("requirements.txt"))) from exc
    return Image, ImageDraw, ImageFont, features, PIL.__version__


def text(value, name, limit, *, multiline=False, optional=False, rendered=True):
    if not isinstance(value, str) or (not optional and not value.strip()) or len(value) > limit:
        raise ValueError(f"{name}: provide {'optional ' if optional else ''}text up to {limit} characters")
    value = unicodedata.normalize("NFC", value.strip())
    for char in value:
        category = unicodedata.category(char)
        forbidden = category.startswith("C") if rendered else category == "Cc"
        if (forbidden and not (multiline and char == "\n")) or (char == "\n" and not multiline):
            raise ValueError(f"{name}: unsupported control/format character U+{ord(char):04X}")
        if rendered and category.startswith("L") and "LATIN" not in unicodedata.name(char, ""):
            raise ValueError(f"{name}: this layout supports Latin-script English/Turkish text")
    return value


def validate(job):
    if not isinstance(job, dict) or type(job.get("schema_version")) is not int or job["schema_version"] != 1:
        raise ValueError("expected schema_version 1")
    if job.get("language") not in ("en", "tr"):
        raise ValueError("language must be en or tr")
    handle = job.get("account", "")
    if not isinstance(handle, str):
        raise ValueError("account must be the publishing handle")
    handle = handle.strip().removeprefix("@").lower()
    if not re.fullmatch(r"[a-z0-9_.]{1,30}", handle) or handle in (".", ".."):
        raise ValueError("account must be the publishing handle, not a path")
    theme = dict(DEFAULT_THEME)
    if not isinstance(job.get("theme", {}), dict):
        raise ValueError("theme must be an object")
    for key, color in job.get("theme", {}).items():
        if key not in theme or not isinstance(color, str) or not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("theme supports background, text and accent as #RRGGBB colors")
        theme[key] = color
    for key in ("text", "accent"):
        if contrast(theme[key], theme["background"]) < 4.5:
            raise ValueError(f"theme.{key}: contrast against background must be at least 4.5")
    slides = job.get("slides")
    if not isinstance(slides, list) or not 2 <= len(slides) <= 20:
        raise ValueError("this exporter supports 2 to 20 slides")
    normalized = []
    for number, slide in enumerate(slides, 1):
        if not isinstance(slide, dict):
            raise ValueError(f"slide {number}: expected an object")
        normalized.append({"title": text(slide.get("title"), f"slide {number} title", 200),
                           "body": text(slide.get("body", ""), f"slide {number} body", 1800, multiline=True, optional=True),
                           "label": text(slide.get("label", ""), f"slide {number} label", 50, optional=True),
                           "alt_text": text(slide.get("alt_text"), f"slide {number} alt_text", 1500, multiline=True, rendered=False)})
    return {"account": handle, "language": job["language"], "theme": theme, "slides": normalized,
            "caption": text(job.get("caption", ""), "caption", 2200, multiline=True, optional=True, rendered=False)}


def contrast(first, second):
    def luminance(color):
        values = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
        return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
    a, b = sorted((luminance(first), luminance(second)))
    return (b + .05) / (a + .05)


def glyphs_available(value, font, field):
    def signature(char):
        mask = font.getmask(char)
        return mask.size, bytes(mask)
    missing = signature("\U0010ffff")
    for char in set(value):
        if not char.isspace() and signature(char) == missing:
            raise ValueError(f"{field}: font has no glyph for {char!r}; choose a suitable font or edit the copy")


def wrap(value, font, width):
    lines = []
    for paragraph in value.split("\n"):
        current = ""
        if not paragraph.strip():
            lines.append("")
            continue
        for word in paragraph.split():
            if font.getlength(word) > width:
                raise ValueError("an unbroken word is too wide; shorten it or split the slide")
            candidate = current + " " + word if current else word
            if current and font.getlength(candidate) > width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
    return lines


def line_height(font):
    return math.ceil(sum(font.getmetrics()) * 1.12)


def prepare(job, regular_path, bold_path):
    Image, ImageDraw, ImageFont, features, version = pillow()
    regular_path = Path(regular_path).expanduser().resolve()
    bold_path = Path(bold_path or regular_path).expanduser().resolve()
    if not regular_path.is_file() or not bold_path.is_file():
        raise ValueError("provide existing TrueType/OpenType files with --font and optionally --font-bold")
    body = ImageFont.truetype(str(regular_path), 44)
    footer = ImageFont.truetype(str(regular_path), 32)
    title = ImageFont.truetype(str(bold_path), 72)
    cover = ImageFont.truetype(str(bold_path), 96)
    plans = []
    for number, slide in enumerate(job["slides"], 1):
        heading_font = cover if number == 1 else title
        glyphs_available(slide["title"], heading_font, f"slide {number} title")
        glyphs_available(slide["body"], body, f"slide {number} body")
        glyphs_available(slide["label"] + "@" + job["account"], footer, f"slide {number} footer/label")
        headings = wrap(slide["title"], heading_font, WIDTH - 2 * MARGIN)
        body_lines = wrap(slide["body"], body, WIDTH - 2 * MARGIN) if slide["body"] else []
        body_y = 260 + len(headings) * line_height(heading_font) + 48
        if len(headings) > 4 or body_y + len(body_lines) * line_height(body) > 1100:
            raise ValueError(f"slide {number}: text overflows the layout; shorten or split it (fonts are not shrunk)")
        if footer.getlength(slide["label"]) > WIDTH - 2 * MARGIN:
            raise ValueError(f"slide {number}: label is too wide")
        if footer.getlength("@" + job["account"]) > 620:
            raise ValueError("account handle is too wide for the footer with this font")
        plans.append({"heading_font": heading_font, "headings": headings,
                      "body_lines": body_lines, "body_y": body_y})
    provenance = {"pillow": version, "freetype": features.version("freetype2"),
                  "font_sha256": hashlib.sha256(regular_path.read_bytes()).hexdigest(),
                  "bold_font_sha256": hashlib.sha256(bold_path.read_bytes()).hexdigest(),
                  "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return plans, body, footer, provenance


def export(job, regular_path, bold_path=None, output=None, source_bytes=None):
    job = validate(job)
    if output is not None:
        output = Path(output).expanduser().absolute()
        if output.exists() or output.is_symlink():
            raise ValueError("choose a new output directory; existing exports are never overwritten")
    plans, body, footer, provenance = prepare(job, regular_path, bold_path)
    result = {"status": "checked" if output is None else "exported", "account": job["account"],
              "language": job["language"], "width": WIDTH, "height": HEIGHT,
              "source_sha256": hashlib.sha256(source_bytes if source_bytes is not None else
                                              json.dumps(job, ensure_ascii=False, sort_keys=True).encode()).hexdigest(),
              "source_encoding": "raw-json" if source_bytes is not None else "canonical-normalized-json",
              **provenance, "slides": []}
    if output is None:
        result["slide_count"] = len(plans)
        return result
    Image, ImageDraw, _, _, _ = pillow()
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".carousel-stage-", dir=output.parent))
    thumbnails = []
    try:
        for number, (slide, plan) in enumerate(zip(job["slides"], plans), 1):
            canvas = Image.new("RGB", (WIDTH, HEIGHT), job["theme"]["background"])
            draw = ImageDraw.Draw(canvas)
            draw.rectangle((MARGIN, 120, MARGIN + 96, 130), fill=job["theme"]["accent"])
            draw.text((MARGIN, 172), slide["label"], font=footer, fill=job["theme"]["accent"], anchor="lt")
            for i, line in enumerate(plan["headings"]):
                draw.text((MARGIN, 260 + i * line_height(plan["heading_font"])), line,
                          font=plan["heading_font"], fill=job["theme"]["text"], anchor="lt")
            for i, line in enumerate(plan["body_lines"]):
                draw.text((MARGIN, plan["body_y"] + i * line_height(body)), line,
                          font=body, fill=job["theme"]["text"], anchor="lt")
            draw.line((MARGIN, 1168, WIDTH - MARGIN, 1168), fill=job["theme"]["accent"], width=2)
            draw.text((MARGIN, 1200), "@" + job["account"], font=footer, fill=job["theme"]["text"], anchor="lt")
            page = f"{number:02d} / {len(plans):02d}"
            draw.text((WIDTH - MARGIN - footer.getlength(page), 1200), page,
                      font=footer, fill=job["theme"]["text"], anchor="lt")
            filename = f"{number:02d}.png"
            canvas.save(stage / filename, format="PNG")
            thumbnails.append(canvas.resize((270, 338), Image.Resampling.LANCZOS))
            result["slides"].append({"file": filename, "alt_text": slide["alt_text"],
                                     "sha256": hashlib.sha256((stage / filename).read_bytes()).hexdigest()})
        overview = Image.new("RGB", (580, math.ceil(len(thumbnails) / 2) * 358 + 20), "#DFDFDF")
        for i, thumbnail in enumerate(thumbnails):
            overview.paste(thumbnail, (20 + (i % 2) * 290, 20 + (i // 2) * 358))
        (stage / "review").mkdir()
        overview.save(stage / "review/overview.png")
        (stage / "caption.txt").write_text(job["caption"] + "\n", encoding="utf-8")
        (stage / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # A new destination avoids mixing old/new slide counts. Refuse an
        # output created by another run while this one was rendering.
        if output.exists() or output.is_symlink():
            raise ValueError("output directory appeared during rendering; choose a new destination")
        stage.rename(output)
        return result
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="approved slide copy as JSON")
    parser.add_argument("--font", required=True, help="regular font file with Turkish glyph coverage")
    parser.add_argument("--font-bold", help="optional heading font file; defaults to regular")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate layout without creating files")
    mode.add_argument("--out", type=Path, help="new directory for numbered PNGs and review files")
    args = parser.parse_args()
    try:
        raw = args.input.read_bytes()
        result = export(json.loads(raw), args.font, args.font_bold, args.out, raw)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
