# English Instagram Automation — Phase 1

Validated master English-learning content is converted into a pending Instagram carousel queue. Phase 1 does not call external APIs or generate images.

## Structure

- `data/master/`: canonical content JSON input
- `data/queue/`: generated Instagram queue JSON
- `artifacts/images/`: fixed output location for rendered question images
- `assets/source/`: problem-specific source images (no directory fallback)
- `assets/fonts/`: repository-pinned Noto Sans JP/Noto Emoji fonts and OFL license
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
python3 -m unittest discover -s /absolute/path/to/english-instagram-automation/tests -v
```

Install the single rendering dependency with `python3 -m pip install -r requirements.txt`.

## Question image renderer

The renderer uses Pillow for deterministic direct PNG drawing at `1080 × 1350`. This keeps the layout stable, avoids browser/runtime complexity in GitHub Actions, and supports English and Japanese through the repository-pinned Noto Sans JP font. It automatically selects one of three layouts: image plus four choices, text-only four choices, or text-only two choices. Font sizes shrink only within defined bounds; content that still does not fit raises an error.

Set `problem_image_path` to a repository-relative file directly inside `assets/source/` when `visual_required` is `true`. Output is always fixed to `artifacts/images/<content_id>-question.png`. Missing inputs, paths outside the fixed directory, unsupported choice counts, and oversized text stop rendering without fallback.

## Answer image renderer

The answer renderer creates `1080 × 1350` PNG files at the fixed path `artifacts/images/<content_id>-answer.png`. Its headings, emoji mapping, section order, and layout are fixed for `grammar`, `vocabulary`, and `situation`; unused optional sections receive no reserved space. English and Japanese text use Noto Sans JP, while fixed heading emoji use the repository-pinned Noto Emoji font. English examples use the first `examples` item and require a matching Japanese entry in `example_translations`. Situation content requires `also_natural`. Oversized text, unsupported categories, and missing required section data stop rendering without fallback.

All paths are derived from each script/module's resolved `__file__`. Inputs are accepted only from this repository's `data/master`; missing or invalid data stops processing without fallback or automatic correction.

## Future phases

Future work may add answer-image rendering, AI-generated source images, Meta API publishing, scheduled Codex generation, insights, and optimization. These are intentionally absent from the current implementation.
