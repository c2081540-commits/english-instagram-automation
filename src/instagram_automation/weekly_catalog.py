from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

JST = timezone(timedelta(hours=9))


def _quiz(content_id, production_category, category, difficulty, seasonal,
          question, choices, best, hint, explanation, example="", translation="",
          difference=None, also=None, visual=False, visual_description=None):
    number = int(content_id.split("-")[1])
    captions = (
        "まずは3秒で考えてみよう。",
        "基礎表現をひとつ確認。",
        "日常で使える英語をチェック。",
        "パッと選べる？",
        "短い英語クイズです。",
        "今日の1問。答えは2枚目へ。",
    )
    return {
        "content_id": content_id,
        "category": category,
        "production_category": production_category,
        "difficulty": difficulty,
        "seasonal": seasonal,
        "question": question,
        "choices": choices,
        "answer_type": "best" if production_category in {"natural_choice", "situation"} else "single",
        "best_answer": best,
        "acceptable_answers": [best],
        "answer_hint": hint,
        "answer_hint_approved": True,
        "explanation": explanation,
        "key_difference": difference,
        "examples": [example] if example else [],
        "example_translations": [translation] if translation else [],
        "also_natural": also,
        "tip": None,
        "visual_required": visual,
        "visual_type": "photo" if visual else None,
        "visual_description": visual_description if visual else None,
        "problem_image_path": None,
        "image_information_role": "essential" if visual else None,
        "question_repeats_visual": False if visual else None,
        "instagram_caption": captions[number % len(captions)],
        "instagram_hashtags": [],
        "threads_parent_text": "3秒でどうぞ。",
        "threads_answer_text": f"正解は {best}。{explanation}",
        "publish_at": "",
    }


