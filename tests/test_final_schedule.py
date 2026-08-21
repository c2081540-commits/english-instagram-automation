import json
import sys
import unittest
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.queue import validate_queue_state
from instagram_automation.schedule import (load_schedule_config, should_execute,
                                             validate_schedule_items)


class FinalInstagramScheduleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_schedule_config()
        cls.schedule = json.loads((REPO_ROOT / "data" / "production" /
                                   "final-schedule-2026-08-20.json").read_text(encoding="utf-8"))
        cls.queues = [json.loads((REPO_ROOT / "data" / "queue" /
                                 f"{item['content_id']}.json").read_text(encoding="utf-8"))
                      for item in cls.schedule["items"]]

    def test_config_and_seven_daily_slots(self):
        self.assertEqual(self.config["quiz_slots"], ["07:00", "09:30", "12:00", "15:00", "18:00", "20:30"])
        self.assertEqual(self.config["normal_slot"], "22:30")
        self.assertEqual(self.schedule["timezone"], "Asia/Tokyo")
        validate_schedule_items(self.schedule["items"])

    def test_all_49_queues_are_trackable_and_known_post_is_reconciled(self):
        self.assertEqual(len(self.queues), 49)
        for queue in self.queues:
            validate_queue_state(queue)
            for field in ("content_id", "platform", "publish_at", "status"):
                self.assertIn(field, queue)
        posted = [queue for queue in self.queues if queue["status"] == "posted"]
        self.assertEqual([queue["content_id"] for queue in posted],
                         ["ENG-000009", "ENG-000012", "ENG-000013", "ENG-000014", "ENG-000015"])
        self.assertTrue(posted[0]["remote_post_id"])
        self.assertEqual(sum(queue["status"] == "pending" for queue in self.queues), 44)

    def test_carousel_order_and_story_slot(self):
        quizzes = [queue for queue in self.queues if queue["content_type"] == "quiz"]
        normals = [queue for queue in self.queues if queue["content_type"] == "normal"]
        self.assertEqual((len(quizzes), len(normals)), (42, 7))
        self.assertTrue(all([(slide["order"], slide["role"]) for slide in queue["carousel"]] ==
                            [(1, "question"), (2, "answer")] for queue in quizzes))
        self.assertTrue(all(datetime.fromisoformat(queue["publish_at"]).strftime("%H:%M") == "22:30"
                            for queue in normals))

    def test_past_slots_are_held_without_rescheduling(self):
        held = [queue for queue in self.queues if queue["execution_eligibility"] == "past_due_hold"]
        self.assertEqual([queue["content_id"] for queue in held],
                         ["ENG-000006", "ENG-000007", "ENG-000008", "ENG-000010", "ENG-000011",
                          "ENG-100002"])
        self.assertTrue(all(queue["publish_at"].startswith("2026-08-20T") for queue in held))

    def test_posted_is_never_selected_for_repost(self):
        queue = dict(self.queues[3], status="posted", execution_eligibility="scheduled")
        self.assertFalse(should_execute(queue, datetime.fromisoformat("2026-08-21T00:00:00+09:00")))


if __name__ == "__main__":
    unittest.main()
