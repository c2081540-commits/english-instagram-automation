import unittest

from instagram_automation.formats import (
    FormatValidationError,
    answer_leakage_issues,
    validate_answer_leakage,
)


class AnswerLeakageTests(unittest.TestCase):
    def test_repeated_collocation_answer_is_rejected(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["make a decision", "make a mistake", "make progress", "___ an effort"],
            "choices": ["do", "make"], "correct_answer": "make",
        }
        self.assertIn("PATTERN_REPETITION_LEAKAGE", answer_leakage_issues(record))
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage(record)

    def test_repeated_transformation_shape_is_rejected(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["bring → brought", "buy → bought", "think → thought", "fight → ___"],
            "choices": ["fighted", "fought"], "correct_answer": "fought",
        }
        self.assertIn("TRANSFORMATION_LEAKAGE", answer_leakage_issues(record))
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage(record)

    def test_mixed_examples_pass(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["a desk", "an email", "a meeting", "___ hour"],
            "choices": ["an", "a"], "correct_answer": "an",
        }
        self.assertEqual([], answer_leakage_issues(record))
        validate_answer_leakage(record)

    def test_only_unseen_choice_is_rejected(self):
        record = {
            "format": "pattern", "answer_leakage": "PASS",
            "examples": ["do homework", "make a mistake", "have lunch", "___ a look"],
            "choices": ["do", "make", "have", "take"], "correct_answer": "take",
        }
        self.assertIn("SEQUENCE_LEAKAGE", answer_leakage_issues(record))
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage(record)

    def test_missing_human_review_status_fails_closed(self):
        record = {"format": "text", "choices": ["is", "are"], "correct_answer": "are"}
        with self.assertRaises(FormatValidationError):
            validate_answer_leakage(record)


if __name__ == "__main__":
    unittest.main()
