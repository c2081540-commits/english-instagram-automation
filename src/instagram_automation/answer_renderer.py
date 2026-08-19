import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .paths import IMAGE_DIR, require_file
from .renderer import BACKGROUND, CANVAS_SIZE, RenderError, TEXT, _font, _wrap
from .validation import validate

HEADINGS = {
    "answer": "ANSWER",
    "point": "POINT",
    "meaning": "MEANING",
    "example": "EXAMPLE",
    "difference": "DIFFERENCE",
    "also_natural": "ALSO NATURAL",
    "tip": "TIP",
}

STYLES = {
    "answer": {"accent": "#26734D", "background": "#FFFFFF", "border": "#C8E4D4"},
    "point": {"accent": "#2B67A0", "background": "#FFFFFF", "border": "#CADCED"},
    "meaning": {"accent": "#2B67A0", "background": "#FFFFFF", "border": "#CADCED"},
    "example": {"accent": "#5E6268", "background": "#FFFFFF", "border": "#D9D9D6"},
    "difference": {"accent": "#B96822", "background": "#FFFFFF", "border": "#EED2B8"},
    "also_natural": {"accent": "#7653A6", "background": "#FFFFFF", "border": "#DED2EC"},
    "tip": {"accent": "#5E6268", "background": "#FFFFFF", "border": "#D9D9D6"},
}


def _required_text(content: dict, field: str) -> str:
    value = content.get(field)
    if not isinstance(value, str) or not value.strip():
        raise RenderError(f"{field} must be a non-empty string for the answer template")
    return value.strip()


def _example(content: dict) -> str:
    examples = content.get("examples")
    translations = content.get("example_translations")
    if not isinstance(examples, list) or not examples or not isinstance(examples[0], str) or not examples[0].strip():
        raise RenderError("examples must contain an English example for the answer template")
    if not isinstance(translations, list) or not translations or not isinstance(translations[0], str) or not translations[0].strip():
        raise RenderError("example_translations must contain a Japanese translation")
    return f"{examples[0].strip()}\n{translations[0].strip()}"


def _sections(content: dict) -> list[tuple[str, str]]:
    category = content.get("category")
    if category == "grammar":
        sections = [("point", _required_text(content, "explanation")),
                    ("example", _example(content))]
    elif category == "vocabulary":
        sections = [("meaning", _required_text(content, "explanation")),
                    ("example", _example(content))]
        difference = content.get("key_difference")
        if isinstance(difference, str) and difference.strip():
            sections.append(("difference", difference.strip()))
    elif category == "situation":
        sections = [("also_natural", _required_text(content, "also_natural")),
                    ("point", _required_text(content, "explanation"))]
    else:
        raise RenderError("Answer renderer category must be grammar, vocabulary, or situation")

    tip = content.get("tip")
    if isinstance(tip, str) and tip.strip():
        sections.append(("tip", tip.strip()))
    return sections


