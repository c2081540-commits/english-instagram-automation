#!/usr/bin/env python3
"""Apply approved L1/L2/L3 levels and difficulty-aware Threads hooks."""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

IG_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = IG_ROOT.parent
THREADS_ROOT = WORKSPACE / "english-threads-automation"
sys.path.insert(0, str(IG_ROOT / "src"))
sys.path.insert(0, str(THREADS_ROOT / "src"))

from instagram_automation.difficulty import validate_distribution  # noqa: E402
from threads_automation.difficulty import (choose_hook, question_type,
                                           validate_hook_for_item)  # noqa: E402

LEVELS = {
    6: "L1", 7: "L2", 8: "L3", 9: "L2", 10: "L2", 11: "L3",
    12: "L1", 13: "L2", 14: "L1", 15: "L2", 16: "L3", 17: "L2",
    18: "L1", 19: "L2", 20: "L3", 21: "L3", 22: "L2", 23: "L2",
    24: "L2", 25: "L1", 26: "L2", 27: "L3", 28: "L2", 29: "L3",
    30: "L1", 31: "L2", 32: "L2", 33: "L3", 34: "L2", 35: "L2",
    36: "L1", 37: "L2", 38: "L3", 39: "L2", 40: "L3", 41: "L2",
    42: "L1", 43: "L2", 44: "L2", 45: "L3", 46: "L3", 47: "L2",
}
LEARNING_POINTS = {
    6: "look forward to＋-ing", 7: "地点のat", 8: "現在進行形", 9: "byとuntil",
    10: "turn onとturn off", 11: "anything else", 12: "三単現", 13: "be動詞の過去形",
    14: "状態を表す形容詞", 15: "交通手段のby", 16: "I'd like", 17: "nearとnext to",
    18: "複数主語の現在形", 19: "現在完了とjust", 20: "手段を表すwith", 21: "afterとlater",
    22: "You're welcome", 23: "be about to＋動詞", 24: "比較級", 25: "現在進行形",
    26: "否定文のanything", 27: "manyとmuch", 28: "時刻のatと曜日のon", 29: "Don't＋動詞",
    30: "There isとThere are", 31: "have to", 32: "upとup toの使い分け", 33: "becauseとso",
    34: "会話でのyouとIの使い分け", 35: "三単現", 36: "can＋動詞", 37: "否定文のyet",
    38: "物を表すthat", 39: "out of", 40: "Could you＋動詞", 41: "offer to＋動詞",
    42: "三単現", 43: "sinceとfor", 44: "in half", 45: "曜日のonと時刻のat",
    46: "現在進行形の疑問文", 47: "take a break",
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def posted_ids() -> set[str]:
    posted = set()
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        for root in (IG_ROOT, THREADS_ROOT):
            if read(root / "data" / "queue" / f"{content_id}.json")["status"] == "posted":
                posted.add(content_id)
    return posted


def update_item(item: dict, posted: set[str]) -> None:
    content_id = item.get("content_id")
    if not isinstance(content_id, str) or not content_id.startswith("ENG-000"):
        return
    number = int(content_id.split("-")[1])
    if number not in LEVELS or content_id in posted:
        return
    item["difficulty_level"] = LEVELS[number]
    item["learning_point"] = LEARNING_POINTS[number]


def walk(value, posted: set[str]) -> None:
    if isinstance(value, dict):
        update_item(value, posted)
        for child in value.values():
            walk(child, posted)
    elif isinstance(value, list):
        for child in value:
            walk(child, posted)


def main() -> int:
    posted = posted_ids()
    unposted_masters = []
    threads_masters = {}
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        if content_id in posted:
            continue
        ig_path = IG_ROOT / "data" / "master" / f"{content_id}.json"
        th_path = THREADS_ROOT / "data" / "master" / "quiz" / f"{content_id}.json"
        ig_item, th_item = read(ig_path), read(th_path)
        update_item(ig_item, posted)
        update_item(th_item, posted)
        write(ig_path, ig_item)
        write(th_path, th_item)
        unposted_masters.append(ig_item)
        threads_masters[content_id] = th_item

    for path in sorted((IG_ROOT / "data" / "production").glob("*.json")):
        value = read(path)
        walk(value, posted)
        write(path, value)

    recent_hooks: list[str] = []
    hook_rows = []
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        ig_queue_path = IG_ROOT / "data" / "queue" / f"{content_id}.json"
        th_queue_path = THREADS_ROOT / "data" / "queue" / f"{content_id}.json"
        ig_queue, th_queue = read(ig_queue_path), read(th_queue_path)
        if content_id in posted:
            continue
        master = threads_masters[content_id]
        hook = choose_hook(master, recent_hooks)
        validate_hook_for_item(master, hook)
        recent_hooks.append(hook)
        master["threads_parent_text"] = hook
        th_queue["parent_text"] = hook
        ig_queue["difficulty_level"] = LEVELS[number]
        th_queue["difficulty_level"] = LEVELS[number]
        write(THREADS_ROOT / "data" / "master" / "quiz" / f"{content_id}.json", master)
        write(ig_queue_path, ig_queue)
        write(th_queue_path, th_queue)
        hook_rows.append((content_id, LEVELS[number], question_type(master), hook,
                          master.get("question_guide_ja")))

    audit_items = []
    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        queue = read(IG_ROOT / "data" / "queue" / f"{content_id}.json")
        audit_items.append({"content_id": content_id, "publish_at": queue["publish_at"],
                            "difficulty_level": LEVELS[number]})
    report = validate_distribution(audit_items)
    by_day = defaultdict(list)
    for item in sorted(audit_items, key=lambda row: row["publish_at"]):
        by_day[item["publish_at"][:10]].append(item)
    out = IG_ROOT / "artifacts" / "weekly" / "2026-08-20"
    out.mkdir(parents=True, exist_ok=True)
    payload = {"posted_immutable": sorted(posted), "distribution": report,
               "items": audit_items}
    write(out / "difficulty-level-audit.json", payload)
    lines = ["# 日次Difficulty表", ""]
    for day, entries in sorted(by_day.items()):
        counts = Counter(item["difficulty_level"] for item in entries)
        lines.extend([f"## {day}", "",
                      f"L1 {counts['L1']} / L2 {counts['L2']} / L3 {counts['L3']}", ""])
        lines.extend(f"- {item['publish_at'][11:16]} {item['difficulty_level']} {item['content_id']}"
                     for item in entries)
        lines.append("")
    lines.extend(["## 週次集計", "",
                  f"- L1 {report['weekly']['L1']}", f"- L2 {report['weekly']['L2']}",
                  f"- L3 {report['weekly']['L3']}", ""])
    (out / "difficulty-level-daily.md").write_text("\n".join(lines), encoding="utf-8")
    hook_lines = ["# Threads Hook対応表", "",
                  "| content_id | difficulty | question type | threads_hook | question_guide_ja | 判定 |",
                  "|---|---|---|---|---|---|"]
    for row in hook_rows:
        hook_lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4] or '-'} | PASS |")
    (out / "difficulty-level-hooks.md").write_text("\n".join(hook_lines) + "\n", encoding="utf-8")
    print(f"unposted={len(unposted_masters)} posted_immutable={len(posted)} "
          f"distribution={dict(report['weekly'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
