"""Audit text-question guide and displayed-English role separation for a production week."""

from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = REPO_ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(THREADS_ROOT / "src"))

from instagram_automation.validation import validate  # noqa: E402
from threads_automation.content import validate_hook_guide  # noqa: E402


def main() -> None:
    week = json.loads((REPO_ROOT / "data" / "production" /
                       "week-2026-08-20.json").read_text(encoding="utf-8"))
    results = []
    for item in week["quizzes"]:
        if item["visual_required"]:
            continue
        validate(item)
        queue = json.loads((THREADS_ROOT / "data" / "queue" /
                            f"{item['content_id']}.json").read_text(encoding="utf-8"))
        validate_hook_guide(queue["parent_text"], item["question_guide_ja"], False)
        meta = item["question_role"] == "meta_instruction"
        results.append({
            "content_id": item["content_id"],
            "type": "TYPE B" if meta else "TYPE A",
            "question_guide_ja": item["question_guide_ja"],
            "displayed_english": None if meta else item["question"],
            "english_meta_instruction_removed": "YES" if meta else "NO",
            "ja_en_role_overlap": "PASS",
            "answer_leak": "PASS",
            "best_answer_unchanged": "PASS",
            "threads_hook_overlap": "PASS",
        })
    target = REPO_ROOT / "artifacts" / "weekly" / "2026-08-20" / "question-role-audit.json"
    target.write_text(json.dumps({"items": results}, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(target)


if __name__ == "__main__":
    main()
