#!/usr/bin/env python3
"""Collect first-page TMDB reviews for the fixed V1 training movies."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.local_env import load_local_env  # noqa: E402
from movie_rating_reliability.review_coverage import (  # noqa: E402
    collect_review_coverage,
    temporal_training_rows,
)
from movie_rating_reliability.tmdb_client import TmdbClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--workers", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("--workers must be between 1 and 8.")
    load_local_env(PROJECT_ROOT / ".env")
    token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
    if not token or token == "replace_with_your_tmdb_api_read_access_token":
        raise SystemExit("TMDB_BEARER_TOKEN is not configured.")
    ratings = PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv"
    client = TmdbClient(token, PROJECT_ROOT / "data" / "cache" / "tmdb")
    summary = collect_review_coverage(
        client,
        temporal_training_rows(ratings),
        PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_1_training_reviews",
        PROJECT_ROOT / "reports" / "generated" / "v1_1_training_review_coverage.json",
        stage="v1_1_training_review_coverage",
        population_name="fixed_v1_training_rows",
        refresh=args.refresh,
        limit=args.limit,
        workers=args.workers,
    )
    printable = {key: value for key, value in summary.items() if key != "movie_audits"}
    print(json.dumps(printable, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
