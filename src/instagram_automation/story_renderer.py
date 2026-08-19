from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .paths import (NORMAL_MASTER_DIR, STORY_CHARACTER_PATH, STORY_IMAGE_DIR,
                    THREADS_NORMAL_MASTER_DIR)
from .renderer import RenderError, _font, _wrap

CANVAS_SIZE = (1080, 1920)
BACKGROUND = "#F7F7F3"
BOARD = "#FFFFFF"
TEXT = "#151515"
BLUE = "#25639A"
BOARD_BORDER = "#D7E0E7"
MARKER_YELLOW = "#F6E58D"
CONTENT_ID = re.compile(r"^ENG-\d{6}$")
REQUIRED = {"content_id", "content_type", "theme", "threads_text",
            "story_headline", "story_body", "publish_at"}
CHARACTER_HEIGHT = 350
CHARACTER_RIGHT = 1000
CHARACTER_BOTTOM = 1780


def _read_direct(path: Path, expected_dir: Path, label: str) -> dict:
    resolved = path.resolve()
    if resolved.parent != expected_dir.resolve():
        raise ValueError(f"{label} must be directly under {expected_dir}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required {label} not found: {resolved}")
    try:
        value = json.loads(resolved.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RenderError(f"Invalid JSON in {resolved}: {exc}") from exc
    if not isinstance(value, dict):
        raise RenderError(f"{label} JSON root must be an object")
    return value


def validate_story_master(local: dict, threads: dict) -> None:
    missing = sorted(REQUIRED - local.keys())
    if missing:
        raise RenderError(f"missing story fields: {', '.join(missing)}")
    if local != threads:
        differing = sorted(field for field in REQUIRED if local.get(field) != threads.get(field))
        raise RenderError(f"Instagram/Threads normal master mismatch: {', '.join(differing) or 'unexpected fields'}")
    if not isinstance(local["content_id"], str) or not CONTENT_ID.fullmatch(local["content_id"]):
        raise RenderError("content_id must match ENG-000001")
    if local["content_type"] != "normal":
        raise RenderError("content_type must be normal")
    for field, limit in (("theme", 80), ("threads_text", 500),
                         ("story_headline", 60), ("story_body", 280)):
        value = local[field]
        if not isinstance(value, str) or not value.strip():
            raise RenderError(f"{field} must be a non-empty string")
        if len(value) > limit:
            raise RenderError(f"{field} exceeds {limit} characters")
    try:
        parsed = datetime.fromisoformat(local["publish_at"])
        if parsed.tzinfo is None:
            raise ValueError
    except (TypeError, ValueError):
        raise RenderError("publish_at must be an ISO 8601 datetime with timezone")


def load_story_master(master_path: Path) -> dict:
    local = _read_direct(master_path, NORMAL_MASTER_DIR, "Instagram normal master")
    threads = _read_direct(THREADS_NORMAL_MASTER_DIR / f"{local.get('content_id')}.json",
                           THREADS_NORMAL_MASTER_DIR, "Threads normal master")
    validate_story_master(local, threads)
    return local


def _fit_headline(draw: ImageDraw.ImageDraw, text: str) -> tuple[ImageFont.FreeTypeFont, list[str]]:
    for size in range(82, 55, -2):
        font = _font(size)
        lines = _wrap(draw, text, font, 840)
        if len(lines) <= 3 and len(lines) * (size + 18) <= 300:
            return font, lines
    raise RenderError("story_headline exceeds layout limits")


def _body_layout(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> tuple[list[tuple[str, bool]], int]:
    output: list[tuple[str, bool]] = []
    total = 0
    for raw in text.splitlines():
        if not raw.strip():
            output.append(("", False))
            total += 32
            continue
        checked = raw.strip().startswith("✓")
        content = raw.strip()[1:].strip() if checked else raw.strip()
        lines = _wrap(draw, content, font, 760 if checked else 820)
        for index, line in enumerate(lines):
            output.append((line, checked and index == 0))
            total += font.size + 18
    return output, total


def _fit_body(draw: ImageDraw.ImageDraw, text: str) -> tuple[ImageFont.FreeTypeFont, list[tuple[str, bool]], int]:
    for size in range(52, 37, -2):
        font = _font(size)
        lines, total = _body_layout(draw, text, font)
        if len([line for line, _ in lines if line]) <= 12 and total <= 820:
            return font, lines, total
    raise RenderError("story_body exceeds layout limits")


def character_placement(source_size: tuple[int, int]) -> tuple[int, int, int, int]:
    width, height = source_size
    if width <= 0 or height <= 0:
        raise RenderError("character image has invalid dimensions")
    display_height = CHARACTER_HEIGHT
    display_width = round(width * display_height / height)
    if display_width > 400:
        display_width = 400
        display_height = round(height * display_width / width)
    left = CHARACTER_RIGHT - display_width
    top = CHARACTER_BOTTOM - display_height
    return left, top, display_width, display_height


def load_character(path: Path = STORY_CHARACTER_PATH) -> tuple[Image.Image, tuple[int, int, int, int]] | None:
    if not path.exists():
        return None
    if not path.is_file():
        raise RenderError(f"character path is not a file: {path}")
    try:
        with Image.open(path) as source:
            placement = character_placement(source.size)
            resized = source.convert("RGB").resize((placement[2], placement[3]), Image.Resampling.LANCZOS)
    except OSError as exc:
        raise RenderError(f"character image is unreadable: {path}") from exc
    return resized, placement


def render_story(master_path: Path) -> Path:
    content = load_story_master(master_path)
    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((48, 56, 1032, 1840), radius=28, fill=BOARD, outline=BOARD_BORDER, width=4)

    small_font = _font(34)
    draw.text((92, 108), "オトナの英語やり直し", font=small_font, fill=BLUE)
    draw.line((92, 164, 310, 164), fill=BLUE, width=5)

    headline_font, headline_lines = _fit_headline(draw, content["story_headline"])
    headline_top = 230
    line_height = headline_font.size + 18
    total_headline = len(headline_lines) * line_height - 18
    y = headline_top + (280 - total_headline) / 2
    for line in headline_lines:
        width = draw.textbbox((0, 0), line, font=headline_font)[2]
        draw.text(((1080 - width) / 2, y), line, font=headline_font, fill=TEXT)
        y += line_height
    draw.rounded_rectangle((170, 512, 910, 536), radius=12, fill=MARKER_YELLOW)

    body_font, body_lines, body_height = _fit_body(draw, content["story_body"])
    y = 660 + (760 - body_height) / 2
    for line, checked in body_lines:
        if not line:
            y += 32
            continue
        if checked:
            draw.text((130, y), "✓", font=body_font, fill=BLUE)
            draw.text((195, y), line, font=body_font, fill=TEXT)
        else:
            draw.text((130, y), line, font=body_font, fill=TEXT)
        y += body_font.size + 18

    character = load_character()
    if character is not None:
        character_image, placement = character
        canvas.paste(character_image, (placement[0], placement[1]))

    draw.text((92, 1742), "@eigo_yarinaoshi", font=_font(30), fill=BLUE)

    STORY_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output = STORY_IMAGE_DIR / f"{content['content_id']}-story.png"
    canvas.save(output, format="PNG", optimize=True)
    return output
