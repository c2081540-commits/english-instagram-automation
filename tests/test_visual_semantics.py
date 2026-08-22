import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
THREADS = ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(ROOT / "src"))

from instagram_automation.validation import ValidationError, validate


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
            self.assertEqual(master["visual_semantics"]["completed_sentence"],
                             master["question"].replace("___", master["best_answer"]))
            validate(master)

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
