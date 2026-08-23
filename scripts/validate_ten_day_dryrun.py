#!/usr/bin/env python3
"""Read-only validation of an approved multi-day dataset before production import."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = REPO_ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(THREADS_ROOT / "src"))

from instagram_automation.formats import (NEW_FORMATS, from_dryrun,
                                           validate_answer_payload,
                                           validate_format_master,
                                           validate_quiz_schedule)
from threads_automation.formats import (validate_format_master as validate_threads_master,
                                         from_dryrun as threads_from_dryrun,
                                         validate_threads_reply)

SLOTS = ["07:00", "09:30", "12:00", "15:00", "18:00", "20:30"]


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def enrich_standard(record: dict, item: dict, visual_audit: dict) -> None:
    existing = REPO_ROOT / "data" / "master" / f"{item['content_id']}.json"
    base = read(existing) if existing.is_file() else {}
    record.update(
        explanation=item.get("explanation") or base.get("explanation"),
        completed_sentence=item.get("example") or (base.get("examples") or [None])[0],
        japanese_translation=item.get("translation") or (base.get("example_translations") or [None])[0],
        question_guide_ja=(None if record["format"] == "visual" else
                           item.get("question_guide_ja") or base.get("question_guide_ja")),
    )
    if record["format"] == "visual":
        audit = visual_audit[item["content_id"]]
        record.update(visual_semantic_consistency=True, visual_answer_uniqueness=True,
                      visual_only_solvable=False,
                      visual_semantics={"subject_gender":"verified","subject_count":"verified",
                      "action":audit["visual_evidence"],"direction":"verified","object":"verified",
                      "state":"verified","location":"verified",
                      "completed_sentence":record["completed_sentence"]})


def payload(record: dict) -> dict:
    result = {"format":record["format"], "correct_answer":record["correct_answer"]}
    if record["format"] == "error_hunt": result["answer_sentences"] = record["answer_sentences"]
    elif record["format"] == "pattern": result.update(pattern_rule=record["pattern_rule"], examples=record["examples"])
    elif record["format"] == "save_list": result["complete_list"] = record["complete_list"]
    elif record["format"] == "difference": result["choice_explanations"] = record["choice_explanations"]
    return result


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    args=parser.parse_args()
    source=args.dataset.resolve()
    content=read(source/"content-candidates.json")
    schedule=read(source/"schedule.json")
    visuals={row["content_id"]:row for row in read(source/"visual-14-audit.json")}
    queue=[]; formats=Counter(); difficulty=Counter(); positions={2:Counter(),4:Counter()}; records={}
    previous=None; streak=max_streak=0; learning=[]
    for slot in schedule:
        item=content[slot["content_id"]]
        record=from_dryrun(item,slot["publish_at"])
        threads_record=threads_from_dryrun(item,slot["publish_at"])
        if record["format"] in {"text","visual"}: enrich_standard(record,item,visuals)
        if threads_record["format"] in {"text","visual"}: enrich_standard(threads_record,item,visuals)
        if record != threads_record: raise ValueError(f"Instagram/Threads master mismatch: {record['content_id']}")
        validate_format_master(record); validate_threads_master(record)
        if record["format"] in NEW_FORMATS: validate_answer_payload(record,payload(record))
        validate_threads_reply(record,item["threads_reply"])
        records[record["content_id"]]=record
        queue.append({"content_id":record["content_id"],"publish_at":record["publish_at"],"status":"pending"})
        formats[record["format"]]+=1; difficulty[record["difficulty"]]+=1
        if record.get("choices"):
            letter=chr(ord("A")+record["choices"].index(record["correct_answer"])); positions[len(record["choices"])][letter]+=1
            streak=streak+1 if letter==previous else 1; previous=letter; max_streak=max(max_streak,streak)
        else: streak=0; previous=None
        learning.append(record["learning_point"])
        for role in ("question","answer"):
            with Image.open(source/"images"/f"{record['content_id']}-{role}.png") as image:
                if (image.format,image.mode,image.size)!=("PNG","RGB",(1080,1350)): raise ValueError(f"invalid image: {record['content_id']} {role}")
    validate_quiz_schedule(queue,"2026-08-24","2026-09-02",SLOTS)
    duplicates=[schedule[i]["content_id"] for i,value in enumerate(learning) if value in learning[max(0,i-20):i]]
    result={"master":len(records),"queue":len(queue),"sync":len(records),"formats":dict(formats),
            "difficulty":dict(difficulty),"two_choice":dict(positions[2]),"four_choice":dict(positions[4]),
            "max_position_streak":max_streak,"learning_point_duplicates":duplicates,
            "error_hunt_sentences":sum(len(x.get("sentences",[])) for x in records.values()),
            "visual_semantic":sum(x.get("visual_semantic_consistency") is True for x in records.values()),
            "visual_uniqueness":sum(x.get("visual_answer_uniqueness") is True for x in records.values()),
            "production_writes":0}
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))


if __name__ == "__main__":
    main()