WEEK_ITEMS = [
    _quiz("ENG-000012", "grammar_usage", "grammar", "very_easy", False,
           "Tom ___ to work at eight.", ["go", "goes"], "goes",
           "主語は Tom。動詞の形は？", "Tom の現在形には -s を付けます。",
           "Tom goes home at six.", "トムは6時に帰宅します。"),
    _quiz("ENG-000013", "grammar_usage", "grammar", "easy", False,
           "I ___ busy yesterday.", ["am", "was"], "was",
           "yesterday に注目。", "過去の状態には was を使います。",
           "I was tired yesterday.", "昨日は疲れていました。"),
    _quiz("ENG-000014", "visual_vocabulary", "vocabulary", "very_easy", False,
           "The door is ___.", ["open", "closed", "broken", "missing"], "open",
           "ドアの今の状態は？", "open は「開いている」です。",
           "The door is open.", "ドアは開いています。", visual=True,
           visual_description="A clearly open office door, with the doorway and open door panel fully visible. No people, text, signs, logos, or watermark."),
    _quiz("ENG-000015", "natural_choice", "grammar", "easy", False,
           "I go to work ___ train.", ["by", "with", "on", "at"], "by",
           "移動手段の言い方は？", "交通手段には by を使います。",
           "I go to work by train.", "電車で通勤します。", "by train → 電車で\nwith a friend → 友達と"),
    _quiz("ENG-000016", "situation", "situation", "easy", True,
           "Would you like some water?", ["Yes, please.", "I am water."], "Yes, please.",
           "ほしいときの短い返事は？", "勧めを受けるなら Yes, please. が自然です。",
           also="Sure, thanks.", visual=True,
           visual_description="A server politely offering a clear glass of cold water to an office worker on a hot summer day. The offered water and gesture are obvious. No text, menu words, logos, or watermark."),
    _quiz("ENG-000017", "situation", "situation", "very_easy", False,
           "Where is the station?", ["It's near the bank.", "I am a station.", "At three years.", "Yes, I do."], "It's near the bank.",
           "場所を聞かれています。", "場所を伝える短い返答が自然です。",
           also="It's just ahead."),

    _quiz("ENG-000018", "grammar_usage", "grammar", "very_easy", False,
           "They ___ in Tokyo.", ["live", "lives"], "live",
           "主語は they。-s は必要？", "they の現在形には -s を付けません。",
           "They live near the station.", "彼らは駅の近くに住んでいます。"),
    _quiz("ENG-000019", "grammar_usage", "grammar", "easy", False,
           "I have ___ finished lunch.", ["just", "yet", "ever", "tomorrow"], "just",
           "たった今終えたなら？", "just は「たった今」を表します。",
           "I've just finished work.", "仕事を終えたところです。"),
    _quiz("ENG-000020", "visual_vocabulary", "vocabulary", "easy", False,
           "She is ___ the box.", ["carrying", "opening", "dropping", "kicking"], "carrying",
           "箱をどうしている？", "carry は「運ぶ」です。",
           "She is carrying a box.", "彼女は箱を運んでいます。", visual=True,
           visual_description="An adult office worker carrying one medium cardboard box securely with both arms. The carrying action is clear. No text, labels, logos, or watermark."),
    _quiz("ENG-000021", "natural_choice", "grammar", "easy_plus", False,
           "Please call me ___ lunch.", ["after", "later", "ago", "next"], "after",
           "後ろに lunch が続く形は？", "名詞の前には after を置けます。",
           "Let's talk after lunch.", "昼食後に話しましょう。", "after lunch → 昼食後\nlater → あとで"),
    _quiz("ENG-000022", "situation", "situation", "very_easy", False,
           "Thank you for your help.", ["You're welcome.", "Good morning.", "See you yesterday.", "I am help."], "You're welcome.",
           "お礼への定番の返事は？", "You're welcome. はお礼への基本の返事です。",
           also="No problem."),
    _quiz("ENG-000023", "situation", "situation", "easy", True,
           "Could you close the window?", ["Sure.", "I like windows."], "Sure.",
           "頼みを引き受けるなら？", "短い依頼には Sure. で自然に返せます。",
           also="Of course.", visual=True,
           visual_description="A summer office with an open window letting in bright heat, one coworker politely gesturing toward it and another ready to close it. No text, logos, or watermark."),

    _quiz("ENG-000024", "grammar_usage", "grammar", "very_easy", False,
           "This bag is ___ than mine.", ["heavy", "heavier", "heaviest", "more heavy"], "heavier",
           "than の前はどの形？", "2つを比べるときは比較級を使います。",
           "This box is heavier than that one.", "この箱はあの箱より重いです。"),
    _quiz("ENG-000025", "grammar_usage", "grammar", "easy", False,
           "We ___ dinner now.", ["eat", "are eating"], "are eating",
           "now に注目。", "今している動作には現在進行形を使います。",
           "We are eating dinner now.", "今、夕食を食べています。"),
    _quiz("ENG-000026", "visual_vocabulary", "vocabulary", "very_easy", False,
           "The cup is ___.", ["empty", "full", "hot", "broken"], "empty",
           "カップの中を見てみよう。", "empty は「空の」です。",
           "My cup is empty.", "私のカップは空です。", visual=True,
           visual_description="A clearly empty ceramic coffee cup viewed slightly from above on a clean desk. The empty inside is visible. No text, logos, or watermark."),
    _quiz("ENG-000027", "visual_vocabulary", "vocabulary", "easy", True,
           "The road is ___.", ["crowded", "quiet", "empty", "closed"], "crowded",
           "道路の混み具合は？", "crowded は「混雑した」です。",
           "The road is crowded today.", "今日は道路が混んでいます。", visual=True,
           visual_description="A busy summer city road filled with slow-moving cars, clearly showing traffic congestion. No readable signs, license text, logos, or watermark."),
    _quiz("ENG-000028", "natural_choice", "grammar", "easy_plus", False,
           "I have a meeting ___ 3 p.m.", ["at", "on"], "at",
           "時刻の前に置く語は？", "具体的な時刻には at を使います。",
           "The meeting starts at three.", "会議は3時に始まります。", "at 3 p.m. → 3時に\non Monday → 月曜に"),
    _quiz("ENG-000029", "situation", "situation", "easy", False,
           "Sorry I'm late.", ["That's okay.", "Here you are.", "I am late.", "Good night."], "That's okay.",
           "謝られたときの短い返事は？", "That's okay. は相手を安心させる返事です。",
           also="No worries."),

    _quiz("ENG-000030", "grammar_usage", "grammar", "very_easy", False,
           "There ___ a bank near here.", ["is", "are", "be", "have"], "is",
           "後ろの名詞は単数？", "単数の a bank には There is を使います。",
           "There is a cafe nearby.", "近くにカフェがあります。"),
    _quiz("ENG-000031", "grammar_usage", "grammar", "easy", False,
           "I ___ get up early tomorrow.", ["have to", "has to"], "have to",
           "主語は I。どちらの形？", "I には have to を使います。",
           "I have to leave now.", "もう出なければなりません。"),
    _quiz("ENG-000032", "visual_vocabulary", "vocabulary", "easy", False,
           "He is ___ the stairs.", ["climbing", "cleaning", "closing", "counting"], "climbing",
           "階段で何をしている？", "climb は「登る」です。",
           "He is climbing the stairs.", "彼は階段を登っています。", visual=True,
           visual_description="An adult office worker clearly walking upward on indoor stairs, one foot on a higher step. No text, signs, logos, or watermark."),
    _quiz("ENG-000033", "natural_choice", "grammar", "easy_plus", False,
           "I stayed home ___ it was raining.", ["because", "so"], "because",
           "後ろは理由？結果？", "理由を続けるときは because を使います。",
           "I left early because I was tired.", "疲れていたので早く帰りました。", "because → 理由\nso → 結果"),
    _quiz("ENG-000034", "situation", "situation", "very_easy", False,
           "May I sit here?", ["Of course.", "I sit daily.", "It is a pen.", "Last week."], "Of course.",
           "席を使ってよいなら？", "許可するときは Of course. と返せます。",
           also="Sure.", visual=True,
           visual_description="A person politely gesturing toward an empty chair beside a seated coworker in a simple office break area. The empty chair and request are clear. No text, logos, or watermark."),
    _quiz("ENG-000035", "review", "grammar", "easy", False,
           "Which sentence is correct?", ["He plays tennis.", "He play tennis.", "He playing tennis.", "He is play tennis."], "He plays tennis.",
           "he と現在形に注目。", "he の現在形には動詞へ -s を付けます。",
           "He works on Fridays.", "彼は金曜日に働きます。"),

    _quiz("ENG-000036", "grammar_usage", "grammar", "very_easy", False,
           "Can you ___ English?", ["speak", "speaks"], "speak",
           "can の後ろはどの形？", "can の後ろには動詞の原形を置きます。",
           "I can speak a little English.", "英語を少し話せます。"),
    _quiz("ENG-000037", "grammar_usage", "grammar", "easy", False,
           "I haven't eaten lunch ___.", ["yet", "already"], "yet",
           "まだ食べていないなら？", "否定文の「まだ」には yet を使います。",
           "I haven't finished yet.", "まだ終わっていません。"),
    _quiz("ENG-000038", "grammar_usage", "grammar", "easy_plus", False,
           "This is the book ___ I bought.", ["that", "where", "when", "what"], "that",
           "book を後ろから説明する語は？", "物を説明する関係代名詞に that を使えます。",
           "This is the bag that I bought.", "これは私が買ったバッグです。"),
    _quiz("ENG-000039", "visual_vocabulary", "vocabulary", "very_easy", True,
           "The bottle is ___.", ["leaking", "shining", "growing", "sleeping"], "leaking",
           "ボトルから何が起きている？", "leak は「漏れる」です。",
           "The bottle is leaking.", "ボトルから漏れています。", visual=True,
           visual_description="A reusable water bottle lying on a summer picnic table with a small visible stream of water leaking from a loose cap. No text, logos, or watermark."),
    _quiz("ENG-000040", "situation", "situation", "easy", False,
           "I didn't catch that.", ["Could you repeat that?", "I catch a train."], "Could you repeat that?",
           "聞き取れなかったら、どう頼む？", "聞き返すときの自然な依頼表現です。",
           also="Could you say that again?"),
    _quiz("ENG-000041", "situation", "situation", "easy_plus", False,
           "Do you need any help?", ["Yes, please.", "I need yesterday."], "Yes, please.",
           "助けが必要なら？", "助けをお願いするなら Yes, please. が自然です。",
           also="That would be great.", visual=True,
           visual_description="One office worker struggling to carry several plain boxes while a coworker offers help with an open-hand gesture. The need for help is obvious. No text, labels, logos, or watermark."),

    _quiz("ENG-000042", "grammar_usage", "grammar", "very_easy", False,
           "My office ___ at nine.", ["open", "opens"], "opens",
           "主語は単数。動詞の形は？", "単数の主語には opens を使います。",
           "The store opens at ten.", "店は10時に開きます。"),
    _quiz("ENG-000043", "grammar_usage", "grammar", "easy", False,
           "I've known her ___ 2020.", ["since", "for"], "since",
           "2020は期間？開始時点？", "開始時点には since を使います。",
           "I've worked here since April.", "4月からここで働いています。", "since 2020 → 2020年から\nfor five years → 5年間"),
    _quiz("ENG-000044", "visual_vocabulary", "vocabulary", "easy", False,
           "She is ___ the paper.", ["folding", "pouring", "unlocking", "throwing"], "folding",
           "紙をどうしている？", "fold は「折る」です。",
           "She is folding the paper.", "彼女は紙を折っています。", visual=True,
           visual_description="An adult at a clean desk folding a plain sheet of paper in half with both hands. The fold action is obvious. No text on paper, logos, or watermark."),
    _quiz("ENG-000045", "natural_choice", "grammar", "easy_plus", False,
           "Let's meet ___ Monday morning.", ["on", "at"], "on",
           "曜日を含む日の前は？", "曜日を含む日には on を使います。",
           "Let's meet on Friday.", "金曜日に会いましょう。", "on Monday → 月曜に\nat nine → 9時に"),
    _quiz("ENG-000046", "situation", "situation", "easy", True,
           "Is this seat taken?", ["No, it's free.", "It's very summer."], "No, it's free.",
           "空いている席なら？", "空席なら No, it's free. と伝えられます。",
           also="No, go ahead.", visual=True,
           visual_description="A commuter train with one clearly empty seat beside an adult passenger who makes a welcoming gesture toward it. Summer clothing, no readable signs, logos, or watermark."),
    _quiz("ENG-000047", "review", "vocabulary", "very_easy", False,
           "Which one means '休憩する'?", ["take a break", "make a break", "do a break", "get a breaking"], "take a break",
           "break と一緒に使う動詞は？", "「休憩する」は take a break です。",
           "Let's take a short break.", "少し休憩しましょう。"),
]

