from __future__ import annotations

import re


QUALITY_FIELDS = (
    "object_consistency",
    "action_consistency",
    "state_consistency",
    "pragmatic_consistency",
    "answer_uniqueness",
    "english_knowledge_required",
)
SCENE_FIELDS = ("subject", "addressee", "action", "state", "utterance_reason", "contradiction_check")
REASONING_EXPECTED = {
    "image_only_solvable": False,
    "text_only_solvable": False,
    "noun_object_leak": False,
    "action_state_ambiguity": False,
    "correct_answer_visually_supported": True,
    "answer_uniqueness": True,
    "pragmatic_consistency": True,
    "elimination_only": False,
}


class VisualQualityError(ValueError):
    pass


def validate_visual_learning_value(record: dict) -> None:
    if record.get("format") != "visual" or record.get("visual_required") is not True:
        return
    value = record.get("learning_value")
    if value not in {"high", "standard", "low"}:
        raise VisualQualityError("learning_value must be high, standard, or low")
    if not isinstance(record.get("learning_value_reason"), str) or not record["learning_value_reason"].strip():
        raise VisualQualityError("learning_value_reason is required")


def validate_visual_learning_value_mix(records: list[dict], *, max_low: int = 1) -> None:
    visuals = [record for record in records if record.get("format") == "visual" and record.get("visual_required") is True]
    for record in visuals:
        validate_visual_learning_value(record)
    low = [record.get("content_id") for record in visuals if record.get("learning_value") == "low"]
    if len(low) > max_low:
        raise VisualQualityError(f"too many low-learning-value Visuals: {low}")


def _words(value: str) -> set[str]:
    words = set(re.findall(r"[a-z]+", value.casefold()))
    normalized = set(words)
    for word in words:
        if word.endswith("ies") and len(word) > 3:
            normalized.add(word[:-3] + "y")
        elif word.endswith("es") and len(word) > 3:
            normalized.add(word[:-2])
        elif word.endswith("s") and len(word) > 2:
            normalized.add(word[:-1])
    return normalized


def validate_visual_object_leak(record: dict) -> None:
    """Mechanically compare reviewed scene objects with every choice."""
    if record.get("format") != "visual" or record.get("visual_required") is not True:
        return
    audit = record.get("object_noun_leak_check")
    if not isinstance(audit, dict):
        raise VisualQualityError("object_noun_leak_check is required for Visual v2 candidates")
    objects = audit.get("salient_object_terms")
    if not isinstance(objects, list) or not objects or any(not isinstance(x, str) or not x.strip() for x in objects):
        raise VisualQualityError("salient_object_terms must be a non-empty string list")
    choices = record.get("choices")
    if not isinstance(choices, list) or len(choices) not in {2, 4}:
        raise VisualQualityError("Visual choices must contain 2 or 4 items")
    correct = record.get("best_answer") or record.get("correct_answer")
    if choices.count(correct) != 1:
        raise VisualQualityError("Visual correct answer must occur exactly once")
    object_words = set().union(*(_words(x) for x in objects))
    hits = [sorted(_words(choice) & object_words) for choice in choices]
    correct_index = choices.index(correct)
    if hits[correct_index] and all(not hit for i, hit in enumerate(hits) if i != correct_index):
        raise VisualQualityError(
            f"OBJECT_NOUN_LEAK: correct choice alone names salient object(s): {hits[correct_index]}"
        )
    if audit.get("question_hidden_answerable_without_english") is not False:
        raise VisualQualityError("question-hidden solvability must be explicitly rejected")
    if audit.get("verbs_hidden_answerable_from_nouns") is not False:
        raise VisualQualityError("noun-only solvability must be explicitly rejected")
    if not isinstance(audit.get("reason"), str) or not audit["reason"].strip():
        raise VisualQualityError("object/noun leak reason is required")


def validate_visual_reasoning_gate(record: dict) -> None:
    """Require image + English, positive visual support, and a unique answer."""
    if record.get("format") != "visual" or record.get("visual_required") is not True:
        return
    gate = record.get("visual_reasoning_gate")
    if not isinstance(gate, dict):
        raise VisualQualityError("visual_reasoning_gate is required for Visual v2 candidates")
    missing = set(REASONING_EXPECTED) - set(gate)
    if missing:
        raise VisualQualityError(f"visual reasoning fields missing: {sorted(missing)}")
    failed = [name for name, expected in REASONING_EXPECTED.items() if gate.get(name) is not expected]
    if failed:
        raise VisualQualityError(f"visual reasoning gate failed: {failed}")
    evidence = gate.get("evidence")
    required_evidence = ("image_dependency", "english_dependency", "positive_support", "uniqueness", "pragmatics")
    if not isinstance(evidence, dict):
        raise VisualQualityError("visual reasoning evidence is required")
    empty = [name for name in required_evidence if not isinstance(evidence.get(name), str) or not evidence[name].strip()]
    if empty:
        raise VisualQualityError(f"visual reasoning evidence missing: {empty}")


def validate_visual_quality_gate(record: dict) -> None:
    """Validate the human-reviewed scene contract for a Visual candidate.

    This gate is used before production promotion. It deliberately requires review
    evidence because object presence alone cannot prove pragmatic naturalness.
    """
    if record.get("format") != "visual" or record.get("visual_required") is not True:
        return
    gate = record.get("visual_quality_gate")
    if not isinstance(gate, dict):
        raise VisualQualityError("visual_quality_gate is required for Visual production candidates")
    missing = set(QUALITY_FIELDS) - set(gate)
    if missing:
        raise VisualQualityError(f"visual quality fields missing: {sorted(missing)}")
    failed = [field for field in QUALITY_FIELDS if gate.get(field) is not True]
    if failed:
        raise VisualQualityError(f"visual quality gate failed: {failed}")
    scene = gate.get("scene")
    if not isinstance(scene, dict):
        raise VisualQualityError("visual quality scene review is required")
    empty = [field for field in SCENE_FIELDS if not isinstance(scene.get(field), str) or not scene[field].strip()]
    if empty:
        raise VisualQualityError(f"visual scene evidence missing: {empty}")


def validate_visual_candidate(record: dict) -> None:
    """Validate a newly produced Visual with the complete v2 contract.

    Historical/current reservations keep their immutable contract.  New review
    candidates must use this entry point, which never trusts the boolean
    ``english_knowledge_required`` without the choice/object comparison.
    """
    validate_visual_quality_gate(record)
    validate_visual_object_leak(record)
    validate_visual_reasoning_gate(record)
    validate_visual_learning_value(record)
