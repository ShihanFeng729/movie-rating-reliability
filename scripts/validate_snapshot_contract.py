#!/usr/bin/env python3
"""Validate and summarize the planned V1 real-data snapshot."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.snapshot_contract import (  # noqa: E402
    load_snapshot_contract,
    summarize_snapshot_contract,
)


def main() -> None:
    path = PROJECT_ROOT / "config" / "real_snapshot_v1.json"
    summary = summarize_snapshot_contract(load_snapshot_contract(path))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
