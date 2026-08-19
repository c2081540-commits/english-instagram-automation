import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .paths import EMOJI_FONT_PATH, IMAGE_DIR, require_file
from .renderer import BACKGROUND, BORDER, CANVAS_SIZE, RenderError, TEXT, _font, _wrap
from .validation import validate

HEADINGS = {
    "answer": ("✅", "ANSWER"),
    "point": ("💡", "POINT"),
    "meaning": ("💡", "MEANING"),
    "example": ("📝", "EXAMPLE"),
    "difference": ("🔍", "DIFFERENCE"),
    "also_natural": ("💬", "ALSO NATURAL"),
    "tip": ("🔖", "TIP"),
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


def _sections(content: dict) -> list[tuple[tuple[str, str], str]]:
    category = content.get("category")
    if category == "grammar":
        sections = [(HEADINGS["point"], _required_text(content, "explanation")),
                    (HEADINGS["example"], _example(content))]
    elif category == "vocabulary":
        sections = [(HEADINGS["meaning"], _required_text(content, "explanation")),
                    (HEADINGS["example"], _example(content))]
        difference = content.get("key_difference")
        if isinstance(difference, str) and difference.strip():
            sections.append((HEADINGS["difference"], difference.strip()))
    elif category == "situation":
        sections = [(HEADINGS["also_natural"], _required_text(content, "also_natural")),
                    (HEADINGS["point"], _required_text(content, "explanation"))]
    else:
        raise RenderError("Answer renderer category must be grammar, vocabulary, or situation")

    tip = content.get("tip")
    if isinstance(tip, str) and tip.strip():
        sections.append((HEADINGS["tip"], tip.strip()))
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


def _emoji_font(size: int) -> ImageFont.FreeTypeFont:
    if not EMOJI_FONT_PATH.is_file():
        raise FileNotFoundError(f"Required emoji font not found: {EMOJI_FONT_PATH}")
    font = ImageFont.truetype(str(EMOJI_FONT_PATH), size=size)
    font.set_variation_by_axes([500])
    return font


def _draw_heading(draw: ImageDraw.ImageDraw, position: tuple[int, int], heading: tuple[str, str], size: int) -> None:
    emoji, label = heading
    draw.text(position, emoji, font=_emoji_font(size), fill=TEXT)
    emoji_width = draw.textbbox((0, 0), emoji, font=_emoji_font(size))[2]
    draw.text((position[0] + emoji_width + 14, position[1]), label, font=_font(size), fill=TEXT)


def _draw_section(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], heading: tuple[str, str], text: str) -> None:
    draw.rounded_rectangle(box, radius=24, fill=BACKGROUND, outline=BORDER, width=3)
    _draw_heading(draw, (box[0] + 34, box[1] + 24), heading, 34)
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
    _draw_heading(draw, (64, 54), HEADINGS["answer"], 40)

    answer_box = (64, 118, 1016, 326)
    draw.rounded_rectangle(answer_box, radius=28, fill=BACKGROUND, outline=BORDER, width=3)
    answer = _required_text(content, "best_answer")
    from .renderer import _draw_centered_text
    _draw_centered_text(draw, answer, (96, 144, 984, 300), 88, 54, 2)

    top, bottom, gap = 370, 1286, 24
    section_height = (bottom - top - gap * (len(sections) - 1)) // len(sections)
    for index, (heading, text) in enumerate(sections):
        y1 = top + index * (section_height + gap)
        y2 = bottom if index == len(sections) - 1 else y1 + section_height
        _draw_section(draw, (64, y1, 1016, y2), heading, text)

    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    output = IMAGE_DIR / f"{content['content_id']}-answer.png"
    canvas.save(output, format="PNG", optimize=True)
    return output