def _wrap_paragraphs(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont,
                     width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.splitlines():
        if not paragraph.strip():
            raise RenderError("Blank lines are not supported in answer sections")
        lines.extend(_wrap(draw, paragraph.strip(), font, width))
    return lines


def _fit_section_text(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int]) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    width, height = box[2] - box[0], box[3] - box[1]
    for size in range(48, 31, -2):
        font = _font(size)
        lines = _wrap_paragraphs(draw, text, font, width)
        spacing = max(10, size // 3)
        if len(lines) <= 5 and len(lines) * (size + spacing) - spacing <= height:
            return font, lines, spacing
    raise RenderError(f"Answer section exceeds layout limits: {text!r}")


def _draw_icon(draw: ImageDraw.ImageDraw, position: tuple[int, int], kind: str, size: int, color: str) -> None:
    x, y = position
    stroke = max(3, size // 10)
    if kind == "answer":
        draw.rounded_rectangle((x, y, x + size, y + size), radius=size // 6, fill=color)
        draw.line((x + size * .22, y + size * .54, x + size * .42, y + size * .75,
                   x + size * .80, y + size * .25), fill="#FFFFFF", width=stroke, joint="curve")
    elif kind in {"point", "meaning"}:
        draw.ellipse((x + size * .23, y + size * .05, x + size * .77, y + size * .62), outline=color, width=stroke)
        draw.line((x + size * .38, y + size * .65, x + size * .62, y + size * .65), fill=color, width=stroke)
        draw.line((x + size * .41, y + size * .78, x + size * .59, y + size * .78), fill=color, width=stroke)
    elif kind == "example":
        draw.rounded_rectangle((x + size * .12, y + size * .04, x + size * .82, y + size * .92), radius=3, outline=color, width=stroke)
        for offset in (.32, .50, .68):
            draw.line((x + size * .26, y + size * offset, x + size * .68, y + size * offset), fill=color, width=stroke)
    elif kind == "difference":
        draw.ellipse((x + size * .08, y + size * .05, x + size * .65, y + size * .62), outline=color, width=stroke)
        draw.line((x + size * .58, y + size * .56, x + size * .91, y + size * .89), fill=color, width=stroke)
    elif kind == "also_natural":
        draw.rounded_rectangle((x + size * .04, y + size * .08, x + size * .92, y + size * .72), radius=size // 4, outline=color, width=stroke)
        draw.polygon((x + size * .25, y + size * .70, x + size * .18, y + size * .94, x + size * .45, y + size * .72), fill=color)
        for offset in (.32, .50, .68):
            draw.ellipse((x + size * offset - 2, y + size * .38 - 2, x + size * offset + 2, y + size * .38 + 2), fill=color)
    else:
        draw.polygon((x + size * .22, y + size * .05, x + size * .78, y + size * .05,
                      x + size * .78, y + size * .92, x + size * .50, y + size * .72,
                      x + size * .22, y + size * .92), fill=color)


def _draw_heading(draw: ImageDraw.ImageDraw, position: tuple[int, int], kind: str, size: int) -> None:
    style = STYLES[kind]
    _draw_icon(draw, position, kind, size, style["accent"])
    draw.text((position[0] + size + 14, position[1]), HEADINGS[kind], font=_font(size), fill=style["accent"])


def _draw_section(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], kind: str, text: str) -> None:
    style = STYLES[kind]
    draw.rounded_rectangle(box, radius=24, fill=style["background"], outline=style["border"], width=3)
    _draw_heading(draw, (box[0] + 34, box[1] + 24), kind, 34)
    text_box = (box[0] + 34, box[1] + 82, box[2] - 34, box[3] - 28)
    font, lines, spacing = _fit_section_text(draw, text, text_box)
    total = len(lines) * (font.size + spacing) - spacing
    y = text_box[1] + (text_box[3] - text_box[1] - total) / 2
    for line in lines:
        draw.text((text_box[0], y), line, font=font, fill=TEXT)
        y += font.size + spacing


def render_answer(master_path: Path) -> Path:
    source_json = require_file(master_path)
    try:
        content = json.loads(source_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RenderError(f"Invalid JSON in {source_json}: {exc}") from exc
    if not isinstance(content, dict):
        raise RenderError("Master JSON root must be an object")
    validate(content)
    sections = _sections(content)
    if len(sections) > 3:
        raise RenderError("Answer template supports at most three detail sections")

    canvas = Image.new("RGB", CANVAS_SIZE, BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    _draw_heading(draw, (64, 54), "answer", 40)

    answer_box = (64, 118, 1016, 326)
    answer_style = STYLES["answer"]
    draw.rounded_rectangle(answer_box, radius=28, fill=answer_style["background"], outline=answer_style["border"], width=3)
    answer = _required_text(content, "best_answer")
    from .renderer import _draw_centered_text
    _draw_centered_text(draw, answer, (96, 144, 984, 300), 88, 54, 2)

    top, bottom, gap = 370, 1286, 24
    section_height = (bottom - top - gap * (len(sections) - 1)) // len(sections)
    for index, (kind, text) in enumerate(sections):
        y1 = top + index * (section_height + gap)
        y2 = bottom if index == len(sections) - 1 else y1 + section_height
        _draw_section(draw, (64, y1, 1016, y2), kind, text)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output = IMAGE_DIR / f"{content['content_id']}-answer.png"
    canvas.save(output, format="PNG", optimize=True)
    return output
