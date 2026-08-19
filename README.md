# English Instagram Automation — Phase 1

Validated master English-learning content is converted into a pending Instagram carousel queue. Phase 1 does not call external APIs or generate images.

## Structure

- `data/master/`: canonical content JSON input
- `data/queue/`: generated Instagram queue JSON
- `artifacts/images/`: planned location for future rendered images
- `src/instagram_automation/`: validation, paths, and queue builder
- `scripts/`: queue generation and dry-run commands
- `tests/`: standard-library unit tests

## Run

Python 3.10 or newer is required. From any current directory:

```bash
python3 /absolute/path/to/english-instagram-automation/scripts/build_queue.py ENG-000001
python3 /absolute/path/to/english-instagram-automation/scripts/dry_run.py ENG-000001
python3 -m unittest discover -s /absolute/path/to/english-instagram-automation/tests -v
```

All paths are derived from each script/module's resolved `__file__`. Inputs are accepted only from this repository's `data/master`; missing or invalid data stops processing without fallback or automatic correction.

## Future phases

Future work may add image rendering/generation, Meta API publishing, scheduled Codex generation, insights, and optimization. These are intentionally absent from Phase 1.
