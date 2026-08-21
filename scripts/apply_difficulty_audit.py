#!/usr/bin/env python3
"""Apply the human-review draft difficulty revisions without touching posted queues."""
from __future__ import annotations

import json
from pathlib import Path

IG_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = IG_ROOT.parent
THREADS_ROOT = WORKSPACE / "english-threads-automation"


REVISIONS = {
    "ENG-000008": {
        "question": "He is ___ up his sleeves.",
        "choices": ["rolling", "roll"], "best_answer": "rolling",
        "answer_hint": "isの後ろの形に注目。",
        "explanation": "今している動作なので、isの後ろにrollingを置きます。",
        "key_difference": None,
        "examples": ["He is rolling up his sleeves."],
        "example_translations": ["彼は袖をまくっています。"],
        "threads_answer_text": "💡 正解は A. rolling\n\n今している動作なので、isの後ろにrollingを置きます。\n\n📝 He is rolling up his sleeves.\n「彼は袖をまくっています。」\n\n🔑 is＋-ing＝今している動作",
    },
    "ENG-000010": {
        "question": "It's hot. He'll turn ___ the AC.",
        "choices": ["on", "off"], "best_answer": "on",
        "answer_hint": "暑い部屋で、エアコンをどうする？",
        "explanation": "turn onは、エアコンなどの電源を入れる定番表現です。",
        "key_difference": "turn on＝つける / turn off＝消す",
        "examples": ["He'll turn on the AC."],
        "example_translations": ["彼がエアコンをつけます。"],
        "threads_answer_text": "💡 正解は A. on\n\n暑い部屋でエアコンをつけるので、turn onを使います。\n\n🗣️ He'll turn on the AC.\n「彼がエアコンをつけます。」\n\n🔑 turn on＝つける / turn off＝消す",
    },
    "ENG-000011": {
        "question": "Would you like anything ___?",
        "choices": ["else", "other", "another", "again"], "best_answer": "else",
        "answer_hint": "anythingと一緒に使う語は？",
        "explanation": "anything elseで「ほかに何か」という定番のまとまりです。",
        "key_difference": "anything else＝ほかに何か",
        "examples": ["Would you like anything else?"],
        "example_translations": ["ほかに何かいかがですか？"],
        "question_guide_ja": "「ほかにも何か」ならどれ？",
        "threads_answer_text": "💡 正解は A. else\n\nanything elseで「ほかに何か」という意味になります。\n\n🗣️ Would you like anything else?\n「ほかに何かいかがですか？」\n\n🔑 anything else＝ほかに何か",
    },
    "ENG-000016": {
        "question": "Yes, I'd ___ some, please.",
        "choices": ["like", "to like"], "best_answer": "like",
        "answer_hint": "I'dの後ろの形に注目。",
        "explanation": "I'd like ...は、欲しいものを丁寧に伝える定番表現です。",
        "key_difference": "I'd like ...＝〜をお願いします",
        "examples": ["Yes, I'd like some, please."],
        "example_translations": ["はい、少しいただきたいです。"],
        "threads_answer_text": "💡 正解は A. like\n\nI'd like ...は、欲しいものを丁寧に伝える表現です。\n\n🗣️ Yes, I'd like some, please.\n「はい、少しいただきたいです。」\n\n🔑 I'd like ...＝〜をお願いします",
    },
    "ENG-000017": {
        "question": "It's ___ the bank.",
        "choices": ["near", "nearly", "next", "close"], "best_answer": "near",
        "answer_hint": "後ろにthe bankがそのまま続く語は？",
        "explanation": "nearは、後ろに場所を直接置いて「〜の近く」を表せます。",
        "key_difference": "near the bank / next to the bank",
        "examples": ["It's near the bank."],
        "example_translations": ["銀行の近くです。"],
        "question_guide_ja": "「銀行の近く」ならどれ？",
        "threads_answer_text": "💡 正解は A. near\n\nnearは、後ろに場所を直接置いて「〜の近く」を表せます。\n\n🗣️ It's near the bank.\n「銀行の近くです。」\n\n🔑 near the bank / next to the bank",
    },
    "ENG-000020": {
        "question": "She carries the box ___ both hands.",
        "choices": ["with", "by"], "best_answer": "with",
        "answer_hint": "手段を表す前置詞を考えよう。",
        "explanation": "with both handsで「両手で」という意味になります。",
        "key_difference": None,
        "examples": ["She carries the box with both hands."],
        "example_translations": ["彼女は両手で箱を運びます。"],
        "threads_answer_text": "💡 正解は A. with\n\nwith both handsで「両手で」という意味になります。\n\n📝 She carries the box with both hands.\n「彼女は両手で箱を運びます。」\n\n🔑 with＋道具・体の一部＝〜を使って",
    },
    "ENG-000022": {
        "question": "Thank you for your help. — You're ___.",
        "choices": ["welcome", "welcomed", "welcoming", "welcomes"], "best_answer": "welcome",
        "answer_hint": "お礼への定番の返答は？",
        "explanation": "You're welcome.は、お礼を言われたときの定番表現です。",
        "key_difference": "You're welcome.＝どういたしまして。",
        "examples": ["You're welcome."],
        "example_translations": ["どういたしまして。"],
        "question_guide_ja": "「どういたしまして」ならどれ？",
        "threads_answer_text": "💡 正解は A. welcome\n\nYou're welcome.は、お礼を言われたときの定番表現です。\n\n🗣️ You're welcome.\n「どういたしまして。」\n\n🔑 You're welcome.＝どういたしまして。",
    },
    "ENG-000023": {
        "question": "She is ___ to close the window.",
        "choices": ["about", "almost"], "best_answer": "about",
        "answer_hint": "to closeの前に置ける形は？",
        "explanation": "be about to ...で「今にも〜する」を表します。",
        "key_difference": "be about to＋動詞＝今にも〜する",
        "examples": ["She is about to close the window."],
        "example_translations": ["彼女は今、窓を閉めようとしています。"],
        "visual_required": False,
        "visual_type": None,
        "visual_description": None,
        "problem_image_path": None,
        "image_information_role": None,
        "question_repeats_visual": None,
        "question_guide_ja": "「今にも閉める」ならどっち？",
        "question_role": "learning_sentence",
        "threads_parent_text": "答えを決めてからどうぞ。",
        "learning_point": "be about to＋動詞",
        "threads_answer_text": "💡 正解は A. about\n\nbe about to ...で「今にも〜する」を表します。\n\n🗣️ She is about to close the window.\n「彼女は今、窓を閉めようとしています。」\n\n🔑 be about to＋動詞＝今にも〜する",
    },
    "ENG-000026": {
        "question": "There isn't ___ in the cup.",
        "choices": ["anything", "something", "nothing", "everything"], "best_answer": "anything",
        "answer_hint": "否定文で使う語を考えよう。",
        "explanation": "否定文ではanythingを使って「何も〜ない」を表します。",
        "key_difference": None,
        "examples": ["There isn't anything in the cup."],
        "example_translations": ["カップには何も入っていません。"],
        "threads_answer_text": "💡 正解は A. anything\n\n否定文ではanythingを使って「何も〜ない」を表します。\n\n📝 There isn't anything in the cup.\n「カップには何も入っていません。」\n\n🔑 not ... anything＝何も〜ない",
    },
    "ENG-000027": {
        "question": "There are ___ cars on the road.",
        "choices": ["too many", "too much"], "best_answer": "too many",
        "answer_hint": "carsは数えられる？",
        "explanation": "carsは数えられる名詞なので、too manyを使います。",
        "key_difference": None,
        "examples": ["There are too many cars on the road."],
        "example_translations": ["道路には車が多すぎます。"],
        "threads_answer_text": "💡 正解は A. too many\n\ncarsは数えられるので、too manyを使います。\n\n📝 There are too many cars on the road.\n「道路には車が多すぎます。」\n\n🔑 too many＋数えられる名詞",
    },
    "ENG-000029": {
        "question": "Sorry I'm late. Don't ___ about it.",
        "choices": ["worry", "worries", "worried", "worrying"], "best_answer": "worry",
        "answer_hint": "Don'tの後ろの形に注目。",
        "explanation": "Don'tの後ろでは、動詞をそのままの形で使います。",
        "key_difference": "Don't＋動詞＝〜しないで",
        "examples": ["Don't worry about it."],
        "example_translations": ["気にしないでください。"],
        "question_guide_ja": "「気にしないで」ならどれ？",
        "threads_answer_text": "💡 正解は A. worry\n\nDon'tの後ろでは、動詞をそのままの形で使います。\n\n🗣️ Don't worry about it.\n「気にしないでください。」\n\n🔑 Don't＋動詞＝〜しないで",
    },
    "ENG-000032": {
        "question": "He is walking ___ the stairs.",
        "choices": ["up", "up to"], "best_answer": "up",
        "answer_hint": "階段の途中？ それとも手前まで？",
        "explanation": "upは「上る」、up toは「〜まで行く」です。",
        "key_difference": None,
        "examples": ["He is walking up the stairs."],
        "example_translations": ["彼は階段を上っています。"],
        "learning_point": "upとup toの使い分け",
        "threads_answer_text": "💡 正解は A. up\n\n写真では階段の途中を上っているので、up the stairsです。\n\n📝 He is walking up the stairs.\n「彼は階段を上っています。」\n\n🔑 up＝上る / up to＝〜まで行く",
    },
    "ENG-000034": {
        "question": "What does she say to him?",
        "choices": ["You can sit here.", "I can sit here."], "best_answer": "You can sit here.",
        "answer_hint": "話している相手は誰？",
        "explanation": "相手に席を勧めるので、主語はyouになります。",
        "key_difference": "you＝相手 / I＝自分",
        "examples": ["You can sit here."],
        "example_translations": ["ここに座っていいですよ。"],
        "learning_point": "会話でのyouとIの使い分け",
        "threads_answer_text": "💡 正解は A. You can sit here.\n\n相手に席を勧めるので、主語はyouです。\n\n🗣️ You can sit here.\n「ここに座っていいですよ。」\n\n🔑 you＝相手 / I＝自分",
    },
    "ENG-000039": {
        "question": "Water is coming ___ of the bottle.",
        "choices": ["out", "up", "on", "at"], "best_answer": "out",
        "answer_hint": "水が動いている方向は？",
        "explanation": "come out of ...で「〜から出てくる」を表します。",
        "key_difference": None,
        "examples": ["Water is coming out of the bottle."],
        "example_translations": ["ボトルから水が出ています。"],
        "threads_answer_text": "💡 正解は A. out\n\n水がボトルの中から外へ出ているので、out ofを使います。\n\n📝 Water is coming out of the bottle.\n「ボトルから水が出ています。」\n\n🔑 out of＝〜の中から外へ",
    },
    "ENG-000040": {
        "question": "I didn't catch that. Could you ___ that?",
        "choices": ["repeat", "repeats", "repeated", "repeating"], "best_answer": "repeat",
        "answer_hint": "Could youの後ろの形に注目。",
        "explanation": "Could youの後ろでは、動詞をそのままの形で使います。",
        "key_difference": "Could you＋動詞＝〜していただけますか",
        "examples": ["Could you repeat that?"],
        "example_translations": ["もう一度言っていただけますか？"],
        "question_guide_ja": "「もう一度言って」ならどれ？",
        "threads_answer_text": "💡 正解は A. repeat\n\nCould youの後ろでは、動詞をそのままの形で使います。\n\n🗣️ Could you repeat that?\n「もう一度言っていただけますか？」\n\n🔑 Could you＋動詞＝〜していただけますか",
    },
    "ENG-000041": {
        "question": "She offers ___ him with the boxes.",
        "choices": ["to help", "help", "helping", "helped"], "best_answer": "to help",
        "answer_hint": "offerの後ろの形に注目。",
        "explanation": "offer to helpで「手伝うと申し出る」という意味になります。",
        "key_difference": "offer to＋動詞＝〜すると申し出る",
        "examples": ["She offers to help him with the boxes."],
        "example_translations": ["彼女は箱を運ぶのを手伝うと申し出ています。"],
        "threads_answer_text": "💡 正解は A. to help\n\noffer to helpで「手伝うと申し出る」という意味になります。\n\n🗣️ She offers to help him with the boxes.\n「彼女は箱を運ぶのを手伝うと申し出ています。」\n\n🔑 offer to＋動詞＝〜すると申し出る",
    },
    "ENG-000044": {
        "question": "She is folding the paper ___ half.",
        "choices": ["in", "on", "at", "to"], "best_answer": "in",
        "answer_hint": "「半分に」の定番表現は？",
        "explanation": "fold ... in halfで「〜を半分に折る」を表します。",
        "key_difference": None,
        "examples": ["She is folding the paper in half."],
        "example_translations": ["彼女は紙を半分に折っています。"],
        "threads_answer_text": "💡 正解は A. in\n\nfold ... in halfで「〜を半分に折る」を表します。\n\n📝 She is folding the paper in half.\n「彼女は紙を半分に折っています。」\n\n🔑 in half＝半分に",
    },
    "ENG-000046": {
        "question": "Is anyone ___ here?",
        "choices": ["sitting", "sit"], "best_answer": "sitting",
        "answer_hint": "今の状態を尋ねる形に注目。",
        "explanation": "今そこに座っている人がいるか尋ねるので、isとsittingを使います。",
        "key_difference": "be動詞＋-ing＝今していること",
        "examples": ["Is anyone sitting here?"],
        "example_translations": ["ここに誰か座っていますか？"],
        "learning_point": "現在進行形の疑問文",
        "threads_answer_text": "💡 正解は A. sitting\n\n今そこに座っている人がいるか尋ねるので、is＋sittingです。\n\n🗣️ Is anyone sitting here?\n「ここに誰か座っていますか？」\n\n🔑 be動詞＋-ing＝今していること",
    },
}

