#!/usr/bin/env python3
"""Export the four-item human review package for the difficulty second pass."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "weekly" / "2026-08-20"
IDS = ("ENG-000023", "ENG-000032", "ENG-000034", "ENG-000046")
OLD = {
    "ENG-000023": ("She is about ___ close the window.", ["to", "for", "at", "on"],
                   "be about to＋動詞"),
    "ENG-000032": ("He is going ___ the stairs.", ["up", "on", "to", "at"],
                   "go up＝上る"),
    "ENG-000034": ("She says he ___ sit there.", ["can", "cans", "can to", "is can"],
                   "can＋動詞"),
    "ENG-000046": ("The seat is free, so I ___ sit there.", ["can", "can to", "am can", "cans"],
                   "can＋動詞"),
}


def load(content_id: str) -> dict:
    return json.loads((ROOT / "data" / "master" / f"{content_id}.json").read_text(encoding="utf-8"))


def font(size: int):
    for path in ("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
                 "/System/Library/Fonts/Helvetica.ttc"):
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    lines = ["# 難易度監査 第2回修正", ""]
    for content_id in IDS:
        item = load(content_id)
        gate = item["difficulty_gate"]
        old_question, old_choices, old_point = OLD[content_id]
        record = {
            "content_id": content_id,
            "mode": "visual" if item["visual_required"] else "text",
            "old_question": old_question,
            "new_question": item["question"],
            "old_choices": old_choices,
            "new_choices": item["choices"],
            "correct_answer": item["best_answer"],
            "old_learning_point": old_point,
            "new_learning_point": item["learning_point"],
            "effective_choice_count": gate["effective_choice_count"],
            "weak_distractor_count": gate["weak_distractor_count"],
            "visual_only_solvable": gate["visual_only_solvable"],
            "common_sense_only": gate["common_sense_only"],
            "unique_answer": gate["unique_answer"],
            "difficulty": gate["difficulty"],
        }
        records.append(record)
        lines.extend([
            f"## {content_id}", "",
            f"- 旧問題 → 新問題: `{old_question}` → `{item['question']}`",
            f"- 旧choices → 新choices: `{old_choices}` → `{item['choices']}`",
            f"- 旧learning point → 新learning point: `{old_point}` → `{item['learning_point']}`",
            f"- 正解: `{item['best_answer']}`", "",
        ])
    (OUT / "difficulty-second-pass-review.json").write_text(
        json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "difficulty-second-pass-review.md").write_text("\n".join(lines), encoding="utf-8")

    thumb_w, thumb_h, label_h, columns = 540, 675, 48, 2
    sheet = Image.new("RGB", (thumb_w * columns, (thumb_h + label_h) * 2), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = font(26)
    for index, content_id in enumerate(IDS):
        with Image.open(ROOT / "artifacts" / "images" / f"{content_id}-question.png") as source:
            image = source.convert("RGB")
        image.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = index % columns * thumb_w
        y = index // columns * (thumb_h + label_h)
        sheet.paste(image, (x + (thumb_w - image.width) // 2, y))
        draw.text((x + 18, y + thumb_h + 7), content_id, font=label_font, fill="#111111")
    sheet.save(OUT / "difficulty-second-pass-contact-sheet.png", "PNG")
    print(f"exported={len(records)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
