import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import (MASTER_DIR, REVIEW_DECISION_DIR, REVIEW_PAYLOAD_DIR,
                                         REVIEW_RESULT_DIR)  # noqa: E402
from instagram_automation.review import (build_review_batch, check_platform_consistency,
                                          machine_check, validate_decisions,
                                          write_review_results)  # noqa: E402


class ReviewTests(unittest.TestCase):
    def _content(self, content_id: str) -> dict:
        return json.loads((MASTER_DIR / f"{content_id}.json").read_text(encoding="utf-8"))

    def _check_mutation(self, content: dict):
        temporary = MASTER_DIR / "ENG-999999.json"
        content["content_id"] = "ENG-999999"
        temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        try:
            return machine_check(temporary)
        finally:
            temporary.unlink()

    def test_current_three_pass_machine_checks_and_batch_together(self):
        results = [machine_check(MASTER_DIR / f"{content_id}.json")
                   for content_id in ("ENG-000002", "ENG-000003", "ENG-000005")]
        self.assertEqual([result.status for result in results], ["PASS", "PASS", "PASS"])
        batch = build_review_batch(results)
        self.assertEqual(len(batch["items"]), 3)
        self.assertTrue(batch["items"][0]["review_scope"]["image"])
        self.assertIsNotNone(batch["items"][0]["image"])
        self.assertFalse(batch["items"][1]["review_scope"]["image"])
        self.assertIsNone(batch["items"][1]["image"])
        self.assertTrue(batch["review_policy"]["single_pass"])
        self.assertFalse(batch["review_policy"]["allow_repair"])

    def test_rejects_best_answer_outside_choices(self):
        content = self._content("ENG-000003")
        content["best_answer"] = "outside"
        result = self._check_mutation(content)
        self.assertEqual(result.status, "REJECT")
        self.assertIn("best_answer", result.reason)

    def test_rejects_missing_required_field(self):
        content = self._content("ENG-000003")
        del content["question"]
        result = self._check_mutation(content)
        self.assertEqual(result.status, "REJECT")
        self.assertIn("missing fields", result.reason)

    def test_rejects_length_overflow(self):
        content = self._content("ENG-000003")
        content["question"] = "x" * 181
        result = self._check_mutation(content)
        self.assertEqual(result.status, "REJECT")
        self.assertIn("exceeds 180", result.reason)

    def test_rejects_missing_required_source_image(self):
        content = self._content("ENG-000002")
        content["problem_image_path"] = "assets/source/does-not-exist.png"
        content["visual_semantic_consistency"] = True
        content["visual_semantics"] = {
            "subject_gender": "none", "subject_count": 0, "action": "melting",
            "direction": None, "object": "ice cream", "state": "partly melted",
            "location": "outdoors",
            "completed_sentence": content["question"].replace("___", content["best_answer"]),
        }
        result = self._check_mutation(content)
        self.assertEqual(result.status, "REJECT")
        self.assertIn("problem image not found", result.reason)

    def test_platform_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "best_answer mismatch"):
            check_platform_consistency({
                "instagram": {"content_id": "ENG-000003", "best_answer": "for"},
                "threads": {"content_id": "ENG-000003", "best_answer": "since"},
            })

    def test_compact_pass_and_reject_decisions(self):
        batch = {"items": [{"content_id": "ENG-000002"}, {"content_id": "ENG-000003"}]}
        decisions = validate_decisions(batch, [
            {"content_id": "ENG-000002", "status": "PASS", "reason": None},
            {"content_id": "ENG-000003", "status": "REJECT", "reason": "選択肢Bも成立する"},
        ])
        self.assertEqual(decisions[0], {"content_id": "ENG-000002", "status": "PASS", "reason": None})
        self.assertEqual(decisions[1]["reason"], "選択肢Bも成立する")

    def test_reject_requires_reason_and_never_repairs(self):
        batch = {"items": [{"content_id": "ENG-000002"}]}
        with self.assertRaisesRegex(ValueError, "requires a concise reason"):
            validate_decisions(batch, [{"content_id": "ENG-000002", "status": "REJECT", "reason": None}])

    def test_reject_reason_is_saved_compactly(self):
        batch_path = REVIEW_PAYLOAD_DIR / "test-batch.json"
        decision_path = REVIEW_DECISION_DIR / "test-decisions.json"
        result_path = REVIEW_RESULT_DIR / "ENG-999998.json"
        REVIEW_PAYLOAD_DIR.mkdir(parents=True, exist_ok=True)
        REVIEW_DECISION_DIR.mkdir(parents=True, exist_ok=True)
        batch_path.write_text(json.dumps({"items": [{"content_id": "ENG-999998"}]}), encoding="utf-8")
        decision_path.write_text(json.dumps({"results": [
            {"content_id": "ENG-999998", "status": "REJECT", "reason": "正答に重大な疑義がある"}
        ]}, ensure_ascii=False), encoding="utf-8")
        try:
            self.assertEqual(write_review_results(batch_path, decision_path), [result_path])
            self.assertEqual(json.loads(result_path.read_text(encoding="utf-8")), {
                "content_id": "ENG-999998", "status": "REJECT", "reason": "正答に重大な疑義がある"
            })
        finally:
            for path in (batch_path, decision_path, result_path):
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