# Preserve the already-approved weekly difficulty distribution.  The audit
# classification (TARGET / TOO_EASY / TOO_HARD) is stored separately in
# difficulty_gate and must not rewrite this production metadata.
ORIGINAL_DIFFICULTY = {
    "ENG-000008": "beginner",
    "ENG-000010": "beginner",
    "ENG-000011": "intermediate",
    "ENG-000016": "easy",
    "ENG-000017": "very_easy",
    "ENG-000020": "easy",
    "ENG-000022": "very_easy",
    "ENG-000023": "easy",
    "ENG-000026": "very_easy",
    "ENG-000027": "easy",
    "ENG-000029": "easy",
    "ENG-000032": "easy",
    "ENG-000034": "very_easy",
    "ENG-000039": "very_easy",
    "ENG-000040": "easy",
    "ENG-000041": "easy_plus",
    "ENG-000044": "easy",
    "ENG-000046": "easy",
}

VISUAL_IDS = {8, 10, 16, 20, 23, 26, 27, 32, 34, 39, 41, 44, 46}
TEXT_REVISED_IDS = {11, 17, 22, 29, 40}
POSTED_IDS = {9, 12, 13, 14, 15}
EFFECTIVE = {
    6: 2, 7: 3, 8: 2, 10: 2, 11: 3, 15: 2, 16: 2, 17: 3, 18: 2, 19: 3,
    20: 2, 21: 2, 22: 2, 23: 2, 24: 3, 25: 2, 26: 2, 27: 2, 28: 2,
    29: 2, 30: 3, 31: 2, 32: 2, 33: 2, 34: 2, 35: 3, 36: 2, 37: 2,
    38: 3, 39: 2, 40: 2, 41: 2, 42: 2, 43: 2, 44: 2, 45: 2, 46: 2, 47: 3,
}


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def gate(content_id: str, item: dict) -> dict:
    number = int(content_id.split("-")[1])
    revised = content_id in REVISIONS
    return {
        "visual_only_solvable": False,
        "common_sense_only": False,
        "effective_choice_count": EFFECTIVE[number],
        "weak_distractor_count": 0,
        "unique_answer": True,
        "visual_contributes_to_decision": True if item.get("visual_required") else None,
        "difficulty": "TARGET",
        "initial_difficulty": "TOO_EASY" if revised else "TARGET",
        "decision": "REVISE" if revised else "KEEP",
    }


