#!/usr/bin/env python3
"""Apply the approved visual-semantic audit without changing schedules or status."""
from __future__ import annotations

import json
from pathlib import Path

IG_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = IG_ROOT.parent / "english-threads-automation"

TARGET_IDS = {
    "ENG-000008", "ENG-000010", "ENG-000020", "ENG-000026", "ENG-000027",
    "ENG-000032", "ENG-000034", "ENG-000039", "ENG-000041", "ENG-000044",
    "ENG-000046",
}

REVISIONS = {
    "ENG-000020": {
        "question": "He carries the box ___ both hands.",
        "examples": ["He carries the box with both hands."],
        "example_translations": ["彼は両手で箱を運びます。"],
        "threads_answer_text": "💡 正解は A. with\n\nwith both handsで「両手で」という意味になります。\n\n📝 He carries the box with both hands.\n「彼は両手で箱を運びます。」\n\n🔑 with＋道具・体の一部＝〜を使って",
    },
    "ENG-000044": {
        "question": "He is folding the paper ___ half.",
        "examples": ["He is folding the paper in half."],
        "example_translations": ["彼は紙を半分に折っています。"],
        "threads_answer_text": "💡 正解は A. in\n\nfold ... in halfで「〜を半分に折る」を表します。\n\n📝 He is folding the paper in half.\n「彼は紙を半分に折っています。」\n\n🔑 in half＝半分に",
    },
}

SEMANTICS = {
    "ENG-000008": ("male", 1, "rolling up a shirt sleeve", None, "shirt sleeve", "being rolled", "office"),
    "ENG-000010": ("male", 2, "turning on an air conditioner", None, "air conditioner remote", "AC currently needs activation", "office"),
    "ENG-000020": ("male", 1, "carrying", None, "one cardboard box", "held with both hands", "office"),
    "ENG-000026": ("none", 0, None, None, "one cup", "empty", "desk"),
    "ENG-000027": ("mixed", "many", "slow traffic", None, "multiple cars", "too many cars", "city road"),
    "ENG-000032": ("male", 1, "walking", "up", "stairs", "ascending", "indoor stairs"),
    "ENG-000034": ("female speaker to male listener", 2, "offering a seat", None, "one empty chair", "available", "office break area"),
    "ENG-000039": ("none", 0, "water flowing", "out", "one bottle", "open and leaking", "picnic table"),
    "ENG-000041": ("female helper to male carrier", 2, "offering help", None, "multiple boxes", "being carried with difficulty", "office"),
    "ENG-000044": ("male", 1, "folding", "in half", "one sheet of paper", "being folded", "desk"),
    "ENG-000046": ("male speaker", 1, "indicating an empty seat", None, "one empty train seat", "unoccupied", "train"),
}


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def apply_item(item: dict) -> None:
    content_id = item.get("content_id")
    if content_id not in TARGET_IDS:
        return
    if content_id in REVISIONS:
        item.update(REVISIONS[content_id])
    gender, count, action, direction, obj, state, location = SEMANTICS[content_id]
    completed = item["question"].replace("___", item["best_answer"])
    item["visual_semantic_consistency"] = True
    item["visual_semantics"] = {
        "subject_gender": gender, "subject_count": count, "action": action,
        "direction": direction, "object": obj, "state": state, "location": location,
        "completed_sentence": completed,
    }


def walk(value) -> None:
    if isinstance(value, dict):
        apply_item(value)
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def main() -> int:
    for content_id in sorted(TARGET_IDS):
        for path in (IG_ROOT / "data/master" / f"{content_id}.json",
                     THREADS_ROOT / "data/master/quiz" / f"{content_id}.json"):
            data = read(path)
            apply_item(data)
            write(path, data)
        if content_id in REVISIONS:
            queue_path = THREADS_ROOT / "data/queue" / f"{content_id}.json"
            queue = read(queue_path)
            queue["answer_text"] = REVISIONS[content_id]["threads_answer_text"]
            write(queue_path, queue)

    for path in sorted((IG_ROOT / "data/production").glob("*.json")):
        data = read(path)
        walk(data)
        write(path, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
