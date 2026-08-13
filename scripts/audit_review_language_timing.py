#!/usr/bin/env python3
"""Audit locally held TMDB review language evidence and timing boundaries."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.review_language_timing import (  # noqa: E402
    audit_language_and_timing,
    validate_languages_with_langdetect,
)


def main() -> None:
    summary = audit_language_and_timing(
        PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_reviews",
        PROJECT_ROOT / "reports" / "generated" / "v1_review_language_timing.json",
        imdb_cutoff=datetime(2026, 8, 11, 9, 37, 48, tzinfo=timezone.utc),
        movielens_cutoff=datetime(2023, 10, 13, tzinfo=timezone.utc),
    )
    summary["independent_language_validation"] = validate_languages_with_langdetect(
        PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_reviews"
    )
    (PROJECT_ROOT / "reports" / "generated" / "v1_review_language_timing.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    printable = {key: value for key, value in summary.items() if key != "movie_audits"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
