import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PIL import Image  # noqa: E402

from instagram_automation.paths import (NORMAL_MASTER_DIR, STORY_CHARACTER_PATH,
                                         STORY_IMAGE_DIR, THREADS_NORMAL_MASTER_DIR)  # noqa: E402
from instagram_automation.renderer import RenderError  # noqa: E402
from instagram_automation.story_renderer import (CANVAS_SIZE, character_placement,
                                                   load_character, load_story_master,
                                                   render_story,
                                                   validate_story_master)  # noqa: E402


class StoryRendererTests(unittest.TestCase):
    def test_eng_100001_renders_rgb_png(self):
        output = render_story(NORMAL_MASTER_DIR / "ENG-100001.json")
        self.assertEqual(output, STORY_IMAGE_DIR / "ENG-100001-story.png")
        with Image.open(output) as image:
            self.assertEqual(image.size, CANVAS_SIZE)
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.mode, "RGB")

    def test_threads_normal_master_matches_exactly(self):
        local = json.loads((NORMAL_MASTER_DIR / "ENG-100001.json").read_text(encoding="utf-8"))
        threads = json.loads((THREADS_NORMAL_MASTER_DIR / "ENG-100001.json").read_text(encoding="utf-8"))
        self.assertEqual(local, threads)
        self.assertEqual(load_story_master(NORMAL_MASTER_DIR / "ENG-100001.json")["content_id"], "ENG-100001")
        self.assertEqual(local["story_headline"], "今日、英語を勉強できなかった人へ。")
        self.assertIn("それだけでも「英語に触れた日」になります。", local["story_body"])

    def test_content_mismatch_fails_closed(self):
        local = json.loads((NORMAL_MASTER_DIR / "ENG-100001.json").read_text(encoding="utf-8"))
        threads = dict(local)
        threads["story_headline"] = "異なる見出し"
        with self.assertRaisesRegex(RenderError, "mismatch"):
            validate_story_master(local, threads)

    def test_story_text_overflow_fails_closed(self):
        local = json.loads((NORMAL_MASTER_DIR / "ENG-100001.json").read_text(encoding="utf-8"))
        local["story_body"] = "長い本文" * 100
        with self.assertRaisesRegex(RenderError, "exceeds 280"):
            validate_story_master(local, dict(local))

    def test_script_is_cwd_independent(self):
        script = REPO_ROOT / "scripts" / "render_story.py"
        result = subprocess.run([sys.executable, str(script), "ENG-100001"], cwd="/private/tmp",
                                check=True, capture_output=True, text=True)
        self.assertIn("ENG-100001-story.png", result.stdout)

    def test_fixed_character_is_lower_right_without_overlap(self):
        self.assertTrue(STORY_CHARACTER_PATH.is_file())
        with Image.open(STORY_CHARACTER_PATH) as source:
            box = character_placement(source.size)
            self.assertEqual(box[3], 350)
            self.assertAlmostEqual(box[2] / box[3], source.width / source.height, places=2)
        self.assertGreaterEqual(box[0], 500)
        self.assertGreaterEqual(box[1], 1420)
        self.assertLessEqual(box[0] + box[2], 1000)
        self.assertLessEqual(box[1] + box[3], 1780)
        output = render_story(NORMAL_MASTER_DIR / "ENG-100001.json")
        with Image.open(output) as rendered:
            colors = rendered.crop((box[0], box[1], box[0] + box[2], box[1] + box[3])).getcolors(maxcolors=1000000)
            self.assertIsNotNone(colors)
            self.assertGreater(len(colors), 100)

    def test_missing_character_keeps_text_only_renderer_available(self):
        self.assertIsNone(load_character(REPO_ROOT / "assets" / "character" / "missing.png"))


if __name__ == "__main__":
    unittest.main()
