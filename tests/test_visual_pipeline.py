import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.visual_pipeline import (machine_check_visual,
                                                    validate_visual_review)


class VisualPipelineTests(unittest.TestCase):
    def test_eng_000002_production_source_passes(self):
        master = json.loads((REPO_ROOT / "data" / "master" / "ENG-000002.json").read_text(encoding="utf-8"))
        result = machine_check_visual(master)
        self.assertEqual(result["status"], "PASS")
        self.assertNotIn("placeholder", result["source_image"])

    def test_two_production_visuals_pass_free_checks_and_review(self):
        for content_id in ("ENG-000008", "ENG-000010"):
            master = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text(encoding="utf-8"))
            machine = machine_check_visual(master)
            self.assertEqual(machine["status"], "PASS")
            review = validate_visual_review(machine, {
                "content_id": content_id, "status": "PASS", "reason": None,
            })
            self.assertEqual(review["status"], "PASS")
            self.assertEqual(len(review["checks"]), 4)

    def test_placeholder_fixture_is_rejected_as_production_visual(self):
        master = json.loads((REPO_ROOT / "data" / "master" / "ENG-000008.json").read_text(encoding="utf-8"))
        master["problem_image_path"] = "assets/source/ice-cream-placeholder.png"
        result = machine_check_visual(master)
        self.assertEqual(result["status"], "REJECT")
        self.assertIn("placeholder", result["reason"])


if __name__ == "__main__":
    unittest.main()