QUESTION_GUIDES = {
    "ENG-000012": "「トムは8時出勤」ならどっち？",
    "ENG-000013": "「昨日は大忙し」ならどっち？",
    "ENG-000015": "一番自然なのはどれ？",
    "ENG-000017": "こう聞かれたら、どう返す？",
    "ENG-000018": "「東京に住む」ならどっち？",
    "ENG-000019": "「昼食を終えた」ならどれ？",
    "ENG-000021": "一番自然なのはどれ？",
    "ENG-000022": "こんなとき、英語でどう言う？",
    "ENG-000024": "「私のより重い」ならどれ？",
    "ENG-000025": "「今、夕食中」ならどっち？",
    "ENG-000028": "自然なのはどっち？",
    "ENG-000029": "こんなとき、英語でどう言う？",
    "ENG-000030": "「近くに銀行がある」ならどれ？",
    "ENG-000031": "「早起きしないと」ならどっち？",
    "ENG-000033": "自然なのはどっち？",
    "ENG-000035": "正しい英文はどれ？",
    "ENG-000036": "「英語を話せる？」ならどっち？",
    "ENG-000037": "「昼食はまだ」ならどっち？",
    "ENG-000038": "「私が買った本」ならどれ？",
    "ENG-000040": "こんなとき、英語でどう言う？",
    "ENG-000042": "「9時に開く」ならどっち？",
    "ENG-000043": "「2020年から」ならどっち？",
    "ENG-000045": "自然なのはどっち？",
    "ENG-000047": "「休憩する」の意味になるのはどれ？",
}

