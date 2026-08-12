#!/usr/bin/env python3
"""Build the local V1 pre-TMDB candidate table."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.real_candidates import build_candidate_table  # noqa: E402
from movie_rating_reliability.snapshot_contract import (  # noqa: E402
    load_snapshot_contract,
)


def main() -> None:
    external = PROJECT_ROOT / "data" / "external"
    contract = load_snapshot_contract(
        PROJECT_ROOT / "config" / "real_snapshot_v1.json"
    )
    summary = build_candidate_table(
        movielens_zip=external / "movielens" / "ml-32m.zip",
        imdb_basics_gz=external / "imdb" / "title.basics.tsv.gz",
        imdb_ratings_gz=external / "imdb" / "title.ratings.tsv.gz",
        contract=contract,
        output_path=PROJECT_ROOT / "data" / "interim" / "v1_candidates.csv",
        summary_path=(
            PROJECT_ROOT / "reports" / "generated" / "v1_candidate_summary.json"
        ),
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
