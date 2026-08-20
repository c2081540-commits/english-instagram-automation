import json
import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

from .paths import FONT_PATH, IMAGE_DIR, REPO_ROOT, SOURCE_IMAGE_DIR, require_file
from .validation import validate

CANVAS_SIZE = (1080, 1350)
BACKGROUND = "#FFFFFF"
TEXT = "#111111"
BORDER = "#D6D6D6"
LABEL_FILL = "#111111"
LABEL_TEXT = "#FFFFFF"
LETTERS = "ABCD"
TEXT_TEMPLATE_ACCENT = "#2563EB"
TEXT_TEMPLATE_ACCENT_BACKGROUND = "#EEF4FF"
TEXT_TEMPLATE_ENGLISH = "#111827"
TEXT_TEMPLATE_DIVIDER = "#E5E7EB"


class RenderError(ValueError):
    pass


def _font(size: int) -> ImageFont.FreeTypeFont:
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f"Required font not found: {FONT_PATH}")
    font = ImageFont.truetype(str(FONT_PATH), size=size)
    font.set_variation_by_axes([500])
    return font


def _tokens(text: str) -> list[str]:
    if re.search(r"\s", text):
        return re.findall(r"\S+\s*", text)
    return list(text)


def _wrap(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for token in _tokens(text.strip()):
        candidate = current + token
        if draw.textbbox((0, 0), candidate.rstrip(), font=font)[2] <= width:
            current = candidate
        elif current:
            lines.append(current.rstrip())
            current = token.lstrip()
        else:
            raise RenderError("A word or character sequence exceeds the available width")
    if current:
        lines.append(current.rstrip())
    return lines


def _fit_text(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int], max_size: int,
              min_size: int, max_lines: int) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    width, height = box[2] - box[0], box[3] - box[1]
    for size in range(max_size, min_size - 1, -2):
        font = _font(size)
        try:
            lines = _wrap(draw, text, font, width)
        except RenderError:
            continue
        spacing = max(10, size // 4)
        line_height = size + spacing
        if len(lines) <= max_lines and len(lines) * line_height - spacing <= height:
            return font, lines, spacing
    raise RenderError(f"Text exceeds layout limits: {text!r}")


def _draw_centered_text(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int],
                        max_size: int, min_size: int, max_lines: int) -> None:
    font, lines, spacing = _fit_text(draw, text, box, max_size, min_size, max_lines)
    heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total = sum(heights) + spacing * (len(lines) - 1)
    y = box[1] + (box[3] - box[1] - total) / 2
    for line, height in zip(lines, heights):
        line_width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text((box[0] + (box[2] - box[0] - line_width) / 2, y), line, fill=TEXT, font=font)
        y += height + spacing


def _draw_fixed_centered_text(draw: ImageDraw.ImageDraw, text: str,
                              box: tuple[int, int, int, int], size: int, color: str,
                              max_lines: int = 1) -> None:
    font, lines, spacing = _fit_text(draw, text, box, size, size, max_lines)
    heights = [draw.textbbox((0, 0), line, font=font)[3] for line in lines]
    total = sum(heights) + spacing * (len(lines) - 1)
    y = box[1] + (box[3] - box[1] - total) / 2
    for line, height in zip(lines, heights):
        width = draw.textbbox((0, 0), line, font=font)[2]
        draw.text((box[0] + (box[2] - box[0] - width) / 2, y), line, fill=color, font=font)
        y += height + spacing


