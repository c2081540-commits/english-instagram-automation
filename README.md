# English Instagram Automation — Phase 1

Validated master English-learning content is converted into a pending Instagram carousel queue. Phase 1 does not call external APIs or generate images.

## Structure

- `data/master/`: canonical content JSON input
- `data/queue/`: generated Instagram queue JSON
- `artifacts/images/`: fixed output location for rendered question images
- `artifacts/stories/`: fixed output location for rendered Stories images
- `assets/source/`: problem-specific source images (no directory fallback)
- `assets/fonts/`: repository-pinned Noto Sans JP font and OFL license
- `assets/character/story-guide.png`: optional fixed Stories guide character
- `src/instagram_automation/`: validation, paths, and queue builder
- `scripts/`: queue generation and dry-run commands
- `tests/`: standard-library unit tests

## Run

Python 3.10 or newer is required. From any current directory:

```bash
python3 /absolute/path/to/english-instagram-automation/scripts/build_queue.py ENG-000001
python3 /absolute/path/to/english-instagram-automation/scripts/dry_run.py ENG-000001
python3 /absolute/path/to/english-instagram-automation/scripts/render_question.py ENG-000002
python3 /absolute/path/to/english-instagram-automation/scripts/render_answer.py ENG-000003
python3 /absolute/path/to/english-instagram-automation/scripts/render_story.py ENG-100001
python3 /absolute/path/to/english-instagram-automation/scripts/prepare_review.py ENG-000002 ENG-000003 ENG-000005
python3 -m unittest discover -s /absolute/path/to/english-instagram-automation/tests -v
```

Install the single rendering dependency with `python3 -m pip install -r requirements.txt`.

## Question image renderer

The renderer uses Pillow for deterministic direct PNG drawing at `1080 × 1350`. This keeps the layout stable, avoids browser/runtime complexity in GitHub Actions, and supports English and Japanese through the repository-pinned Noto Sans JP font. It automatically selects one of three layouts: image plus four choices, text-only four choices, or text-only two choices. Font sizes shrink only within defined bounds; content that still does not fit raises an error.

Set `problem_image_path` to a repository-relative file directly inside `assets/source/` when `visual_required` is `true`. Output is always fixed to `artifacts/images/<content_id>-question.png`. Missing inputs, paths outside the fixed directory, unsupported choice counts, and oversized text stop rendering without fallback.

## Answer image renderer

The answer renderer creates `1080 × 1350` PNG files at the fixed path `artifacts/images/<content_id>-answer.png`. Japanese-only UI labels and section order are fixed for `grammar`, `vocabulary`, and `situation`. The top section is a non-revealing `ヒント`; the next box shows the computed choice letter and exact answer, followed by category-specific `意味`, `例文`, `使い分け`, `こんな言い方も`, or `ポイント`. Set `answer_hint_approved` to `true` only for a reviewed hint. When it is `false`, the renderer uses the fixed generic cushion instead; approved hints containing `best_answer` or prohibited answer-leading phrases are rejected. Box heights are measured from content and constrained by section-specific minimums and maximums, with remaining space assigned to gaps and overall balance. English and Japanese text use Noto Sans JP. Stable colored heading icons are drawn directly with Pillow. Fixed accents are green for `答え`, blue for `ヒント`/`ポイント`/`意味`, neutral gray for `例文`, orange for `使い分け`, and purple for `こんな言い方も`. Every box has a white `#FFFFFF` background; color is limited to headings, icons, and borders. Missing required data, unsupported categories, oversized text, and overflowing sections stop rendering without fallback.

## Low-cost review preparation

`prepare_review.py` performs free machine checks before any Codex review: required master fields, content ID and answer validity, field length limits, fixed source-image presence for visual questions, rendered question/answer image presence and PNG/RGB/1080×1350 properties, and Instagram/Threads content ID and answer consistency. Machine failures are saved immediately as compact REJECT results and are not added to a review payload.

Passing items are batched into one JSON payload under `data/review/payloads/`. Each item contains its English, Japanese, and—only when `visual_required` is true—source-image review data. The payload explicitly requires one review pass and `REJECT → discard`, with no repair or re-review loop. It excludes Pillow-composed post images because their fixed template is covered by machine checks.

Future Codex automation should return one compact decision per item. Place its batch decision file directly under `data/review/decisions/`, then apply it with:

```bash
python3 /absolute/path/to/english-instagram-automation/scripts/apply_review_results.py review-batch DECISION_NAME
```