def update_item(item: dict) -> None:
    content_id = item.get("content_id")
    if not isinstance(content_id, str) or not content_id.startswith("ENG-000"):
        return
    number = int(content_id.split("-")[1])
    if number < 6 or number > 47:
        return
    if number in POSTED_IDS:
        # A post may become published while a human-review draft is open.
        # Remove draft-only metadata and leave all published content intact.
        item.pop("difficulty_gate", None)
        return
    if content_id in REVISIONS:
        revision = REVISIONS[content_id]
        item.update(revision)
        item["acceptable_answers"] = [revision["best_answer"]]
        item["answer_type"] = "single"
        item["difficulty"] = ORIGINAL_DIFFICULTY[content_id]
        item["answer_hint_approved"] = True
        item["tip"] = None
    item["difficulty_gate"] = gate(content_id, item)


def walk(value) -> None:
    if isinstance(value, dict):
        update_item(value)
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def assert_unposted() -> None:
    for content_id in REVISIONS:
        for root in (IG_ROOT, THREADS_ROOT):
            queue = read(root / "data" / "queue" / f"{content_id}.json")
            if queue["status"] == "posted":
                raise RuntimeError(f"{content_id} became posted; fetch and exclude before applying")


def main() -> int:
    assert_unposted()
    for number in range(6, 48):
        if number in POSTED_IDS:
            continue
        content_id = f"ENG-{number:06d}"
        for path in (IG_ROOT / "data" / "master" / f"{content_id}.json",
                     THREADS_ROOT / "data" / "master" / "quiz" / f"{content_id}.json"):
            data = read(path)
            update_item(data)
            write(path, data)

    for path in sorted((IG_ROOT / "data" / "production").glob("*.json")):
        data = read(path)
        walk(data)
        write(path, data)

    for content_id, revision in REVISIONS.items():
        queue_path = THREADS_ROOT / "data" / "queue" / f"{content_id}.json"
        queue = read(queue_path)
        if queue["status"] != "posted":
            queue["answer_text"] = revision["threads_answer_text"]
            if "threads_parent_text" in revision:
                queue["parent_text"] = revision["threads_parent_text"]
            write(queue_path, queue)

    audited = sum(number not in POSTED_IDS for number in EFFECTIVE)
    print(f"audited={audited} revised={len(REVISIONS)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
