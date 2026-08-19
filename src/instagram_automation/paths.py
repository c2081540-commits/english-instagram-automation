from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_DIR = REPO_ROOT / "data" / "master"
QUEUE_DIR = REPO_ROOT / "data" / "queue"
IMAGE_DIR = REPO_ROOT / "artifacts" / "images"
SOURCE_IMAGE_DIR = REPO_ROOT / "assets" / "source"
FONT_PATH = REPO_ROOT / "assets" / "fonts" / "NotoSansJP-VariableFont_wght.ttf"
EMOJI_FONT_PATH = REPO_ROOT / "assets" / "fonts" / "NotoEmoji-VariableFont_wght.ttf"


def require_file(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent != MASTER_DIR.resolve():
        raise ValueError(f"Master file must be directly under {MASTER_DIR}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required master file not found: {resolved}")
    return resolved
