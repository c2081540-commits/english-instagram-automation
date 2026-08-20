#!/usr/bin/env python3
import json
import sys
from datetime import date
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = REPO_ROOT.parent / "english-threads-automation"
FONT = REPO_ROOT / "assets" / "fonts" / "NotoSansJP-VariableFont_wght.ttf"


def contact_sheet(entries, target, role, columns=6):
    cell_w, cell_h = 200, 280
    rows = (len(entries) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * cell_w, rows * cell_h), "#F3F3F0")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype(str(FONT), 22)
    for index, (content_id, path) in enumerate(entries):
        x, y = (index % columns) * cell_w, (index // columns) * cell_h
        draw.text((x + 10, y + 8), content_id, font=font, fill="#111111")
        box = (x + 10, y + 42, x + cell_w - 10, y + cell_h - 10)
        if path and path.is_file():
            with Image.open(path) as raw:
                thumb = raw.convert("RGB")
                thumb.thumbnail((box[2] - box[0], box[3] - box[1]))
                px = box[0] + (box[2] - box[0] - thumb.width) // 2
                py = box[1] + (box[3] - box[1] - thumb.height) // 2
                canvas.paste(thumb, (px, py))
        else:
            draw.rounded_rectangle(box, radius=12, fill="#FFFFFF", outline="#BBBBBB", width=2)
            draw.text((box[0] + 14, box[1] + 80), "WAITING\nFOR VISUAL", font=font, fill="#666666")
    canvas.save(target, "PNG", optimize=True)


def main():
    start = sys.argv[1] if len(sys.argv) == 2 else date.today().isoformat()
    week = json.loads((REPO_ROOT / "data" / "production" / f"week-{start}.json").read_text(encoding="utf-8"))
    report = json.loads((REPO_ROOT / "data" / "production" / f"week-{start}-report.json").read_text(encoding="utf-8"))
    output = REPO_ROOT / "artifacts" / "weekly" / start
    output.mkdir(parents=True, exist_ok=True)

    question_entries = []
    answer_entries = []
    thread_lines = []
    instagram_lines = []
    for item in week["quizzes"]:
        content_id = item["content_id"]
        question = REPO_ROOT / "artifacts" / "images" / f"{content_id}-question.png"
        answer = REPO_ROOT / "artifacts" / "images" / f"{content_id}-answer.png"
        question_entries.append((content_id, question if question.is_file() else None))
        answer_entries.append((content_id, answer))
        instagram_lines.extend([
            f"[{content_id}] {item['publish_at']} | " + ("READY" if question.is_file() else "WAITING_FOR_VISUAL"),
            f"question: {question.relative_to(REPO_ROOT) if question.is_file() else None}",
            f"answer: {answer.relative_to(REPO_ROOT)}",
            f"caption: {item['instagram_caption']}", "",
        ])
        queue = json.loads((THREADS_ROOT / "data" / "queue" / f"{content_id}.json").read_text(encoding="utf-8"))
        thread_lines.extend([f"[{content_id}] {queue['publish_at']} | {queue['parent_status']}",
                             f"parent: {queue['parent_text']}", f"image: {queue['question_image']}",
                             queue["answer_text"], ""])

    story_entries = [(item["content_id"], REPO_ROOT / "artifacts" / "stories" / f"{item['content_id']}-story.png")
                     for item in week["normals"]]
    for item in week["normals"]:
        queue = json.loads((THREADS_ROOT / "data" / "queue" / f"{item['content_id']}.json").read_text(encoding="utf-8"))
        thread_lines.extend([f"[{item['content_id']}] {queue['publish_at']} | {queue['status']}", queue["text"], ""])
        instagram_lines.extend([f"[{item['content_id']}] {item['publish_at']} | READY",
                                f"story: artifacts/stories/{item['content_id']}-story.png", ""])

    contact_sheet(question_entries, output / "quiz-questions.png", "question")
    changed_entries = [(item["content_id"], REPO_ROOT / "artifacts" / "images" /
                        f"{item['content_id']}-question.png")
                       for item in week["quizzes"]
                       if item.get("question_role") == "meta_instruction"]
    contact_sheet(changed_entries, output / "quiz-question-role-fixes.png", "question", columns=2)
    contact_sheet(answer_entries, output / "quiz-answers.png", "answer")
    contact_sheet(story_entries, output / "stories.png", "story", columns=4)
    (output / "threads-dry-run.txt").write_text("\n".join(thread_lines), encoding="utf-8")
    (output / "instagram-dry-run.txt").write_text("\n".join(instagram_lines), encoding="utf-8")
    (output / "quality-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.txt").write_text(
        "Human review bundle\nquiz-questions.png: 42 question slots (pending visuals are labeled)\n"
        "quiz-answers.png: 42 answer images\nstories.png: 7 Stories\n"
        "instagram-dry-run.txt: 42 Feed plans + 7 Stories\n"
        "threads-dry-run.txt: 42 quiz threads + 7 normal posts\nquality-report.json: aggregate metrics\n",
        encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
