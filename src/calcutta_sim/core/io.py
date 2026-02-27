"""Lightweight JSON input/output utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: str | Path) -> Any:
    """Load JSON from a file path."""

    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str | Path, data: Any) -> None:
    """Serialize JSON to a file path, creating parent directories as needed."""

    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    with path_obj.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