for _item in WEEK_ITEMS:
    _item["question_guide_ja"] = QUESTION_GUIDES.get(_item["content_id"])
    _item["question_role"] = (None if _item["visual_required"] else
                              ("meta_instruction" if _item["content_id"] in {
                                  "ENG-000035", "ENG-000047"} else "learning_sentence"))


SITUATION_METADATA = {
    "ENG-000016": ("accept_refreshment_offer", "short_affirmative_response"),
    "ENG-000017": ("ask_for_directions", "information_request"),
    "ENG-000022": ("respond_to_thanks", "social_response"),
    "ENG-000023": ("accept_action_request", "short_affirmative_response"),
    "ENG-000029": ("respond_to_apology", "social_response"),
    "ENG-000034": ("grant_permission", "short_affirmative_response"),
    "ENG-000040": ("ask_for_repetition", "clarification_request"),
    "ENG-000041": ("accept_help_offer", "short_affirmative_response"),
    "ENG-000046": ("explain_seat_availability", "information_response"),
}

ANSWER_POINTS = {
    "ENG-000012": "he / she / Tom → 動詞に s",
    "ENG-000013": "yesterday → 過去形",
    "ENG-000018": "I / you / we / they → 動詞は原形",
    "ENG-000024": "than があれば比較級",
    "ENG-000025": "now → be動詞＋動詞ing",
    "ENG-000030": "a bank は単数 → There is",
    "ENG-000031": "I / you / we / they → have to",
    "ENG-000036": "can の後ろ → 動詞の原形",
    "ENG-000042": "単数の主語 → 動詞に s",
}

