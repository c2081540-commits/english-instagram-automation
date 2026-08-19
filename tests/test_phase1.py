import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.paths import MASTER_DIR  # noqa: E402
from instagram_automation.answer_renderer import STYLES, render_answer  # noqa: E402
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
        content["answer_hint"] = "長すぎるヒントです。" * 500
        temporary = MASTER_DIR / "ENG-999999.json"
        temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaises(RenderError):
                render_answer(temporary)
        finally:
            temporary.unlink()

    def test_answer_box_backgrounds_are_white(self):
        self.assertTrue(all(style["background"] == "#FFFFFF" for style in STYLES.values()))

    def test_answer_hint_cannot_reveal_best_answer(self):
        content = json.loads((MASTER_DIR / "ENG-000003.json").read_text())
        content["answer_hint"] = "The answer is for."
        temporary = MASTER_DIR / "ENG-999999.json"
        temporary.write_text(json.dumps(content, ensure_ascii=False), encoding="utf-8")
        try:
            with self.assertRaises(RenderError):
                render_answer(temporary)
        finally:
            temporary.unlink()

    def test_unapproved_answer_hint_uses_generic_fallback(self):
        from instagram_automation.answer_renderer import GENERIC_HINT, _top_section
        content = json.loads((MASTER_DIR / "ENG-000003.json").read_text())
        content["answer_hint_approved"] = False
        content["answer_hint"] = ""
        self.assertEqual(_top_section(content), ("hint", GENERIC_HINT))

    def test_answer_hint_rejects_leading_phrases(self):
        from instagram_automation.answer_renderer import _top_section
        content = json.loads((MASTER_DIR / "ENG-000003.json").read_text())
        content["answer_hint"] = "期間に使う前置詞を選びます。"
        with self.assertRaises(RenderError):
            _top_section(content)

    def test_answer_labels_and_choice_prefix(self):
        from instagram_automation.answer_renderer import HEADINGS, _answer_text
        self.assertEqual(
            {key: HEADINGS[key] for key in ("hint", "point", "answer", "meaning", "example", "difference", "also_natural")},
            {"hint": "ヒント", "point": "ポイント", "answer": "答え", "meaning": "意味",
             "example": "例文", "difference": "使い分け", "also_natural": "こんな言い方も"},
        )
        content = json.loads((MASTER_DIR / "ENG-000003.json").read_text())
        self.assertEqual(_answer_text(content), "B. for")


if __name__ == "__main__":
    unittest.main()
