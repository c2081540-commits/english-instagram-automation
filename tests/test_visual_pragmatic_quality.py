import unittest
import json
from pathlib import Path

from instagram_automation.visual_quality import VisualQualityError, validate_visual_quality_gate


def valid_visual():
    return {
        "format": "visual", "visual_required": True,
        "visual_quality_gate": {
            "object_consistency": True, "action_consistency": True,
            "state_consistency": True, "pragmatic_consistency": True,
            "answer_uniqueness": True, "english_knowledge_required": True,
            "scene": {"subject": "a man", "addressee": "none",
                      "action": "points to an empty seat", "state": "the adjacent seat is empty",
                      "utterance_reason": "the question asks what he indicates",
                      "contradiction_check": "no referenced person or state contradicts the answer"},
        },
    }


class VisualPragmaticQualityTests(unittest.TestCase):
    def test_valid_scene_passes(self):
        validate_visual_quality_gate(valid_visual())

    def test_each_quality_dimension_fails_closed(self):
        for field in ("object_consistency", "action_consistency", "state_consistency",
                      "pragmatic_consistency", "answer_uniqueness", "english_knowledge_required"):
            record = valid_visual(); record["visual_quality_gate"][field] = False
            with self.assertRaises(VisualQualityError, msg=field):
                validate_visual_quality_gate(record)

    def test_you_can_sit_here_scene_is_negative_regression(self):
        record = valid_visual()
        record["content_id"] = "ENG-000034"
        record["visual_quality_gate"]["scene"] = {
            "subject": "a standing woman", "addressee": "a seated man",
            "action": "the woman gestures toward the man and chair",
            "state": "the man is already seated",
            "utterance_reason": "the metadata claims she is inviting him to sit",
            "contradiction_check": "You can sit here conflicts with the addressee already sitting",
        }
        record["visual_quality_gate"]["pragmatic_consistency"] = False
        with self.assertRaisesRegex(VisualQualityError, "pragmatic_consistency"):
            validate_visual_quality_gate(record)

    def test_eng_000046_approved_revision_passes(self):
        master = json.loads((Path(__file__).parents[1] / "data/master/ENG-000046.json").read_text())
        validate_visual_quality_gate(master)

    def test_scene_evidence_is_required(self):
        record = valid_visual(); record["visual_quality_gate"]["scene"]["state"] = ""
        with self.assertRaisesRegex(VisualQualityError, "scene evidence"):
            validate_visual_quality_gate(record)


if __name__ == "__main__": unittest.main()
