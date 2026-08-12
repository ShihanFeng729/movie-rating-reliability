"""Load simple local environment settings without third-party dependencies."""

from __future__ import annotations

import os
from pathlib import Path


def load_local_env(path: Path) -> None:
    """Load KEY=VALUE pairs without overwriting existing environment values."""

    if not path.exists():
        return
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"Invalid .env line {line_number}: expected KEY=VALUE.")
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key or any(character.isspace() for character in key):
            raise ValueError(f"Invalid .env key on line {line_number}.")
        os.environ.setdefault(key, value)
