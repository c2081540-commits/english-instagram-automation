import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PIL import Image

from instagram_automation.weekly_batch import (TARGET_CATEGORIES,
                                                TARGET_DIFFICULTIES,
                                                validate_weekly_batch)


class WeeklyBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.week = json.loads((REPO_ROOT / "data" / "production" / "week-2026-08-20.json").read_text(encoding="utf-8"))
        cls.report = json.loads((REPO_ROOT / "data" / "production" / "week-2026-08-20-report.json").read_text(encoding="utf-8"))
        ids = {item["content_id"] for item in cls.week["quizzes"] + cls.week["normals"]}
        paths = list((REPO_ROOT / "data" / "master").glob("ENG-*.json"))
        paths += list((REPO_ROOT / "data" / "master" / "normal").glob("ENG-*.json"))
        cls.existing = [json.loads(path.read_text(encoding="utf-8")) for path in paths if path.stem not in ids]

    def test_weekly_totals_and_distributions(self):
        report = validate_weekly_batch(self.week, self.existing)
        self.assertEqual(report["quiz_total"], 42)
        self.assertEqual(report["normal_total"], 7)
        self.assertEqual(report["categories"], TARGET_CATEGORIES)
        self.assertEqual(report["difficulties"], TARGET_DIFFICULTIES)
        self.assertEqual(sum(report["choice_counts"].values()), 42)
        self.assertTrue(set(map(int, report["choice_counts"])).issubset({2, 4}))
        self.assertEqual(report["visual_required"], 13)
        self.assertEqual(report["seasonal"], 6)

    def test_no_duplicate_questions_examples_hints_or_normal_themes(self):
        validate_weekly_batch(self.week, self.existing)

    def test_situation_purposes_and_normal_categories_are_diverse(self):
        report = validate_weekly_batch(self.week, self.existing)
        self.assertLessEqual(report["short_affirmative_situations"], 5)
        self.assertLessEqual(max(report["situation_purposes"].values()), 2)
        self.assertGreaterEqual(len(report["normal_categories"]), 4)

    def test_week_rejects_affirmative_response_overconcentration(self):
        week = json.loads(json.dumps(self.week))
        situations = [item for item in week["quizzes"] if item["production_category"] == "situation"]
        for index, item in enumerate(situations[:6]):
            item["situation_purpose"] = f"distinct_{index}"
            item["response_family"] = "short_affirmative_response"
        with self.assertRaisesRegex(ValueError, "affirmative"):
            validate_weekly_batch(week, self.existing)

    def test_short_grammar_point_is_supported(self):
        points = [item["answer_point"] for item in self.week["quizzes"] if item.get("answer_point")]
        self.assertTrue(points)
        self.assertTrue(all("\n" not in point and len(point) <= 40 for point in points))

    def test_ready_and_waiting_visual_outputs(self):
        visual = [item for item in self.week["quizzes"] if item["visual_required"]]
        ready = [item for item in visual if item.get("problem_image_path")]
        waiting = [item for item in visual if not item.get("problem_image_path")]
        self.assertEqual(len(ready), 13)
        self.assertEqual(len(waiting), 0)
        for item in ready:
            self.assertTrue((REPO_ROOT / "artifacts" / "images" / f"{item['content_id']}-question.png").is_file())
        for item in waiting:
            self.assertFalse((REPO_ROOT / "artifacts" / "images" / f"{item['content_id']}-question.png").exists())

    def test_all_answers_nonvisual_questions_and_stories_rendered(self):
        for item in self.week["quizzes"]:
            paths = [REPO_ROOT / "artifacts" / "images" / f"{item['content_id']}-answer.png"]
            if not item["visual_required"]:
                paths.append(REPO_ROOT / "artifacts" / "images" / f"{item['content_id']}-question.png")
            for path in paths:
                with Image.open(path) as image:
                    self.assertEqual((image.format, image.mode, image.size), ("PNG", "RGB", (1080, 1350)))
        for item in self.week["normals"]:
            with Image.open(REPO_ROOT / "artifacts" / "stories" / f"{item['content_id']}-story.png") as image:
                self.assertEqual((image.format, image.mode, image.size), ("PNG", "RGB", (1080, 1920)))

    def test_visual_questions_support_two_and_four_choices(self):
        counts = {len(item["choices"]) for item in self.week["quizzes"] if item["visual_required"]}
        self.assertEqual(counts, {2, 4})

    def test_single_review_payload_has_49_items(self):
        payload = json.loads((REPO_ROOT / "data" / "review" / "payloads" / "week-2026-08-20.json").read_text(encoding="utf-8"))
        self.assertTrue(payload["single_batch_review"])
        self.assertEqual(len(payload["items"]), 49)
        pending = [item for item in payload["items"]
                   if item.get("visual") and item["visual"].get("status") == "PENDING"]
        self.assertEqual(len(pending), 0)

    def test_single_visual_review_passes_all_fourteen_assets(self):
        review = json.loads((REPO_ROOT / "data" / "review" / "results" /
                             "week-2026-08-20-visual.json").read_text(encoding="utf-8"))
        self.assertEqual(review["review_mode"], "single_batch")
        self.assertEqual(len(review["results"]), 14)
        self.assertTrue(all(item["status"] == "PASS" for item in review["results"]))


if __name__ == "__main__":
    unittest.main()
