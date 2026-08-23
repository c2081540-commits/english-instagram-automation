#!/usr/bin/env python3
"""Balance only unposted production Quiz choices and synchronize both repositories."""
from __future__ import annotations

import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREADS = ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(ROOT / "src"))

from instagram_automation.answer_renderer import render_answer
from instagram_automation.renderer import render_question


TARGET_POSITION = {
    # 2-choice: final overall A/B = 11/10; only six current A answers move to B.
    "ENG-000010": "B", "ENG-000028": "B", "ENG-000032": "B",
    "ENG-000034": "B", "ENG-000037": "B", "ENG-000046": "B",
    # 4-choice: posted A positions are immutable; remaining answers add no new A.
    "ENG-000007": "C", "ENG-000011": "D", "ENG-000029": "D",
    "ENG-000030": "B", "ENG-000035": "C", "ENG-000038": "D",
    "ENG-000039": "B", "ENG-000040": "C", "ENG-000041": "D",
    "ENG-000044": "B", "ENG-000047": "C",
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def letter(item: dict) -> str:
    return "ABCD"[item["choices"].index(item["best_answer"])]


def reorder(item: dict, wanted: str) -> bool:
    if not isinstance(item, dict) or item.get("content_id") not in TARGET_POSITION:
        return False
    if not isinstance(item.get("choices"), list) or item.get("best_answer") not in item["choices"]:
        return False
    best = item["best_answer"]
    index = "ABCD".index(wanted)
    if index >= len(item["choices"]):
        raise ValueError(f"position outside choices: {item['content_id']}")
    distractors = [choice for choice in item["choices"] if choice != best]
    item["choices"] = distractors[:index] + [best] + distractors[index:]
    text = item.get("threads_answer_text")
    if isinstance(text, str):
        item["threads_answer_text"] = re.sub(
            r"^💡 正解は [A-D]\. ", f"💡 正解は {wanted}. ", text, count=1)
    return True


def walk(value) -> bool:
    changed = False
    if isinstance(value, dict):
        changed = reorder(value, TARGET_POSITION.get(value.get("content_id"), "A"))
        for child in value.values():
            changed = walk(child) or changed
    elif isinstance(value, list):
        for child in value:
            changed = walk(child) or changed
    return changed


def distributions(rows: list[dict]) -> dict:
    result = {}
    for count in (2, 4):
        values = Counter(letter(item) for item in rows if len(item["choices"]) == count)
        result[str(count)] = {key: values[key] for key in "ABCD"[:count]}
    return result


def max_streak(rows: list[dict]) -> int:
    maximum = current = 0
    previous = None
    for item in sorted(rows, key=lambda value: value["publish_at"]):
        value = letter(item)
        current = current + 1 if value == previous else 1
        previous = value
        maximum = max(maximum, current)
    return maximum


def main() -> int:
    all_before = [read(ROOT / "data/master" / f"ENG-{number:06d}.json")
                  for number in range(6, 48)]
    protected = set()
    for item in all_before:
        content_id = item["content_id"]
        ig_queue = read(ROOT / "data/queue" / f"{content_id}.json")
        th_queue = read(THREADS / "data/queue" / f"{content_id}.json")
        if ig_queue["status"] == "posted" or th_queue["status"] == "posted":
            protected.add(content_id)
    collision = protected & TARGET_POSITION.keys()
    if collision:
        raise RuntimeError(f"posted content cannot be changed: {sorted(collision)}")

    rows = []
    for content_id, wanted in TARGET_POSITION.items():
        ig_path = ROOT / "data/master" / f"{content_id}.json"
        th_path = THREADS / "data/master/quiz" / f"{content_id}.json"
        ig, th = read(ig_path), read(th_path)
        before = letter(ig)
        if any(ig[field] != th[field] for field in ("question", "choices", "best_answer")):
            raise RuntimeError(f"platform mismatch before update: {content_id}")
        reorder(ig, wanted); reorder(th, wanted)
        write(ig_path, ig); write(th_path, th)
        th_queue_path = THREADS / "data/queue" / f"{content_id}.json"
        th_queue = read(th_queue_path)
        th_queue["answer_text"] = th["threads_answer_text"]
        write(th_queue_path, th_queue)
        rows.append({"content_id": content_id, "before": before, "after": wanted,
                     "best_answer": ig["best_answer"], "publish_at": ig["publish_at"],
                     "choice_count": len(ig["choices"])})

    for directory in (ROOT / "data/production", ROOT / "data/review"):
        for path in sorted(directory.rglob("*.json")):
            value = read(path)
            if walk(value):
                write(path, value)

    for content_id in TARGET_POSITION:
        master = ROOT / "data/master" / f"{content_id}.json"
        question = render_question(master)
        answer = render_answer(master)
        shutil.copy2(question, THREADS / "assets/question_images" / question.name)
        target_answer = THREADS / "assets/answer_images" / answer.name
        if target_answer.parent.is_dir():
            shutil.copy2(answer, target_answer)

    all_after = [read(ROOT / "data/master" / f"ENG-{number:06d}.json")
                 for number in range(6, 48)]
    unposted_after = [item for item in all_after if item["content_id"] not in protected]
    difficulty_positions = defaultdict(Counter)
    for item in all_after:
        difficulty_positions[item.get("difficulty_level", item["difficulty"])][letter(item)] += 1
    report = {
        "quiz_total": 42, "protected_posted": sorted(protected),
        "unposted_count": len(unposted_after), "changed_count": len(rows),
        "changes": sorted(rows, key=lambda row: row["publish_at"]),
        "before": {"distribution": distributions(all_before),
                   "max_same_position_streak": max_streak(all_before)},
        "after": {"distribution": distributions(all_after),
                  "unposted_distribution": distributions(unposted_after),
                  "max_same_position_streak": max_streak(all_after)},
        "difficulty_cross_tab": {key: dict(value) for key, value in difficulty_positions.items()},
        "immutable_history_exception": {
            "four_choice_target": "mathematically minimal max-min after protecting posted content",
            "max_streak": "historical posted streak remains immutable; unposted sequence <= 2",
        },
    }
    out = ROOT / "artifacts/weekly/2026-08-20/correct-position-audit.json"
    write(out, report)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
