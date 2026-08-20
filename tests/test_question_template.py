import json
import sys
import unittest
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.validation import ValidationError, validate  # noqa: E402


class FinalQuestionTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.week = json.loads((REPO_ROOT / "data" / "production" /
                               "week-2026-08-20.json").read_text(encoding="utf-8"))

    def test_visual_flag_selects_exactly_one_template_contract(self):
        text = [item for item in self.week["quizzes"] if not item["visual_required"]]
        visual = [item for item in self.week["quizzes"] if item["visual_required"]]
        self.assertEqual((len(text), len(visual)), (28, 14))
        self.assertTrue(all(item["question_guide_ja"] for item in text))
        self.assertTrue(all(item.get("question_guide_ja") is None for item in visual))
        self.assertEqual(sum(item["question_role"] == "learning_sentence" for item in text), 26)
        self.assertEqual(sum(item["question_role"] == "meta_instruction" for item in text), 2)
        self.assertTrue(all(item.get("question_role") is None for item in visual))

    def test_all_text_guides_are_fixed_one_line_and_choice_aware(self):
        for item in self.week["quizzes"]:
            validate(item)
            guide = item.get("question_guide_ja")
            if item["visual_required"]:
                continue
            self.assertLessEqual(len(guide), 30)
            self.assertNotIn("\n", guide)
            if len(item["choices"]) == 2:
                self.assertNotIn("どれ？", guide)
            if len(item["choices"]) == 4:
                self.assertNotIn("どっち？", guide)

    def test_wrong_template_and_choice_word_fail_closed(self):
        text = next(item for item in self.week["quizzes"] if not item["visual_required"])
        broken = dict(text, question_guide_ja=None)
        with self.assertRaises(ValidationError):
            validate(broken)

    def test_meta_instruction_is_not_displayed_as_learning_english(self):
        meta = [item for item in self.week["quizzes"]
                if item.get("question_role") == "meta_instruction"]
        self.assertEqual([item["content_id"] for item in meta], ["ENG-000035", "ENG-000047"])
        self.assertEqual(meta[0]["question_guide_ja"], "正しい英文はどれ？")
        self.assertEqual(meta[1]["question_guide_ja"], "「休憩する」の意味になるのはどれ？")
        with self.assertRaises(ValidationError):
            validate(dict(meta[0], question_role="learning_sentence"))
        learning = next(item for item in self.week["quizzes"]
                        if item.get("question_role") == "learning_sentence")
        with self.assertRaises(ValidationError):
            validate(dict(learning, question_role="meta_instruction"))
        visual = next(item for item in self.week["quizzes"] if item["visual_required"])
        broken = dict(visual, question_guide_ja="覚えてる？")
        with self.assertRaises(ValidationError):
            validate(broken)

    def test_all_question_images_are_rgb_1080_by_1350(self):
        for item in self.week["quizzes"]:
            path = REPO_ROOT / "artifacts" / "images" / f"{item['content_id']}-question.png"
            with Image.open(path) as image:
                self.assertEqual(image.size, (1080, 1350))
                self.assertEqual((image.format, image.mode), ("PNG", "RGB"))


if __name__ == "__main__":
    unittest.main()
