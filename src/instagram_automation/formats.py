from __future__ import annotations

from collections import Counter
from datetime import date, datetime

FORMATS = {"text", "visual", "error_hunt", "pattern", "save_list", "difference"}
NEW_FORMATS = {"error_hunt", "pattern", "save_list", "difference"}
DIFFICULTIES = {"L1", "L2", "L3"}
VERDICTS = {"CORRECT", "INCORRECT"}


class FormatValidationError(ValueError):
    pass


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise FormatValidationError(f"{field} must be non-empty")
    return value


def _choices(record):
    choices = record.get("choices")
    if not isinstance(choices, list) or len(choices) not in {2, 4} or len(set(choices)) != len(choices):
        raise FormatValidationError("choices must contain 2 or 4 unique values")
    if any(not isinstance(x, str) or not x.strip() for x in choices):
        raise FormatValidationError("choices must be non-empty strings")
    answer = _text(record.get("correct_answer"), "correct_answer")
    if choices.count(answer) != 1:
        raise FormatValidationError("correct_answer must occur exactly once in choices")
    if record.get("unique_answer") is not True:
        raise FormatValidationError("unique_answer must be true")


def _common(record):
    if record.get("format") not in FORMATS:
        raise FormatValidationError("unsupported format")
    for field in ("content_id", "learning_point", "question", "correct_answer", "publish_at"):
        _text(record.get(field), field)
    if record.get("difficulty") not in DIFFICULTIES:
        raise FormatValidationError("difficulty must be L1, L2, or L3")
    try:
        if datetime.fromisoformat(record["publish_at"]).tzinfo is None:
            raise ValueError
    except ValueError as exc:
        raise FormatValidationError("publish_at must include timezone") from exc
    for field in ("english_correctness", "unique_answer"):
        if record.get(field) is not True:
            raise FormatValidationError(f"{field} must be true")


def _error_hunt(record):
    rows = record.get("sentences")
    if not isinstance(rows, list) or len(rows) != 4:
        raise FormatValidationError("error_hunt requires exactly 4 sentences")
    wrong = []
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise FormatValidationError("each sentence audit must be an object")
        for field in ("sentence", "corrected_sentence", "grammar_rule", "reason_ja"):
            _text(row.get(field), f"sentences[{index}].{field}")
        verdict = row.get("verdict")
        if verdict not in VERDICTS:
            raise FormatValidationError("verdict must be CORRECT or INCORRECT")
        same = row["sentence"] == row["corrected_sentence"]
        if verdict == "CORRECT" and not same:
            raise FormatValidationError("CORRECT sentence cannot be changed")
        if verdict == "INCORRECT" and same:
            raise FormatValidationError("INCORRECT sentence requires a correction")
        if verdict == "INCORRECT":
            wrong.append(index)
    if not wrong:
        raise FormatValidationError("error_hunt requires at least one incorrect sentence")
    derived = f"{len(wrong)}個" if record.get("answer_mode") == "count" else f"{wrong[0]}番"
    if record.get("correct_answer") != derived or record.get("displayed_answer") != derived:
        raise FormatValidationError("incorrect count/position must be derived from verdicts")
    answer_rows = record.get("answer_sentences")
    if not isinstance(answer_rows, list) or len(answer_rows) != len(rows):
        raise FormatValidationError("answer_sentences must cover every sentence")
    for audit, answer in zip(rows, answer_rows):
        expected = (audit["verdict"], audit["corrected_sentence"], audit["reason_ja"])
        actual = (answer.get("verdict"), answer.get("corrected_sentence"), answer.get("reason_ja"))
        if actual != expected:
            raise FormatValidationError("answer sentence verdict/correction/reason mismatch")