Final results are stored as `data/review/results/<content_id>.json` with only `content_id`, `status`, and `reason`. A REJECT reason is mandatory and limited to 160 characters. No correction path exists.

## Stories renderer

The Stories renderer converts the same normal master used by Threads into a fixed `1080 × 1920` RGB PNG. It uses Pillow and the repository-pinned Noto Sans JP font to draw an off-white outer background, white-board panel, blue accents, one restrained yellow marker line, the fixed label `オトナの英語やり直し`, `story_headline`, mechanically wrapped `story_body`, and the footer `@eigo_yarinaoshi`. When `assets/character/story-guide.png` exists, the same fixed character is resized with its aspect ratio preserved and placed at the lower right; when absent, the text-only template still renders. It does not regenerate characters, use AI image generation, gradients, CTA, or ads.

Normal masters are placed directly under `data/master/normal/`. Every required field must exactly match the fixed sibling source at `english-threads-automation/data/master/normal/`; otherwise rendering stops. Headline and body have hard character and layout limits, and the renderer fails closed instead of shrinking below the minimum font size.

All paths are derived from each script/module's resolved `__file__`. Inputs are accepted only from this repository's `data/master`; missing or invalid data stops processing without fallback or automatic correction.

## Phase 3 daily trial

`data/production/daily-2026-08-20.json` is the single batch source for six quizzes and one normal item. `python3 scripts/build_daily_trial.py 2026-08-20` checks the category mix, exactly one seasonal quiz, at most two visual quizzes, ID/question duplication, length limits, and renderer compatibility before materializing the shared masters and outputs. The date argument selects the matching fixed-path batch, so additional days do not require code changes.

Questions that need an ungenerated visual are never given a placeholder: their status is `WAITING_FOR_VISUAL` in `data/production/daily-2026-08-20-status.json`. Non-visual question images, every answer image, and the normal Stories image use the existing renderers. The seven items share one compact Codex review payload at `data/review/payloads/daily-2026-08-20.json`; REJECT means discard and replacement, with a maximum of three replacements and no repair/re-review loop.

## Production visual pipeline and SNS limits

Production visual requests are fixed under `data/visual/requests/`; generated PNG sources are saved directly under `assets/source/` and referenced explicitly by each master. No directory search or placeholder fallback is allowed. `ice-cream-placeholder.png` remains a renderer fixture and is rejected by the production visual check. After free PNG/path/resolution checks, the two source assets are reviewed together for content match, visible action/state, obvious generation failures, and unwanted text. Compact decisions are stored under `data/visual/reviews/` before the existing Pillow question renderer runs.

Daily candidates fail closed above 70 characters for a question, 25 characters for any choice, or 45 characters for a hint. Situation quizzes also fail when the question plus longest choice exceeds 85 characters, and explanations are limited to two sentences. Recommended targets remain 50 characters for questions and 15 for choices; passing the renderer alone does not override these SNS content limits.

## 最上位コンテンツ品質基準

正本は `config/content_quality.json` です。対象は「英語学習に一度挫折し、基礎からやり直したい日本人社会人」であり、難化を品質向上とは扱いません。中学英語、高校初級、日常・仕事で使う基礎表現を中心に、簡単な2択・4択も積極的に許可します。上級者・資格試験・難関受験・細かな例外・ひっかけ問題は対象外です。

問題は3〜5秒で論点が分かる短さを優先します。70文字・25文字・45文字はfail closed上限であり、推奨値ではありません。画像は解答に必要な情報を担う場合だけ使用し、問題文で画像の状況を重複説明しません。回答画像は必要なBOXだけを使い、例文は原則1件、使い分けは短い対比を優先します。一括レビューは「英語・正解」「日本語」「画像」「挫折者向けとして3〜5秒で理解できるか」の4点を1回で判定し、REJECTを修正ループへ送りません。

## 7日量産テスト

`python3 scripts/build_weekly_trial.py YYYY-MM-DD` は指定開始日から7日分（42 quiz＋7 normal）を生成し、週全体のカテゴリ・難易度・2択/4択・visual・seasonal・重複を検査します。原稿確定後に `python3 scripts/prepare_weekly_visuals.py YYYY-MM-DD` でvisual対象だけを単一requestへまとめます。未生成素材は `WAITING_FOR_VISUAL` のままで、ダミー画像は使用しません。

