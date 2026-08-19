import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import MASTER_DIR  # noqa: E402
from instagram_automation.answer_renderer import render_answer  # noqa: E402
from instagram_automation.queue import build_queue  # noqa: E402
from instagram_automation.renderer import CANVAS_SIZE, RenderError, render_question  # noqa: E402
from instagram_automation.validation import ValidationError, validate  # noqa: E402


class Phase1Tests(unittest.TestCase):
    def setUp(self):
        self.content = json.loads((MASTER_DIR / "ENG-000001.json").read_text())

    def test_sample_builds_two_slide_queue(self):
        queue = build_queue(MASTER_DIR / "ENG-000001.json")
        self.assertEqual(queue["content_id"], "ENG-000001")
        self.assertEqual([x["role"] for x in queue["carousel"]], ["question", "answer"])

    def test_validation_fail_closed_cases(self):
        mutations = [
            ("content_id", None), ("question", ""), ("choices", ["since"]),
            ("best_answer", "from"), ("answer_type", "unknown"),
            ("publish_at", "tomorrow"), ("visual_description", ""),
        ]
        for field, value in mutations:
            broken = dict(self.content)
            broken[field] = value
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate(broken)

    def test_master_path_cannot_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                build_queue(Path(directory) / "ENG-000001.json")

    def test_three_question_layouts_render_as_png(self):
        for content_id in ("ENG-000002", "ENG-000003", "ENG-000004"):
            with self.subTest(content_id=content_id):
                output = render_question(MASTER_DIR / f"{content_id}.json")
                from PIL import Image
                with Image.open(output) as rendered:
                    self.assertEqual(rendered.size, CANVAS_SIZE)
                    self.assertEqual(rendered.format, "PNG")

    def test_oversized_question_fails_closed(self):
        content = dict(self.content)
        content["question"] = "word " * 1000
        content["visual_required"] = False
        content["choices"] = ["yes", "no"]
        content["best_answer"] = "yes"
        content["acceptable_answers"] = ["yes"]
        temporary = MASTER_DIR / "ENG-999999.json"
        temporary.write_text(json.dumps(content), encoding="utf-8")
        try:
            with self.assertRaises(RenderError):
                render_question(temporary)
        finally:
            temporary.unlink()

    def test_three_answer_templates_render_as_png(self):
        for content_id in ("ENG-000003", "ENG-000002", "ENG-000005"):
            with self.subTest(content_id=content_id):
                output = render_answer(MASTER_DIR / f"{content_id}.json")
                from PIL import Image
                with Image.open(output) as rendered:
                    self.assertEqual(rendered.size, CANVAS_SIZE)
                    self.assertEqual(rendered.format, "PNG")

    def test_oversized_answer_section_fails_closed(self):
        content = json.loads((MASTER_DIR / "ENG-000003.json").read_text())
        content["explanation"] = "長すぎる説明です。" * 500
        temporary = MASTER_DIR / "ENG-999999.json"
        temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaises(RenderError):
                render_answer(temporary)
        finally:
            temporary.unlink()


if __name__ == "__main__":
    unittest.main()
