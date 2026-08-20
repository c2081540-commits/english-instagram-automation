"""Render the isolated ENG-000009 question-image design prototype."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from instagram_automation.renderer import (  # noqa: E402
    BACKGROUND,
    CANVAS_SIZE,
    LETTERS,
    RenderError,
    _draw_centered_text,
    _draw_choice,
    _fit_text,
)


CONTENT_ID = "ENG-000009"
JAPANESE_PROMPT = "「金曜日までに送る」ならどれ？"
EXPECTED_QUESTION = "I'll send you the file ___."
EXPECTED_CHOICES = ["by Friday", "until Friday", "since Friday", "for Friday"]
OUTPUT_PATH = REPO_ROOT / "artifacts" / "prototypes" / f"{CONTENT_ID}-question-v2.png"

ACCENT = "#2563EB"
ACCENT_BACKGROUND = "#EEF4FF"
ENGLISH_TEXT = "#111827"
DIVIDER = "#E5E7EB"


def _draw_colored_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    *,
    size: int,
    color: str,
) -> None:
    font, lines, spacing = _fit_text(draw, text, box, size, size, 1)
    if len(lines) != 1:
        raise RenderError(f"Prototype text must fit on one line: {text!r}")
    line = lines[0]
    bounds = draw.textbbox((0, 0), line, font=font)
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    x = box[0] + (box[2] - box[0] - width) / 2
    y = box[1] + (box[3] - box[1] - height) / 2 - bounds[1]
    draw.text((x, y), line, fill=color, font=font)


def main() -> None:
    master_path = REPO_ROOT / "data" / "master" / f"{CONTENT_ID}.json"
    if not master_path.is_file():
        raise FileNotFoundError(f"Required master not found: {master_path}")
    content = json.loads(master_path.read_text(encoding="utf-8"))

    if content.get("content_id") != CONTENT_ID:
        raise RenderError("Unexpected content_id")
    if content.get("question") != EXPECTED_QUESTION:
        raise RenderError("ENG-000009 question has changed; prototype aborted")
    if content.get("choices") != EXPECTED_CHOICES:
        raise RenderError("ENG-000009 choices have changed; prototype aborted")

    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(canvas)

    # The prompt remains legible in a profile-grid thumbnail without adding a meta label.
    draw.rounded_rectangle((64, 154, 1016, 392), radius=28, fill=ACCENT_BACKGROUND)
    draw.rounded_rectangle((64, 154, 78, 392), radius=7, fill=ACCENT)
    _draw_colored_centered_text(
        draw,
        JAPANESE_PROMPT,
        (104, 184, 982, 362),
        size=58,
        color=ACCENT,
    )

    _draw_colored_centered_text(
        draw,
        EXPECTED_QUESTION,
        (80, 440, 1000, 630),
        size=68,
        color=ENGLISH_TEXT,
    )
    draw.line((80, 670, 1000, 670), fill=DIVIDER, width=3)

    boxes = [
        (64, 722, 526, 962),
        (554, 722, 1016, 962),
        (64, 1006, 526, 1246),
        (554, 1006, 1016, 1246),
    ]
    for index, (choice, box) in enumerate(zip(EXPECTED_CHOICES, boxes)):
        _draw_choice(draw, box, LETTERS[index], choice)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT_PATH, format="PNG")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
