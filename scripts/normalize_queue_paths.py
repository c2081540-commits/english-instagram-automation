"""Normalize existing Instagram queue assets to repo-relative paths without changing state."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUEUE_DIR = REPO_ROOT / "data" / "queue"


def normalize(value: str) -> str:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (REPO_ROOT / path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise ValueError(f"Queue asset is outside repo root: {value}") from exc


def main() -> None:
    changed = 0
    for path in sorted(QUEUE_DIR.glob("ENG-*.json")):
        queue = json.loads(path.read_text(encoding="utf-8"))
        before = json.dumps(queue, ensure_ascii=False, sort_keys=True)
        if queue.get("platform") != "instagram":
            continue
        if queue.get("content_type") == "quiz":
            for slide in queue.get("carousel", []):
                slide["image_path"] = normalize(slide["image_path"])
        elif queue.get("content_type") == "normal":
            queue["story_image"] = normalize(queue["story_image"])
        after = json.dumps(queue, ensure_ascii=False, sort_keys=True)
        if before != after:
            path.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            changed += 1
    print(f"normalized_queue_files={changed}")


if __name__ == "__main__":
    main()
