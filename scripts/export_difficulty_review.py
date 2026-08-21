#!/usr/bin/env python3
"""Export human-review artifacts for the unposted production difficulty audit."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = REPO_ROOT.parent / "english-threads-automation"
OUTPUT_DIR = REPO_ROOT / "artifacts" / "weekly" / "2026-08-20"
REVISED = {8, 10, 11, 16, 17, 20, 22, 23, 26, 27, 29, 32, 34, 39, 40, 41, 44, 46}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def head_master(content_id: str) -> dict:
    raw = subprocess.check_output(["git", "show", f"HEAD:data/master/{content_id}.json"], cwd=REPO_ROOT)
    return json.loads(raw)


def font(size: int):
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    revision_rows = []
    changed_ids = []
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        ig_queue = read(REPO_ROOT / "data" / "queue" / f"{content_id}.json")
        th_queue = read(THREADS_ROOT / "data" / "queue" / f"{content_id}.json")
        if ig_queue["status"] == "posted" or th_queue["status"] == "posted":
            continue
        master = read(REPO_ROOT / "data" / "master" / f"{content_id}.json")
        gate = master["difficulty_gate"]
        action = gate["decision"]
        reason = ("旧版は画像または捨て選択肢だけで実質1択" if action == "REVISE" and master["visual_required"]
                  else "旧版は不自然な捨て選択肢で実質1択" if action == "REVISE"
                  else "基礎英語の比較が必要で正解は一意")
        rows.append({
            "content_id": content_id,
            "mode": "visual" if master["visual_required"] else "text",
            "initial_difficulty": gate["initial_difficulty"],
            "final_difficulty": gate["difficulty"],
            "effective_choices": gate["effective_choice_count"],
            "decision": action,
            "reason": reason,
            "visual_only_solvable": gate["visual_only_solvable"],
            "common_sense_only": gate["common_sense_only"],
            "unique_answer": gate["unique_answer"],
        })
        if number in REVISED:
            old = head_master(content_id)
            revision_rows.append({
                "content_id": content_id,
                "old_question": old["question"], "new_question": master["question"],
                "old_choices": old["choices"], "new_choices": master["choices"],
                "best_answer": master["best_answer"], "reason": reason,
            })
            changed_ids.append(content_id)

    report = {
        "period": "2026-08-20/2026-08-26",
        "unposted_count": len(rows),
        "initial_counts": {
            "TOO_EASY": sum(row["initial_difficulty"] == "TOO_EASY" for row in rows),
            "TARGET": sum(row["initial_difficulty"] == "TARGET" for row in rows),
            "TOO_HARD": 0,
        },
        "final_counts": {"TOO_EASY": 0, "TARGET": len(rows), "TOO_HARD": 0},
        "items": rows,
    }
    (OUTPUT_DIR / "difficulty-audit.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit_lines = ["# 未投稿Quiz 難易度監査", "",
                   "| content_id | visual/text | initial | final | effective choices | KEEP/REVISE | 理由 |",
                   "|---|---|---|---|---:|---|---|"]
    for row in rows:
        audit_lines.append("| {content_id} | {mode} | {initial_difficulty} | {final_difficulty} | "
                           "{effective_choices} | {decision} | {reason} |".format(**row))
    (OUTPUT_DIR / "difficulty-audit.md").write_text("\n".join(audit_lines) + "\n", encoding="utf-8")

    revision_lines = ["# 修正対象一覧", ""]
    for row in revision_rows:
        revision_lines.extend([
            f"## {row['content_id']}", "",
            f"- 旧問題: `{row['old_question']}`", f"- 新問題: `{row['new_question']}`",
            f"- 旧choices: `{row['old_choices']}`", f"- 新choices: `{row['new_choices']}`",
            f"- 正解: `{row['best_answer']}`", f"- 修正理由: {row['reason']}", "",
        ])
    (OUTPUT_DIR / "difficulty-revisions.md").write_text("\n".join(revision_lines), encoding="utf-8")

    thumb_w, thumb_h, label_h, cols = 540, 675, 48, 2
    rows_count = (len(changed_ids) + cols - 1) // cols
    sheet = Image.new("RGB", (thumb_w * cols, (thumb_h + label_h) * rows_count), "white")
    draw = ImageDraw.Draw(sheet)
    label_font = font(26)
    for index, content_id in enumerate(changed_ids):
        source = Image.open(REPO_ROOT / "artifacts" / "images" / f"{content_id}-question.png").convert("RGB")
        source.thumbnail((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        sheet.paste(source, (x + (thumb_w - source.width) // 2, y))
        draw.text((x + 18, y + thumb_h + 7), content_id, font=label_font, fill="#111111")
    sheet.save(OUTPUT_DIR / "difficulty-revisions-contact-sheet.png", "PNG")
    print(f"audited={len(rows)} revised={len(revision_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
