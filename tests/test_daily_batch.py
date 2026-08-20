import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PIL import Image

from instagram_automation.daily_batch import (MAX_REPLACEMENTS,
                                                apply_review_decisions,
                                                build_daily_review_payload,
                                                build_daily_status,
                                                format_daily_dry_run,
                                                validate_daily_batch)
from instagram_automation.paths import MASTER_DIR
from instagram_automation.review import machine_check


class DailyBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.batch_path = REPO_ROOT / "data" / "production" / "daily-2026-08-20.json"
        cls.batch = json.loads(cls.batch_path.read_text(encoding="utf-8"))
        batch_ids = {item["content_id"] for item in cls.batch["quizzes"]} | {cls.batch["normal"]["content_id"]}
        paths = list(MASTER_DIR.glob("ENG-*.json")) + list((MASTER_DIR / "normal").glob("ENG-*.json"))
        cls.existing = [json.loads(path.read_text(encoding="utf-8")) for path in paths
                        if path.stem not in batch_ids]

    def test_six_quizzes_one_normal_and_daily_limits(self):
        validate_daily_batch(self.batch, self.existing)
        counts = {}
        for item in self.batch["quizzes"]:
            counts[item["production_category"]] = counts.get(item["production_category"], 0) + 1
        self.assertEqual(counts, {"grammar_usage": 2, "visual_vocabulary": 1,
                                  "natural_choice": 1, "situation": 2})
        self.assertEqual(sum(item["seasonal"] for item in self.batch["quizzes"]), 1)
        visual = [item for item in self.batch["quizzes"] if item["visual_required"]]
        self.assertEqual(len(visual), 2)
        self.assertEqual({item["production_category"] for item in visual},
                         {"visual_vocabulary", "situation"})

    def test_no_id_or_question_collision(self):
        validate_daily_batch(self.batch, self.existing)
        questions = [item["question"].casefold() for item in self.batch["quizzes"]]
        self.assertEqual(len(questions), len(set(questions)))

    def test_machine_gate_passes_all_quizzes_with_completed_visuals(self):
        status = build_daily_status(self.batch)
        quiz_status = {item["content_id"]: item for item in status["items"]
                       if item["content_type"] == "quiz"}
        self.assertEqual(quiz_status["ENG-000008"]["question_status"], "READY")
        self.assertEqual(quiz_status["ENG-000010"]["question_status"], "READY")
        for content_id in ("ENG-000006", "ENG-000007", "ENG-000008",
                           "ENG-000009", "ENG-000010", "ENG-000011"):
            self.assertEqual(machine_check(MASTER_DIR / f"{content_id}.json").status, "PASS")

    def test_outputs_have_required_image_specs(self):
        for content_id in ("ENG-000006", "ENG-000007", "ENG-000008",
                           "ENG-000009", "ENG-000010", "ENG-000011"):
            for role in ("question", "answer"):
                with Image.open(REPO_ROOT / "artifacts" / "images" / f"{content_id}-{role}.png") as image:
                    self.assertEqual((image.format, image.mode, image.size), ("PNG", "RGB", (1080, 1350)))
        with Image.open(REPO_ROOT / "artifacts" / "stories" / "ENG-100002-story.png") as image:
            self.assertEqual((image.format, image.mode, image.size), ("PNG", "RGB", (1080, 1920)))

    def test_single_review_payload_has_all_seven_items(self):
        payload = build_daily_review_payload(self.batch)
        self.assertTrue(payload["single_batch_review"])
        self.assertTrue(payload["image_review"])
        self.assertIn("挫折者向けとして3〜5秒で理解できるか", payload["checks"])
        self.assertEqual(len(payload["items"]), 7)

    def test_instagram_dry_run_includes_completed_visuals(self):
        text = format_daily_dry_run(build_daily_status(self.batch))
        self.assertIn("ENG-000006", text)
        self.assertIn("ENG-000008", text)
        self.assertNotIn("WAITING_FOR_VISUAL", text)
        self.assertIn("ENG-100002", text)

    def test_sns_length_limits_fail_closed(self):
        cases = [
            ("question", "x" * 71),
            ("choices", ["x" * 26, "short"]),
            ("answer_hint", "あ" * 46),
        ]
        for field, value in cases:
            broken = json.loads(json.dumps(self.batch, ensure_ascii=False))
            broken["quizzes"][0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_daily_batch(broken, self.existing)

    def test_long_situation_question_and_choice_fails_closed(self):
        broken = json.loads(json.dumps(self.batch, ensure_ascii=False))
        item = broken["quizzes"][4]
        item["question"] = "Q" * 65
        item["choices"] = ["A" * 25, "No."]
        item["best_answer"] = item["choices"][0]
        item["acceptable_answers"] = [item["choices"][0]]
        with self.assertRaisesRegex(ValueError, "at-a-glance"):
            validate_daily_batch(broken, self.existing)

    def test_advanced_difficulty_is_not_assumed_to_pass(self):
        broken = json.loads(json.dumps(self.batch, ensure_ascii=False))
        broken["quizzes"][0]["difficulty"] = "advanced"
        with self.assertRaisesRegex(ValueError, "restart-adult"):
            validate_daily_batch(broken, self.existing)

    def test_two_choices_are_allowed(self):
        candidate = json.loads(json.dumps(self.batch, ensure_ascii=False))
        item = candidate["quizzes"][0]
        item["choices"] = ["see", "seeing"]
        item["best_answer"] = "seeing"
        item["acceptable_answers"] = ["seeing"]
        item["question_guide_ja"] = "「また会う」ならどっち？"
        validate_daily_batch(candidate, self.existing)

    def test_visual_question_must_not_repeat_image_context(self):
        broken = json.loads(json.dumps(self.batch, ensure_ascii=False))
        broken["quizzes"][2]["question_repeats_visual"] = True
        with self.assertRaisesRegex(ValueError, "must not repeat"):
            validate_daily_batch(broken, self.existing)

    def test_reject_is_discarded_not_repaired(self):
        decisions = [{"content_id": item["content_id"], "status": "PASS", "reason": None}
                     for item in self.batch["quizzes"]]
        decisions.append({"content_id": self.batch["normal"]["content_id"],
                          "status": "REJECT", "reason": "日本語が不自然"})
        replacement = dict(self.batch["normal"], content_id="ENG-100099", story_headline="別候補")
        result = apply_review_decisions(self.batch, decisions, [replacement])
        self.assertEqual(result["discarded"][0]["content_id"], "ENG-100002")
        self.assertIn(replacement, result["accepted"])
        self.assertNotIn(self.batch["normal"], result["accepted"])

    def test_replacement_limit_fails_closed(self):
        decisions = [{"content_id": item["content_id"], "status": "REJECT", "reason": "reject"}
                     for item in self.batch["quizzes"]]
        decisions.append({"content_id": self.batch["normal"]["content_id"],
                          "status": "PASS", "reason": None})
        with self.assertRaisesRegex(ValueError, "replacement limit"):
            apply_review_decisions(self.batch, decisions, [], MAX_REPLACEMENTS)

    def test_builder_is_cwd_independent(self):
        previous = Path.cwd()
        try:
            os.chdir(tempfile.gettempdir())
            validate_daily_batch(self.batch, self.existing)
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
