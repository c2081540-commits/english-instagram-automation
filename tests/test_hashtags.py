import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from instagram_automation.hashtags import (HashtagConfigError, build_final_caption,
                                            hashtags_for_category, load_hashtag_config)


EXPECTED = {
    "grammar_usage": ["#英語学習", "#英語やり直し", "#英文法", "#大人の勉強"],
    "visual_vocabulary": ["#英語学習", "#英語やり直し", "#英単語", "#英語初心者"],
    "natural_choice": ["#英語学習", "#英語やり直し", "#英文法", "#英語初心者"],
    "situation": ["#英語学習", "#英語やり直し", "#英会話", "#英語フレーズ"],
    "review": ["#英語学習", "#英語やり直し", "#英語勉強", "#大人の勉強"],
}


class HashtagTests(unittest.TestCase):
    def test_all_five_categories_have_exact_expected_tags(self):
        self.assertEqual({key: hashtags_for_category(key) for key in EXPECTED}, EXPECTED)
        self.assertTrue(all(len(tags) == 4 and len(set(tags)) == 4 for tags in EXPECTED.values()))

    def test_unknown_duplicate_missing_hash_and_empty_are_rejected(self):
        with self.assertRaises(HashtagConfigError):
            hashtags_for_category("unknown")
        invalid_values = [
            {"common": ["#英語学習", "#英語学習"], "categories": {"x": ["#a", "#b"]}},
            {"common": ["英語学習", "#英語やり直し"], "categories": {"x": ["#a", "#b"]}},
            {"common": ["", "#英語やり直し"], "categories": {"x": ["#a", "#b"]}},
        ]
        for config in invalid_values:
            with self.subTest(config=config), self.assertRaises(HashtagConfigError):
                hashtags_for_category("x", config)

    def test_caption_body_is_byte_for_byte_prefix_before_separator(self):
        body = "1行目\n2行目。"
        result = build_final_caption(body, "grammar_usage")
        self.assertEqual(result.split("\n\n", 1)[0], body)
        self.assertEqual(result, body + "\n\n" + " ".join(EXPECTED["grammar_usage"]))

    def test_approved_week_has_42_valid_category_mappings_without_body_changes(self):
        schedule = json.loads((REPO_ROOT / "data" / "production" /
                               "final-schedule-2026-08-20.json").read_text())
        ids = [item["content_id"] for item in schedule["items"] if item["content_type"] == "quiz"]
        self.assertEqual(len(ids), 42)
        for content_id in ids:
            master = json.loads((REPO_ROOT / "data" / "master" / f"{content_id}.json").read_text())
            queue = json.loads((REPO_ROOT / "data" / "queue" / f"{content_id}.json").read_text())
            self.assertEqual(queue["caption"], master["instagram_caption"])
            final = build_final_caption(queue["caption"], master["production_category"])
            self.assertEqual(final.rsplit("\n\n", 1)[0], queue["caption"])
            self.assertEqual(final.rsplit("\n\n", 1)[1].split(),
                             EXPECTED[master["production_category"]])

    def test_threads_queue_does_not_receive_instagram_hashtags(self):
        threads_queue = REPO_ROOT.parent / "english-threads-automation" / "data" / "queue" / "ENG-000009.json"
        serialized = threads_queue.read_text(encoding="utf-8")
        for tag in load_hashtag_config()["common"]:
            self.assertNotIn(tag, serialized)


if __name__ == "__main__":
    unittest.main()
