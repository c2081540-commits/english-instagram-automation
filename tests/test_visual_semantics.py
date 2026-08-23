import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREADS = ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(ROOT / "src"))

from instagram_automation.validation import ValidationError, validate
from instagram_automation.formats import FormatValidationError, validate_format_master


TARGETS = {
    "ENG-000008", "ENG-000010", "ENG-000020", "ENG-000026", "ENG-000027",
    "ENG-000032", "ENG-000034", "ENG-000039", "ENG-000041", "ENG-000044",
    "ENG-000046",
}


class VisualSemanticTests(unittest.TestCase):
    def test_target_visuals_have_complete_semantic_gate(self):
        for content_id in TARGETS:
            master = json.loads((ROOT / "data/master" / f"{content_id}.json").read_text())
            self.assertTrue(master["visual_semantic_consistency"])
            if "___" in master["question"]:
                self.assertEqual(master["visual_semantics"]["completed_sentence"],
                                 master["question"].replace("___", master["best_answer"]))
            else:
                self.assertTrue(master["visual_semantics"]["completed_sentence"].strip())
            validate(master)

    def _canonical_visual(self, question, choices, answer, completed):
        return {"content_id":"ENG-900001","format":"visual","difficulty":"L2",
                "learning_point":"visual meaning","question":question,"choices":choices,
                "correct_answer":answer,"publish_at":"2026-08-24T07:00:00+09:00",
                "english_correctness":True,"unique_answer":True,"explanation":"説明",
                "completed_sentence":completed,"japanese_translation":"訳",
                "threads_reply_explanation":"説明","instagram_caption":"caption",
                "threads_parent_text":"hook","threads_answer_text":"answer",
                "visual_required":True,"visual_semantic_consistency":True,
                "visual_answer_uniqueness":True,"visual_only_solvable":False,
                "visual_semantics":{"subject_gender":"verified","subject_count":"verified",
                "action":"verified","direction":"verified","object":"verified",
                "state":"verified","location":"verified","completed_sentence":completed}}

    def test_question_and_fill_in_visual_contracts(self):
        for question, choices, answer, completed in (
            ("What is she offering to do?", ["open the door","carry the boxes"],
             "carry the boxes", "She is offering to carry the boxes."),
            ("What is he showing her?", ["A ticket","A free seat"],
             "A free seat", "He is showing her a free seat."),
            ("She is walking ___ the stairs.", ["up","down"], "up",
             "She is walking up the stairs.")):
            validate_format_master(self._canonical_visual(question,choices,answer,completed))

    def test_question_visual_semantic_failures_are_closed(self):
        base=self._canonical_visual("What is she offering to do?",
            ["open the door","carry the boxes"],"carry the boxes",
            "She is offering to carry the boxes.")
        bad=dict(base); bad["completed_sentence"]="She is offering to open the door."
        bad["visual_semantics"]=dict(base["visual_semantics"],completed_sentence=bad["completed_sentence"])
        with self.assertRaises(FormatValidationError): validate_format_master(bad)
        for field in ("subject_gender","action","object"):
            bad=dict(base); bad["visual_semantics"]=dict(base["visual_semantics"],**{field:"mismatch"})
            with self.assertRaises(FormatValidationError): validate_format_master(bad)
        bad=dict(base); bad["visual_answer_uniqueness"]=False
        with self.assertRaises(FormatValidationError): validate_format_master(bad)

    def test_gate_fails_closed(self):
        master = json.loads((ROOT / "data/master/ENG-000020.json").read_text())
        master["visual_semantic_consistency"] = False
        with self.assertRaisesRegex(ValidationError, "visual_semantic_consistency"):
            validate(master)
        master = json.loads((ROOT / "data/master/ENG-000020.json").read_text())
        master["visual_semantics"]["completed_sentence"] = "wrong"
        with self.assertRaisesRegex(ValidationError, "completed_sentence"):
            validate(master)

    def test_instagram_threads_content_and_question_images_match(self):
        for content_id in TARGETS:
            ig = json.loads((ROOT / "data/master" / f"{content_id}.json").read_text())
            th = json.loads((THREADS / "data/master/quiz" / f"{content_id}.json").read_text())
            for field in ("question", "choices", "best_answer"):
                self.assertEqual(ig[field], th[field])
            self.assertEqual((ROOT / "artifacts/images" / f"{content_id}-question.png").read_bytes(),
                             (THREADS / "assets/question_images" /
                              f"{content_id}-question.png").read_bytes())


if __name__ == "__main__":
    unittest.main()
