from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_DIR = REPO_ROOT / "data" / "master"
QUEUE_DIR = REPO_ROOT / "data" / "queue"
IMAGE_DIR = REPO_ROOT / "artifacts" / "images"


def require_file(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.parent != MASTER_DIR.resolve():
        raise ValueError(f"Master file must be directly under {MASTER_DIR}")
    if not resolved.is_file():
        raise FileNotFoundError(f"Required master file not found: {resolved}")
    return resolved