VISUAL_SOURCE_PATHS = {
    "ENG-000014": "assets/source/ENG-000014-open-door.png",
    "ENG-000016": "assets/source/ENG-000016-water-offer.png",
    "ENG-000020": "assets/source/ENG-000020-carrying-box.png",
    "ENG-000023": "assets/source/ENG-000023-close-window.png",
    "ENG-000026": "assets/source/ENG-000026-empty-cup.png",
    "ENG-000027": "assets/source/ENG-000027-crowded-road.png",
    "ENG-000032": "assets/source/ENG-000032-climbing-stairs.png",
    "ENG-000034": "assets/source/ENG-000034-empty-chair.png",
    "ENG-000039": "assets/source/ENG-000039-leaking-bottle.png",
    "ENG-000041": "assets/source/ENG-000041-help-with-boxes.png",
    "ENG-000044": "assets/source/ENG-000044-folding-paper.png",
    "ENG-000046": "assets/source/ENG-000046-empty-train-seat.png",
}

for _item in WEEK_ITEMS:
    if _item["content_id"] in SITUATION_METADATA:
        _item["situation_purpose"], _item["response_family"] = SITUATION_METADATA[_item["content_id"]]
    if _item["content_id"] in ANSWER_POINTS:
        _item["answer_point"] = ANSWER_POINTS[_item["content_id"]]
    if _item["content_id"] in VISUAL_SOURCE_PATHS:
        _item["problem_image_path"] = VISUAL_SOURCE_PATHS[_item["content_id"]]


