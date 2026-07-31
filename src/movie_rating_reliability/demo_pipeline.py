"""End-to-end, credential-free demo pipeline."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from movie_rating_reliability.demo_data import build_demo_movies, write_demo_csv


RATING_COLUMNS = (
    "tmdb_rating_10",
    "imdb_rating_10",
    "movielens_rating_10",
)


def summarize_demo_csv(path: Path) -> dict[str, Any]:
    """Validate a demo CSV and return a compact data-quality summary."""

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))

    if not rows:
        raise ValueError("Demo CSV contains no movie rows.")

    movie_ids = [row["movie_id"] for row in rows]
    titles = [row["title"] for row in rows]
    if len(movie_ids) != len(set(movie_ids)):
        raise ValueError("Demo CSV contains duplicate movie IDs.")
    if len(titles) != len(set(titles)):
        raise ValueError("Demo CSV contains duplicate movie titles.")

    missing_by_platform: dict[str, int] = {}
    rating_ranges: dict[str, dict[str, float]] = {}
    for column in RATING_COLUMNS:
        values = []
        for row in rows:
            raw_value = row[column].strip()
            if not raw_value:
                continue
            rating = float(raw_value)
            if not 1.0 <= rating <= 10.0:
                raise ValueError(f"{column} contains a rating outside 1–10.")
            values.append(rating)

        missing_by_platform[column] = len(rows) - len(values)
        rating_ranges[column] = {
            "minimum": min(values),
            "maximum": max(values),
        }

    complete_rows = sum(
        all(row[column].strip() for column in RATING_COLUMNS) for row in rows
    )
    return {
        "dataset": "fictional_demo_movie_ratings",
        "row_count": len(rows),
        "complete_row_count": complete_rows,
        "incomplete_row_count": len(rows) - complete_rows,
        "unique_movie_id_count": len(set(movie_ids)),
        "unique_title_count": len(set(titles)),
        "missing_ratings_by_platform": missing_by_platform,
        "rating_ranges": rating_ranges,
        "validation_status": "passed",
    }


def run_demo_pipeline(project_root: Path) -> dict[str, Any]:
    """Generate, validate, and summarize the API-free demo dataset."""

    demo_path = project_root / "data" / "demo" / "movie_ratings.csv"
    report_path = project_root / "reports" / "generated" / "demo_summary.json"

    write_demo_csv(demo_path, build_demo_movies())
    summary = summarize_demo_csv(demo_path)
    summary["data_path"] = str(demo_path.relative_to(project_root))
    summary["report_path"] = str(report_path.relative_to(project_root))

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary
