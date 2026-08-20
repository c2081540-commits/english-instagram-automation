import os
from pathlib import Path


WORKSPACE_ENV = Path(__file__).resolve().parents[3] / ".env"


def load_workspace_env(path: Path = WORKSPACE_ENV) -> None:
    """Load a simple KEY=VALUE file without overriding process environment."""
    if not path.is_file():
        raise RuntimeError(f"Local environment file not found: {path}")
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise RuntimeError(f"Invalid .env entry at line {line_number}")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not key.replace("_", "A").isalnum() or key[0].isdigit():
            raise RuntimeError(f"Invalid .env key at line {line_number}")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)
