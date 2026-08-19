import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from PIL import Image  # noqa: E402

from instagram_automation.paths import (NORMAL_MASTER_DIR, STORY_IMAGE_DIR,
                                         THREADS_NORMAL_MASTER_DIR)  # noqa: E402
from instagram_automation.renderer import RenderError  # noqa: E402
from instagram_automation.story_renderer import (CANVAS_SIZE, load_story_master,
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


if __name__ == "__main__":
    unittest.main()