def _pattern(record):
    examples = record.get("examples")
    if not isinstance(examples, list) or not 2 <= len(examples) <= 4 or any(not isinstance(x, str) or not x.strip() for x in examples):
        raise FormatValidationError("pattern examples must contain 2-4 non-empty examples")
    _text(record.get("target"), "target")
    _text(record.get("pattern_rule"), "pattern_rule")
    if record.get("examples_learning_point") != record.get("learning_point") or record.get("target_learning_point") != record.get("learning_point"):
        raise FormatValidationError("examples and target must share the learning_point")
    _choices(record)


def _save_list(record):
    rows = record.get("list_items")
    if not isinstance(rows, list) or not 4 <= len(rows) <= 5:
        raise FormatValidationError("save_list requires 4-5 list_items")
    for index, row in enumerate(rows, 1):
        if not isinstance(row, dict):
            raise FormatValidationError("each list item must be an object")
        _text(row.get("english"), f"list_items[{index}].english")
        _text(row.get("japanese"), f"list_items[{index}].japanese")
    theme = _text(record.get("list_theme"), "list_theme")
    target = record.get("target_item")
    if not isinstance(target, dict):
        raise FormatValidationError("target_item must be an object")
    for field in ("prompt", "completed", "japanese"):
        _text(target.get(field), f"target_item.{field}")
    if target.get("list_theme") != theme:
        raise FormatValidationError("target_item must belong to list_theme")
    complete = record.get("complete_list")
    if not isinstance(complete, list) or len(complete) != len(rows) + 1:
        raise FormatValidationError("answer must contain the complete list")
    if any(not x.get("english") or not x.get("japanese") for x in complete if isinstance(x, dict)):
        raise FormatValidationError("complete list requires English and Japanese")
    _choices(record)


def _difference(record):
    _choices(record)
    explanations = record.get("choice_explanations")
    if not isinstance(explanations, dict) or set(explanations) != set(record["choices"]):
        raise FormatValidationError("every choice requires exactly one explanation")
    if any(not isinstance(value, str) or not value.strip() for value in explanations.values()):
        raise FormatValidationError("choice explanations must be non-empty")
    completed = record["question"].replace("___", record["correct_answer"])
    if record.get("completed_sentence") != completed:
        raise FormatValidationError("completed_sentence must use the exact correct_answer")


def validate_format_master(record):
    _common(record)
    dispatch = {"error_hunt": _error_hunt, "pattern": _pattern,
                "save_list": _save_list, "difference": _difference}
    validator = dispatch.get(record["format"])
    if validator:
        validator(record)


def validate_threads_reply(record, text):
    _text(text, "threads_reply")
    answer = record["correct_answer"]
    if answer not in text:
        raise FormatValidationError("reply must contain the correct answer")
    fmt = record["format"]
    if fmt == "error_hunt":
        if record["displayed_answer"] not in text:
            raise FormatValidationError("reply must contain the derived incorrect count/position")
        for row in record["sentences"]:
            mark = "○" if row["verdict"] == "CORRECT" else "×"
            if mark not in text or row["corrected_sentence"] not in text or row["reason_ja"] not in text:
                raise FormatValidationError("reply must cover every Error Hunt sentence")
    elif fmt == "pattern":
        if record["pattern_rule"] not in text or any(x not in text for x in record["examples"]):
            raise FormatValidationError("pattern reply must contain rule and examples")
    elif fmt == "save_list":
        for row in record["complete_list"]:
            if row["english"] not in text or row["japanese"] not in text:
                raise FormatValidationError("save_list reply must contain the complete bilingual list")
    elif fmt == "difference":
        for choice, explanation in record["choice_explanations"].items():
            if choice not in text or explanation not in text:
                raise FormatValidationError("difference reply must explain every choice")


