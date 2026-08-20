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

`data/production/daily-2026-08-20.json` is the single batch source for six quizzes and one normal item. `scripts/build_daily_trial.py` checks the category mix, exactly one seasonal quiz, at most two visual quizzes, ID/question duplication, length limits, and renderer compatibility before materializing the shared masters and outputs.

Questions that need an ungenerated visual are never given a placeholder: their status is `WAITING_FOR_VISUAL` in `data/production/daily-2026-08-20-status.json`. Non-visual question images, every answer image, and the normal Stories image use the existing renderers. The seven items share one compact Codex review payload at `data/review/payloads/daily-2026-08-20.json`; REJECT means discard and replacement, with a maximum of three replacements and no repair/re-review loop.

## Future phases

Future work may add answer-image rendering, AI-generated source images, Meta API publishing, scheduled Codex generation, insights, and optimization. These are intentionally absent from the current implementation.
