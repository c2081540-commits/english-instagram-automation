from __future__ import annotations


QUALITY_FIELDS = (
    "object_consistency",
    "action_consistency",
    "state_consistency",
    "pragmatic_consistency",
    "answer_uniqueness",
    "english_knowledge_required",
)
SCENE_FIELDS = ("subject", "addressee", "action", "state", "utterance_reason", "contradiction_check")


class VisualQualityError(ValueError):
    pass


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