def validate_answer_payload(record, payload):
    if not isinstance(payload, dict) or payload.get("format") != record.get("format"):
        raise FormatValidationError("answer payload format mismatch")
    if payload.get("correct_answer") != record.get("correct_answer"):
        raise FormatValidationError("answer payload correct_answer mismatch")
    fmt = record["format"]
    if fmt == "error_hunt" and payload.get("answer_sentences") != record.get("answer_sentences"):
        raise FormatValidationError("Error Hunt answer payload mismatch")
    if fmt == "pattern" and (payload.get("pattern_rule") != record.get("pattern_rule") or payload.get("examples") != record.get("examples")):
        raise FormatValidationError("Pattern answer payload mismatch")
    if fmt == "save_list" and payload.get("complete_list") != record.get("complete_list"):
        raise FormatValidationError("Save List answer payload mismatch")
    if fmt == "difference" and payload.get("choice_explanations") != record.get("choice_explanations"):
        raise FormatValidationError("Difference answer payload mismatch")


def from_dryrun(item, publish_at):
    """Convert an approved review record to the canonical production-format schema in memory."""
    names = {"Text":"text", "Visual":"visual", "Error Hunt":"error_hunt",
             "Pattern":"pattern", "Save List":"save_list", "Difference":"difference"}
    record = {"content_id":item["content_id"], "format":names[item["format"]],
              "difficulty":item["difficulty"], "learning_point":item["learning_point"],
              "question":item["question"], "correct_answer":item["correct_answer"],
              "publish_at":publish_at, "english_correctness":True, "unique_answer":True}
    fmt = record["format"]
    if fmt == "error_hunt":
        rows = [{k:row[k] for k in ("sentence","verdict","corrected_sentence","grammar_rule","reason_ja")}
                for row in item["sentence_audit"]]
        record.update(sentences=rows, answer_mode="count" if "何個" in item["question"] else "position",
                      displayed_answer=item["correct_answer"],
                      answer_sentences=[{"verdict":r["verdict"],"corrected_sentence":r["corrected_sentence"],
                                         "reason_ja":r["reason_ja"]} for r in rows])
    elif fmt == "pattern":
        rule = next(value for heading,value in item["answer_sections"] if heading in {"パターン","ルール"})
        record.update(examples=item["examples"][:-1], target=item["examples"][-1], choices=item["choices"],
                      pattern_rule=rule, examples_learning_point=item["learning_point"],
                      target_learning_point=item["learning_point"])
    elif fmt == "save_list":
        known=item["list_items"][:-1]; target=item["list_items"][-1]; complete=item["complete_items"]
        record.update(list_items=[{"english":a,"japanese":b} for a,b in known], list_theme=item["question"],
                      target_item={"prompt":target[0],"completed":complete[-1][0],"japanese":target[1],"list_theme":item["question"]},
                      choices=item["choices"], complete_list=[{"english":a,"japanese":b} for a,b in complete])
    elif fmt == "difference":
        record.update(choices=item["choices"], choice_explanations=dict(item["differences"]),
                      completed_sentence=item["question"].replace("___",item["correct_answer"]))
    else:
        record["choices"] = item.get("choices", [])
    return record


def validate_quiz_schedule(items, start_date, end_date, slots):
    start=date.fromisoformat(start_date); end=date.fromisoformat(end_date)
    expected_days=(end-start).days+1
    if len(items) != expected_days*len(slots):
        raise FormatValidationError("schedule item count must equal date range times daily slots")
    ids=[x.get("content_id") for x in items]; times=[x.get("publish_at") for x in items]
    if len(set(ids)) != len(ids) or len(set(times)) != len(times):
        raise FormatValidationError("content_id and publish_at must be unique")
    counts=Counter()
    for item in items:
        parsed=datetime.fromisoformat(item["publish_at"])
        if parsed.tzinfo is None or not start <= parsed.date() <= end:
            raise FormatValidationError("scheduled item is outside the timezone-aware date range")
        if parsed.strftime("%H:%M") not in slots:
            raise FormatValidationError("scheduled item uses an unknown slot")
        if item.get("status") != "pending":
            raise FormatValidationError("new production schedule items must start pending")
        counts[parsed.date()]+=1
    if set(counts.values()) != {len(slots)} or len(counts) != expected_days:
        raise FormatValidationError("each date must contain every daily quiz slot")