NORMALS = [
    ("ENG-100003", "learning_habit", "勉強を始めるハードル", "教材を開く前に迷う人へ。", "今日やる場所を1つだけ決めよう。\n\n✓ テキストを机に出す\n✓ 最初の1問に付箋を貼る\n\n始める判断を先に済ませると、仕事後でも動きやすくなります。", "英語を始める前に、何をやるか迷って時間が過ぎることがあります。\n\n今日は教材を机に出し、最初の1問に付箋を貼っておく。\n\n始める判断を先に済ませると、仕事後の負担を減らせます。"),
    ("ENG-100004", "単語学習", "単語を覚えても使えないとき。", "単語だけで終わらせず、短い例文を1つ声に出そう。\n\nwork → I work in Tokyo.\n\n使う場面と一緒に覚えると、思い出しやすくなります。", "単語帳を見て意味が分かっても、会話で出てこないことがあります。\n\n今日は新しい単語を1つ選び、短い例文を作って声に出す。\n\n意味と使う場面を一緒に覚えられます。"),
    ("ENG-100005", "文法の復習", "文法は全部覚え直さなくていい。", "間違えた1問だけ確認しよう。\n\n✓ なぜその答えか\n✓ 自分の例文を1つ\n\n広く読み直すより、使える形を1つ増やそう。", "文法書を最初から読み直すと、量の多さで止まりやすくなります。\n\n間違えた1問のルールを確認し、自分の例文を1つ作る。\n\n今日はその1項目だけで十分です。"),
    ("ENG-100006", "リスニング", "聞き取れない音があるとき。", "同じ10秒を3回聞いてみよう。\n\n1回目：全体\n2回目：聞こえた単語\n3回目：英文を見ながら\n\n長時間流すより、短く確認できます。", "英語を長く聞き流しても、聞こえない部分がそのままになることがあります。\n\n今日は10秒だけ選び、全体・単語・英文確認の順で3回聞く。\n\n短い範囲なら音を丁寧に確認できます。"),
    ("ENG-100007", "音読", "音読で口が止まる人へ。", "速く読む必要はありません。\n\n✓ 1文だけ選ぶ\n✓ 意味を確認する\n✓ ゆっくり3回読む\n\n正確に言える文を1つ作ろう。", "音読で速さを追うと、発音も意味も曖昧になりがちです。\n\n今日は1文だけ選び、意味を確認してゆっくり3回読む。\n\n正確に言える文を1つ作る練習です。"),
    ("ENG-100008", "復習", "復習する問題を迷ったら。", "昨日間違えた問題を1問だけ解き直そう。\n\n答えを覚えていても、理由を言えればOK。\n\n新しい教材を増やす前に、昨日の穴を1つ埋めよう。", "復習範囲を広げすぎると、何から手を付けるか迷います。\n\n昨日間違えた問題を1問選び、答えの理由を言ってみる。\n\n新しい教材を増やす前に、理解の穴を1つ埋められます。"),
]

# Existing weekly copy is retained. These categories make future generation
# diversify learning habits with vocabulary, grammar, listening, and expression content.
_NORMAL_CATEGORY_BY_ID = {
    "ENG-100004": "memory_tip",
    "ENG-100005": "common_mistake",
    "ENG-100006": "skill_practice",
    "ENG-100007": "skill_practice",
    "ENG-100008": "study_method",
}
NORMALS = [item if len(item) == 6 else (item[0], _NORMAL_CATEGORY_BY_ID[item[0]], *item[1:]) for item in NORMALS]


def dated_items(start: date):
    slots = [time(7, 30), time(9, 30), time(12), time(15), time(17, 30), time(19, 30)]
    result = []
    for day_index in range(6):
        day = start + timedelta(days=day_index + 1)
        day_items = WEEK_ITEMS[day_index * 6:(day_index + 1) * 6]
        for item, slot in zip(day_items, slots):
            item = dict(item)
            item["publish_at"] = datetime.combine(day, slot, JST).isoformat()
            result.append(item)
    return result
