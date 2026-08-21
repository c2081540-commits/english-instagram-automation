import json
import sys
import unittest
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.difficulty import load_config, validate_distribution  # noqa: E402


class DifficultyLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = json.loads((REPO_ROOT / "artifacts" / "weekly" / "2026-08-20" /
                                "difficulty-level-audit.json").read_text())

    def test_weekly_and_daily_distribution(self):
        report = validate_distribution(self.audit["items"])
        self.assertEqual(report["weekly"], {"L1": 8, "L2": 22, "L3": 12})
        for counts in report["daily"].values():
            self.assertLessEqual(counts["L1"], 2)
            self.assertGreaterEqual(counts["L2"], 3)
            self.assertGreaterEqual(counts["L3"], 1)

    def test_all_unposted_masters_and_queues_have_levels(self):
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            master = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text())
            if queue["status"] == "posted":
                continue
            self.assertIn(queue["difficulty_level"], {"L1", "L2", "L3"})
            self.assertEqual(master["difficulty_level"], queue["difficulty_level"])
            self.assertTrue(master["learning_point"])

    def test_learning_points_do_not_repeat_within_a_day(self):
        by_day = defaultdict(list)
        for number in range(6, 48):
            content_id = f"ENG-{number:06d}"
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            if queue["status"] == "posted":
                continue
            master = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text())
            by_day[queue["publish_at"][:10]].append(master["learning_point"])
        for points in by_day.values():
            self.assertEqual(len(points), len(set(points)))

    def test_config_contains_generation_and_choice_quality_rules(self):
        config = load_config()
        self.assertEqual(config["max_consecutive_same"], 2)
        self.assertEqual(config["weekly_42"]["most_common"], "L2")
        self.assertEqual(config["choice_quality"]["four_choice_weak_distractor_count"], 0)
        self.assertEqual(set(config["hook_pools"]), {"L1", "L2", "L3"})


if __name__ == "__main__":
    unittest.main()
