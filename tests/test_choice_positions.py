import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THREADS_ROOT = REPO_ROOT.parent / "english-threads-automation"
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.choice_positions import (  # noqa: E402
    assign_balanced_positions,
    correct_position,
    max_same_position_streak,
    position_report,
    validate_position_distribution,
)


class ChoicePositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = [json.loads((REPO_ROOT / "data" / "master" /
                                f"ENG-{number:06d}.json").read_text(encoding="utf-8"))
                     for number in range(6, 48)]

    def test_future_batch_assignment_is_balanced(self):
        balanced = assign_balanced_positions(self.items)
        report = validate_position_distribution(balanced)
        self.assertLessEqual(abs(report["distribution"]["2"]["A"] -
                                 report["distribution"]["2"]["B"]), 1)
        four = report["distribution"]["4"].values()
        self.assertLessEqual(max(four) - min(four), 1)
        self.assertLessEqual(report["max_same_position_streak"], 2)

    def test_assignment_does_not_use_difficulty(self):
        changed_difficulty = deepcopy(self.items)
        for index, item in enumerate(changed_difficulty):
            item["difficulty"] = f"unrelated-{index}"
            item["difficulty_level"] = f"unrelated-{41-index}"
        first = assign_balanced_positions(self.items)
        second = assign_balanced_positions(changed_difficulty)
        self.assertEqual([correct_position(item) for item in first],
                         [correct_position(item) for item in second])

    def test_current_unposted_sequence_has_no_three_position_streak(self):
        unposted = []
        for item in self.items:
            content_id = item["content_id"]
            ig_queue = json.loads((REPO_ROOT / "data" / "queue" /
                                   f"{content_id}.json").read_text(encoding="utf-8"))
            threads_queue = json.loads((THREADS_ROOT / "data" / "queue" /
                                        f"{content_id}.json").read_text(encoding="utf-8"))
            if ig_queue["status"] != "posted" and threads_queue["status"] != "posted":
                unposted.append(item)
        self.assertLessEqual(max_same_position_streak(unposted), 2)
        report = position_report(unposted)["distribution"]
        self.assertLessEqual(abs(report["2"]["A"] - report["2"]["B"]), 1)
        # Posted items leave this legacy window over time; keep the approved maximum bias cap
        # without pinning the test to yesterday's exact set of unposted records.
        self.assertLessEqual(max(report["4"].values()) - min(report["4"].values()), 4)

    def test_platform_choices_answers_and_question_images_match(self):
        for item in self.items:
            content_id = item["content_id"]
            threads = json.loads((THREADS_ROOT / "data" / "master" / "quiz" /
                                  f"{content_id}.json").read_text(encoding="utf-8"))
            self.assertEqual(item["choices"], threads["choices"])
            self.assertEqual(item["best_answer"], threads["best_answer"])
            self.assertEqual(
                (REPO_ROOT / "artifacts" / "images" /
                 f"{content_id}-question.png").read_bytes(),
                (THREADS_ROOT / "assets" / "question_images" /
                 f"{content_id}-question.png").read_bytes())


if __name__ == "__main__":
    unittest.main()
