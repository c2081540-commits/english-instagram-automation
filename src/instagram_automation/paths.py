from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent
MASTER_DIR = REPO_ROOT / "data" / "master"
NORMAL_MASTER_DIR = MASTER_DIR / "normal"
QUEUE_DIR = REPO_ROOT / "data" / "queue"
IMAGE_DIR = REPO_ROOT / "artifacts" / "images"
SOURCE_IMAGE_DIR = REPO_ROOT / "assets" / "source"
FONT_PATH = REPO_ROOT / "assets" / "fonts" / "NotoSansJP-VariableFont_wght.ttf"
REVIEW_DIR = REPO_ROOT / "data" / "review"
REVIEW_PAYLOAD_DIR = REVIEW_DIR / "payloads"
REVIEW_DECISION_DIR = REVIEW_DIR / "decisions"
REVIEW_RESULT_DIR = REVIEW_DIR / "results"
STORY_IMAGE_DIR = REPO_ROOT / "artifacts" / "stories"
THREADS_REPO_ROOT = WORKSPACE_ROOT / "english-threads-automation"
THREADS_NORMAL_MASTER_DIR = THREADS_REPO_ROOT / "data" / "master" / "normal"


def require_file(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent != MASTER_DIR.resolve():
        raise ValueError(f"Master file must be directly under {MASTER_DIR}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required master file not found: {resolved}")
    return resolved
