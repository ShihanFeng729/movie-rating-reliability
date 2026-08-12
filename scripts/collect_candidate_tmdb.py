#!/usr/bin/env python3
"""Collect TMDB details for the fixed V1 candidate sample."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.tmdb_candidate_collection import (  # noqa: E402
    collect_candidate_details,
)
from movie_rating_reliability.tmdb_client import TmdbClient  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect resumable TMDB details for V1 candidate IDs."
    )
    parser.add_argument("--language", default="en-US")
    parser.add_argument("--cache-hours", type=float, default=24)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument(
        "--limit", type=int, help="Collect only the first N rows for a smoke test."
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be at least 1.")
    token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "TMDB_BEARER_TOKEN is not set. Export it in this terminal before running."
        )
    contract = json.loads(
        (PROJECT_ROOT / "config" / "real_snapshot_v1.json").read_text(
            encoding="utf-8"
        )
    )
    sizes = contract["sample_size"]
    thresholds = contract["eligibility"]["minimum_votes"]
    client = TmdbClient(
        token,
        PROJECT_ROOT / "data" / "cache" / "tmdb",
        cache_hours=args.cache_hours,
    )
    summary = collect_candidate_details(
        client,
        PROJECT_ROOT / "data" / "interim" / "v1_candidates.csv",
        PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_candidates",
        PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv",
        PROJECT_ROOT / "reports" / "generated" / "v1_tmdb_collection.json",
        tmdb_minimum_votes=int(thresholds["tmdb"]),
        target_complete=int(sizes["target_complete_movies"]),
        minimum_complete=int(sizes["minimum_complete_movies"]),
        expected_candidates=int(sizes["candidate_movies"]),
        language=args.language,
        refresh=args.refresh,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
