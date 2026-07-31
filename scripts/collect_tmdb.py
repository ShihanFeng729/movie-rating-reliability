#!/usr/bin/env python3
"""Collect timestamped movie-rating snapshots from the TMDB API."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.tmdb_client import TmdbClient  # noqa: E402
from movie_rating_reliability.tmdb_collection import (  # noqa: E402
    collect_discover_snapshot,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect a timestamped TMDB discover/movie snapshot."
    )
    parser.add_argument("--pages", type=int, default=1)
    parser.add_argument("--start-page", type=int, default=1)
    parser.add_argument("--language", default="en-US")
    parser.add_argument("--sort-by", default="popularity.desc")
    parser.add_argument("--minimum-votes", type=int, default=0)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Ignore recent cached responses and request fresh API data.",
    )
    parser.add_argument(
        "--cache-hours",
        type=float,
        default=24,
        help="Reuse an API response for this many hours (default: 24).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    token = os.environ.get("TMDB_BEARER_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "TMDB_BEARER_TOKEN is not set. Copy .env.example for guidance, "
            "then export the token in your terminal before running this command."
        )

    client = TmdbClient(
        token,
        PROJECT_ROOT / "data" / "cache" / "tmdb",
        cache_hours=args.cache_hours,
    )
    metadata = collect_discover_snapshot(
        client,
        PROJECT_ROOT / "data" / "raw" / "tmdb",
        pages=args.pages,
        start_page=args.start_page,
        language=args.language,
        sort_by=args.sort_by,
        minimum_votes=args.minimum_votes,
        refresh=args.refresh,
    )
    print(
        f"Saved {metadata['movie_count']} movies to "
        f"{metadata['movies_path']}"
    )


if __name__ == "__main__":
    main()