週次品質では、シチュエーション問題に `situation_purpose` と `response_family` を持たせます。`Sure. / Of course. / Yes, please. / Go ahead.` などの短い肯定返答は同じ広域ファミリーとして数え、同じ週へ偏らないようfail closedで検査します。基礎文法は必要な場合だけ `answer_point` に40文字以内・改行なしの1行ポイントを持てます。Normal投稿は `normal_category` で学習習慣、勉強法、英語小ネタ、よくある勘違い、覚え方、実用表現、技能練習を区別し、週内で4カテゴリ以上を使用します。

## 正式投稿スケジュール

投稿枠は `config/schedule.json` で管理します。`python3 scripts/finalize_week_schedule.py YYYY-MM-DD` は、確認済み週次原稿の順序を変えず、6件のFeed Quizと22:30のStoriesを7日分のqueueへ確定します。Quiz carouselは常に問題画像が1枚目、回答画像が2枚目です。queueは `content_id / platform / publish_at / status` を持ち、初期状態は `pending` です。`posted` は再実行対象になりません。

実行時点で過去の枠は日時を変更せず `execution_eligibility: past_due_hold` として保持し、自動実行対象から除外します。翌日への詰め込みや時刻変更は行いません。自動実行・定期実行は未接続です。

## Phase 6 Meta投稿クライアント

`scripts/run_due_post.py` はqueueから `pending + scheduled + publish_at <= now` の先頭1件だけを選びます。引数なしはAPIを呼ばないdry-runで、`--live` を明示した場合だけMeta APIへ接続します。

```bash
python3 scripts/run_due_post.py --now 2026-08-20T16:00:00+09:00
# 本番接続工程でのみ: python3 scripts/run_due_post.py --live
```

必要な環境変数（値はrepoへ保存しません）：

- `INSTAGRAM_ACCESS_TOKEN`
- `INSTAGRAM_USER_ID`
- `META_GRAPH_API_VERSION`

認証方式はInstagram API with Instagram Loginです。User profile、権限確認、Feed/Carousel、Stories、
publishはすべて `https://graph.instagram.com/{META_GRAPH_API_VERSION}` を使用します。Facebook Page、
`graph.facebook.com`、`pages_*` permissionは使用しません。投稿に必要なpermissionは
`instagram_business_basic / instagram_business_content_publish` です。

Feed Quizは question child container、answer child container、carousel container、publishの順です。Storiesは独立したStory containerからpublishします。成功後はremote IDとposted時刻をreceiptへ先に保存し、queueを`posted`へ原子的に更新します。`posted / failed / skipped / past_due_hold`は自動選択しません。

画像URLは公開repoのGitHub Raw HTTPSを `config/media_public.json` から生成します。ローカルパスをAPIへ送りません。live時は匿名HEAD取得を検査し、repoのprivate化、404、非HTTPSでは`BLOCKED_MEDIA_URL`で停止します。安全な一時的通信エラーだけ最大2回retryし、認証・データ・media URLエラーはretryしません。

### 分離された実接続テスト

`scripts/run_meta_connection_test.py` はproduction queueを読まず、`data/test_payloads/instagram-carousel.json`だけを使用します。フラグなしは説明表示のみで、`--live-test`がある場合だけpreflight後にテストcarouselを投稿します。
実接続時はrepo rootの親にあるワークスペース共通 `.env` を読み込みます。シェルに既に設定された環境変数は `.env` で上書きしません。`.env` はGit管理対象外です。

```bash
python3 scripts/run_meta_connection_test.py
python3 scripts/run_meta_connection_test.py --live-test
```

preflightではUser IDとtokenをprofile GETで検証し、`content_publishing_limit` の非破壊GETが成功することで
`instagram_business_basic / instagram_business_content_publish` を検証します。Instagram Login APIに存在しない
Facebook方式の `/me/permissions` は使用しません。あわせて2画像の匿名HTTPS取得を検証します。成功時のcontainer IDと
published media IDはgitignoreされた`data/test_receipts/`へ保存し、access tokenは保存しません。

`python3 scripts/export_weekly_review.py YYYY-MM-DD` は問題・回答・Storiesのcontact sheet、両媒体dry-run、集計レポートを `artifacts/weekly/YYYY-MM-DD/` に出力します。

## Future phases

Future work may add answer-image rendering, AI-generated source images, Meta API publishing, scheduled Codex generation, insights, and optimization. These are intentionally absent from the current implementation.
