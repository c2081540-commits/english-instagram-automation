import json
import sys
import unittest
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = REPO_ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(THREADS_ROOT / "src"))

from instagram_automation.validation import ValidationError, validate  # noqa: E402
from instagram_automation.weekly_batch import validate_difficulty_gate  # noqa: E402
from threads_automation.content import build_answer_text  # noqa: E402


REVISED = {8, 10, 11, 16, 17, 20, 22, 23, 26, 27, 29, 32, 34, 39, 40, 41, 44, 46}


class ProductionDifficultyGateTests(unittest.TestCase):
    def unposted(self):
        result = []
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            ig = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            th = json.loads((THREADS_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            if ig["status"] != "posted" and th["status"] != "posted":
                result.append(content_id)
        return result

    def test_all_unposted_are_target_and_not_visual_or_common_sense_only(self):
        items = self.unposted()
        self.assertGreater(len(items), 0)
        for content_id in items:
            master = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text())
            validate(master)
            validate_difficulty_gate(master)
            gate = master["difficulty_gate"]
            self.assertFalse(gate["visual_only_solvable"])
            self.assertFalse(gate["common_sense_only"])
            self.assertGreaterEqual(gate["effective_choice_count"], 2)
            self.assertEqual(gate["weak_distractor_count"], 0)
            self.assertTrue(gate["unique_answer"])
            self.assertEqual(gate["difficulty"], "TARGET")
            if master["visual_required"]:
                self.assertTrue(gate["visual_contributes_to_decision"])

    def test_initial_audit_and_revision_counts(self):
        report = json.loads((REPO_ROOT / "artifacts" / "weekly" / "2026-08-20" /
                             "difficulty-audit.json").read_text())
        self.assertEqual(report["initial_counts"], {"TOO_EASY": 18, "TARGET": 19, "TOO_HARD": 0})
        self.assertEqual(report["final_counts"], {"TOO_EASY": 0, "TARGET": 37, "TOO_HARD": 0})
        self.assertEqual({row["content_id"] for row in report["items"] if row["decision"] == "REVISE"},
                         {f"ENG-{number:06d}" for number in REVISED})

    def test_revised_platform_content_and_question_images_match(self):
        for number in REVISED:
            content_id = f"ENG-{number:06d}"
            instagram = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text())
            threads = json.loads((THREADS_ROOT / "data" / "master" / "quiz" /
                                  f"{content_id}.json").read_text())
            for field in ("question", "choices", "best_answer", "acceptable_answers"):
                self.assertEqual(instagram[field], threads[field])
            self.assertEqual((REPO_ROOT / "artifacts" / "images" /
                              f"{content_id}-question.png").read_bytes(),
                             (THREADS_ROOT / "assets" / "question_images" /
                              f"{content_id}-question.png").read_bytes())
            self.assertEqual(threads["threads_answer_text"], build_answer_text(threads))
            answer_path = REPO_ROOT / "artifacts" / "images" / f"{content_id}-answer.png"
            with Image.open(answer_path) as image:
                self.assertEqual((image.size, image.format, image.mode), ((1080, 1350), "PNG", "RGB"))

    def test_invalid_gate_fails_closed(self):
        master = json.loads((REPO_ROOT / "data" / "master" / "ENG-000026.json").read_text())
        master["difficulty_gate"]["visual_only_solvable"] = True
        with self.assertRaises(ValidationError):
            validate(master)
        master = json.loads((REPO_ROOT / "data" / "master" / "ENG-000026.json").read_text())
        master["difficulty_gate"]["weak_distractor_count"] = 1
        with self.assertRaises(ValidationError):
            validate(master)
        master = json.loads((REPO_ROOT / "data" / "master" / "ENG-000026.json").read_text())
        master["difficulty_gate"]["effective_choice_count"] = 1
        with self.assertRaises(ValidationError):
            validate(master)

    def test_second_pass_uses_four_distinct_learning_points_and_strong_two_choices(self):
        expected = {
            "ENG-000023": (False, "be about to＋動詞"),
            "ENG-000032": (True, "upとup toの使い分け"),
            "ENG-000034": (True, "会話でのyouとIの使い分け"),
            "ENG-000046": (True, "現在進行形の疑問文"),
        }
        for content_id, (visual_required, learning_point) in expected.items():
            master = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text())
            self.assertEqual(len(master["choices"]), 2)
            self.assertEqual(master["difficulty_gate"]["effective_choice_count"], 2)
            self.assertEqual(master["difficulty_gate"]["weak_distractor_count"], 0)
            self.assertEqual(master["visual_required"], visual_required)
            self.assertEqual(master["learning_point"], learning_point)
        self.assertEqual(len({point for _, point in expected.values()}), 4)


if __name__ == "__main__":
    unittest.main()