def _draw_choice(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], letter: str, text: str) -> None:
    draw.rounded_rectangle(box, radius=24, fill=BACKGROUND, outline=BORDER, width=3)
    diameter = 72
    cx = box[0] + 62
    cy = (box[1] + box[3]) // 2
    draw.ellipse((cx - diameter // 2, cy - diameter // 2, cx + diameter // 2, cy + diameter // 2), fill=LABEL_FILL)
    label_font = _font(43)
    label_box = draw.textbbox((0, 0), letter, font=label_font)
    draw.text((cx - (label_box[2] - label_box[0]) / 2, cy - (label_box[3] - label_box[1]) / 2 - label_box[1]),
              letter, font=label_font, fill=LABEL_TEXT)
    text_box = (box[0] + 116, box[1] + 20, box[2] - 24, box[3] - 20)
    _draw_centered_text(draw, text, text_box, max_size=48, min_size=32, max_lines=2)


def _source_image(content: dict) -> Path:
    value = content.get("problem_image_path")
    if not isinstance(value, str) or not value.strip():
        raise RenderError("problem_image_path is required when visual_required is true")
    source = (REPO_ROOT / value).resolve()
    if source.parent != SOURCE_IMAGE_DIR.resolve():
        raise RenderError(f"Problem image must be directly under {SOURCE_IMAGE_DIR}")
    if not source.is_file():
        raise FileNotFoundError(f"Required problem image not found: {source}")
    return source


def render_question(master_path: Path) -> Path:
    source_json = require_file(master_path)
    try:
        content = json.loads(source_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RenderError(f"Invalid JSON in {source_json}: {exc}") from exc
    if not isinstance(content, dict):
        raise RenderError("Master JSON root must be an object")
    validate(content)
    choices = content["choices"]
    if len(choices) not in {2, 4}:
        raise RenderError("Question renderer supports exactly 2 or 4 choices")

    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    has_image = content["visual_required"] is True

    if has_image:
        _draw_centered_text(draw, content["question"], (64, 50, 1016, 240), 82, 48, 2)
        with Image.open(_source_image(content)) as raw:
            image_size = (952, 600) if len(choices) == 4 else (952, 570)
            fitted = ImageOps.fit(raw.convert("RGB"), image_size, method=Image.Resampling.LANCZOS)
        mask = Image.new("L", fitted.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, fitted.width, fitted.height), radius=28, fill=255)
        canvas.paste(fitted, (64, 270), mask)
        if len(choices) == 4:
            boxes = [(64, 910, 526, 1080), (554, 910, 1016, 1080),
                     (64, 1110, 526, 1280), (554, 1110, 1016, 1280)]
        else:
            boxes = [(80, 880, 1000, 1055), (80, 1085, 1000, 1260)]
    elif len(choices) == 4:
        draw.rounded_rectangle((64, 154, 1016, 392), radius=28,
                               fill=TEXT_TEMPLATE_ACCENT_BACKGROUND)
        draw.rounded_rectangle((64, 154, 78, 392), radius=7, fill=TEXT_TEMPLATE_ACCENT)
        is_meta = content["question_role"] == "meta_instruction"
        guide_box = (88, 184, 1008, 362) if is_meta else (104, 184, 982, 362)
        guide_size = 54 if is_meta else 58
        _draw_fixed_centered_text(draw, content["question_guide_ja"],
                                  guide_box, guide_size, TEXT_TEMPLATE_ACCENT)
        if not is_meta:
            _draw_fixed_centered_text(draw, content["question"],
                                      (80, 440, 1000, 630), 68,
                                      TEXT_TEMPLATE_ENGLISH, max_lines=2)
        draw.line((80, 670, 1000, 670), fill=TEXT_TEMPLATE_DIVIDER, width=3)
        boxes = [(64, 722, 526, 962), (554, 722, 1016, 962),
                 (64, 1006, 526, 1246), (554, 1006, 1016, 1246)]
    else:
        draw.rounded_rectangle((64, 154, 1016, 392), radius=28,
                               fill=TEXT_TEMPLATE_ACCENT_BACKGROUND)
        draw.rounded_rectangle((64, 154, 78, 392), radius=7, fill=TEXT_TEMPLATE_ACCENT)
        if content["question_role"] == "meta_instruction":
            raise RenderError("meta_instruction is not supported for two-choice quizzes")
        _draw_fixed_centered_text(draw, content["question_guide_ja"],
                                  (104, 184, 982, 362), 58, TEXT_TEMPLATE_ACCENT)
        _draw_fixed_centered_text(draw, content["question"],
                                  (80, 440, 1000, 630), 68, TEXT_TEMPLATE_ENGLISH, max_lines=2)
        draw.line((80, 670, 1000, 670), fill=TEXT_TEMPLATE_DIVIDER, width=3)
        boxes = [(80, 722, 1000, 950), (80, 1010, 1000, 1238)]

    for index, (choice, box) in enumerate(zip(choices, boxes)):
        _draw_choice(draw, box, LETTERS[index], choice)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output = IMAGE_DIR / f"{content['content_id']}-question.png"
    canvas.save(output, format="PNG", optimize=True)
    return output
