import unittest
import json
from pathlib import Path

from instagram_automation.visual_quality import (
    VisualQualityError, validate_visual_candidate, validate_visual_object_leak,
    validate_visual_learning_value_mix, validate_visual_quality_gate,
    validate_visual_reasoning_gate,
)


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

    def test_eng_000041_object_noun_leak_is_negative_regression(self):
        record = {
            "content_id": "ENG-000041", "format": "visual", "visual_required": True,
            "question": "What is she offering to do?",
            "choices": ["open the door", "make coffee", "call a taxi", "carry the boxes"],
            "best_answer": "carry the boxes",
            "object_noun_leak_check": {
                "salient_object_terms": ["box", "boxes"],
                "question_hidden_answerable_without_english": True,
                "verbs_hidden_answerable_from_nouns": True,
                "reason": "Only the correct choice names the boxes visible in the image.",
            },
        }
        with self.assertRaisesRegex(VisualQualityError, "OBJECT_NOUN_LEAK"):
            validate_visual_object_leak(record)

    def test_same_scene_object_in_all_choices_avoids_noun_leak(self):
        record = {
            "format": "visual", "visual_required": True,
            "choices": ["open the boxes", "label the boxes", "count the boxes", "carry the boxes"],
            "best_answer": "carry the boxes",
            "object_noun_leak_check": {
                "salient_object_terms": ["box", "boxes"],
                "question_hidden_answerable_without_english": False,
                "verbs_hidden_answerable_from_nouns": False,
                "reason": "Every choice names boxes, so the action verb must be understood.",
            },
        }
        validate_visual_object_leak(record)

    def test_eng_000046_object_noun_leak_is_negative_regression(self):
        record = {
            "content_id": "ENG-000046", "format": "visual", "visual_required": True,
            "question": "What is he showing?",
            "choices": ["a train ticket", "a free seat"],
            "best_answer": "a free seat",
            "object_noun_leak_check": {
                "salient_object_terms": ["seat"],
                "question_hidden_answerable_without_english": True,
                "verbs_hidden_answerable_from_nouns": True,
                "reason": "Only the correct choice names the visible empty seat.",
            },
        }
        with self.assertRaisesRegex(VisualQualityError, "OBJECT_NOUN_LEAK"):
            validate_visual_object_leak(record)

    def test_new_visual_candidate_requires_object_noun_audit(self):
        with self.assertRaisesRegex(VisualQualityError, "object_noun_leak_check"):
            validate_visual_candidate(valid_visual())

    def test_reasoning_gate_requires_image_and_english_with_positive_support(self):
        record = {"format": "visual", "visual_required": True, "visual_reasoning_gate": {
            "image_only_solvable": False, "text_only_solvable": False,
            "noun_object_leak": False, "action_state_ambiguity": False,
            "correct_answer_visually_supported": True, "answer_uniqueness": True,
            "pragmatic_consistency": True, "elimination_only": False,
            "evidence": {"image_dependency": "The state comes from the image.",
                         "english_dependency": "The adjective meanings must be understood.",
                         "positive_support": "The visible empty seat supports available.",
                         "uniqueness": "The seat cannot be both occupied and available.",
                         "pragmatics": "Describing an empty seat as available is natural."},
        }}
        validate_visual_reasoning_gate(record)
        record["visual_reasoning_gate"]["elimination_only"] = True
        with self.assertRaisesRegex(VisualQualityError, "elimination_only"):
            validate_visual_reasoning_gate(record)

    def test_positive_visual_support_is_mandatory(self):
        record = {"format": "visual", "visual_required": True, "visual_reasoning_gate": {
            **{name: value for name, value in {
                "image_only_solvable": False, "text_only_solvable": False,
                "noun_object_leak": False, "action_state_ambiguity": False,
                "correct_answer_visually_supported": False, "answer_uniqueness": True,
                "pragmatic_consistency": True, "elimination_only": False}.items()},
            "evidence": {"image_dependency": "x", "english_dependency": "x", "positive_support": "x",
                         "uniqueness": "x", "pragmatics": "x"},
        }}
        with self.assertRaisesRegex(VisualQualityError, "correct_answer_visually_supported"):
            validate_visual_reasoning_gate(record)

    def test_low_learning_value_is_recorded_and_limited(self):
        low = {"content_id": "ENG-LOW", "format": "visual", "visual_required": True,
               "learning_value": "low", "learning_value_reason": "Only basic number-word recognition."}
        validate_visual_learning_value_mix([low], max_low=1)
        with self.assertRaisesRegex(VisualQualityError, "too many low-learning-value"):
            validate_visual_learning_value_mix([low, {**low, "content_id": "ENG-LOW-2"}], max_low=1)


if __name__ == "__main__": unittest.main()
