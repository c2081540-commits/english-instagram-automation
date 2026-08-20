"""Apply the approved text-question template metadata to the reviewed production week."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = REPO_ROOT.parent
THREADS_ROOT = WORKSPACE_ROOT / "english-threads-automation"
sys.path.insert(0, str(THREADS_ROOT / "src"))

from threads_automation.content import build_answer_text, select_hook, validate_hook_guide  # noqa: E402


GUIDES = {
    "ENG-000003": "「5年間住んでいる」ならどれ？",
    "ENG-000004": "「毎朝飲む」ならどっち？",
    "ENG-000005": "こう頼まれたら、どう返す？",
    "ENG-000006": "「再会が楽しみ」ならどれ？",
    "ENG-000007": "「会社に着いた」ならどれ？",
    "ENG-000009": "「金曜日までに送る」ならどれ？",
    "ENG-000011": "こう聞かれたら、どう返す？",
    "ENG-000012": "「トムは8時出勤」ならどっち？",
    "ENG-000013": "「昨日は大忙し」ならどっち？",
    "ENG-000015": "一番自然なのはどれ？",
    "ENG-000017": "こう聞かれたら、どう返す？",
    "ENG-000018": "「東京に住む」ならどっち？",
    "ENG-000019": "「昼食を終えた」ならどれ？",
    "ENG-000021": "一番自然なのはどれ？",
    "ENG-000022": "こんなとき、英語でどう言う？",
    "ENG-000024": "「私のより重い」ならどれ？",
    "ENG-000025": "「今、夕食中」ならどっち？",
    "ENG-000028": "自然なのはどっち？",
    "ENG-000029": "こんなとき、英語でどう言う？",
    "ENG-000030": "「近くに銀行がある」ならどれ？",
    "ENG-000031": "「早起きしないと」ならどっち？",
    "ENG-000033": "自然なのはどっち？",
    "ENG-000035": "正しい英文はどれ？",
    "ENG-000036": "「英語を話せる？」ならどっち？",
    "ENG-000037": "「昼食はまだ」ならどっち？",
    "ENG-000038": "「私が買った本」ならどれ？",
    "ENG-000040": "こんなとき、英語でどう言う？",
    "ENG-000042": "「9時に開く」ならどっち？",
    "ENG-000043": "「2020年から」ならどっち？",
    "ENG-000045": "自然なのはどっち？",
    "ENG-000047": "「休憩する」の意味になるのはどれ？",
}
META_IDS = {"ENG-000035", "ENG-000047"}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def update_content(item: dict) -> None:
    content_id = item.get("content_id")
    if not isinstance(content_id, str) or not content_id.startswith("ENG-000"):
        return
    if "visual_required" not in item:
        return
    visual = item.get("visual_required") is True
    item["question_guide_ja"] = None if visual else GUIDES.get(content_id)
    item["question_role"] = (None if visual else
                             ("meta_instruction" if content_id in META_IDS else "learning_sentence"))
    if not visual and item["question_guide_ja"] is None:
        raise ValueError(f"Missing approved guide for {content_id}")
    if 6 <= int(content_id.split("-")[1]) <= 47:
        if "threads_answer_text" in item:
            item["threads_answer_text"] = build_answer_text(item)
        if "threads_parent_text" in item and not visual:
            hook = select_hook(item["category"], content_id, False)
            validate_hook_guide(hook, item["question_guide_ja"], False)
            item["threads_parent_text"] = hook


def walk(value) -> None:
    if isinstance(value, dict):
        update_content(value)
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def main() -> None:
    for root, pattern in ((REPO_ROOT / "data" / "master", "ENG-*.json"),
                          (THREADS_ROOT / "data" / "master" / "quiz", "ENG-*.json")):
        for path in sorted(root.glob(pattern)):
            data = read(path)
            update_content(data)
            write(path, data)

    for path in sorted((REPO_ROOT / "data" / "production").glob("*.json")):
        data = read(path)
        walk(data)
        write(path, data)

    for number in range(6, 48):
        content_id = f"ENG-{number:06d}"
        master_path = THREADS_ROOT / "data" / "master" / "quiz" / f"{content_id}.json"
        master = read(master_path)
        queue_path = THREADS_ROOT / "data" / "queue" / f"{content_id}.json"
        queue = read(queue_path)
        queue.pop("answer_image", None)
        queue["answer_text"] = build_answer_text(master)
        if not master["visual_required"]:
            hook = select_hook(master["category"], content_id, False)
            validate_hook_guide(hook, master["question_guide_ja"], False)
            queue["parent_text"] = hook
        write(queue_path, queue)


if __name__ == "__main__":
    main()
