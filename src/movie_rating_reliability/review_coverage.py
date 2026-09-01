"""Resumable TMDB review coverage audit for the fixed temporal holdout."""

from __future__ import annotations

import csv
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from typing import Any, Protocol


class ReviewClient(Protocol):
    def movie_reviews(
        self, tmdb_id: int, *, page: int, language: str, refresh: bool
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...


def temporal_holdout_rows(
    data_path: Path, *, test_fraction: float = 0.2, minimum_test_movies: int = 100
) -> list[dict[str, str]]:
    """Return the same newest-movie holdout used by the Ridge evaluation."""

    with data_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"tmdb_id", "release_year", "movielens_id"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Real V1 dataset is empty or missing holdout columns.")
    test_size = max(minimum_test_movies, math.ceil(len(rows) * test_fraction))
    if test_size >= len(rows):
        raise ValueError("Temporal holdout leaves no training movies.")
    ordered = sorted(
        rows,
        key=lambda row: (int(row["release_year"]), row["movielens_id"]),
    )
    return ordered[-test_size:]


def temporal_training_rows(
    data_path: Path, *, test_fraction: float = 0.2, minimum_test_movies: int = 100
) -> list[dict[str, str]]:
    """Return the older training rows preceding the fixed temporal holdout."""

    with data_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {"tmdb_id", "release_year", "movielens_id"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Real V1 dataset is empty or missing holdout columns.")
    test_size = max(minimum_test_movies, math.ceil(len(rows) * test_fraction))
    if test_size >= len(rows):
        raise ValueError("Temporal holdout leaves no training movies.")
    ordered = sorted(
        rows,
        key=lambda row: (int(row["release_year"]), row["movielens_id"]),
    )
    return ordered[:-test_size]


def audit_review_coverage(
    client: ReviewClient,
    data_path: Path,
    raw_dir: Path,
    summary_path: Path,
    *,
    language: str = "en-US",
    refresh: bool = False,
    limit: int | None = None,
    minimum_test_movies: int = 100,
) -> dict[str, Any]:
    """Collect first-page review metadata and summarize text coverage."""

    holdout = temporal_holdout_rows(data_path, minimum_test_movies=minimum_test_movies)
    return collect_review_coverage(
        client, holdout, raw_dir, summary_path,
        stage="tmdb_review_coverage_audit",
        population_name="fixed_holdout",
        language=language, refresh=refresh, limit=limit,
    )


def collect_review_coverage(
    client: ReviewClient,
    population_rows: list[dict[str, str]],
    raw_dir: Path,
    summary_path: Path,
    *,
    stage: str,
    population_name: str,
    language: str = "en-US",
    refresh: bool = False,
    limit: int | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    """Collect resumable first-page reviews for an explicit movie population."""

    selected = population_rows[:limit] if limit is not None else population_rows
    raw_dir.mkdir(parents=True, exist_ok=True)
    if workers < 1:
        raise ValueError("workers must be at least 1")

    def collect_one(row: dict[str, str]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        tmdb_id = int(row["tmdb_id"])
        item_path = raw_dir / f"{tmdb_id}.json"
        try:
            if item_path.exists() and not refresh:
                record = json.loads(item_path.read_text(encoding="utf-8"))
            else:
                payload, request = client.movie_reviews(
                    tmdb_id, page=1, language=language, refresh=refresh
                )
                record = {"payload": payload, "request": request}
                item_path.write_text(
                    json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
            return _summarize_movie(tmdb_id, record), None
        except Exception as error:
            return None, {
                "tmdb_id": tmdb_id,
                "error_type": type(error).__name__,
                "message": str(error),
            }

    with ThreadPoolExecutor(max_workers=workers) as executor:
        collected = list(executor.map(collect_one, selected))
    movie_audits = [audit for audit, _ in collected if audit is not None]
    failures = [failure for _, failure in collected if failure is not None]
    covered = [item for item in movie_audits if item["nonempty_review_count"] > 0]
    language_movie_counts: dict[str, int] = {}
    for item in covered:
        for code in set(item["languages"]):
            language_movie_counts[code] = language_movie_counts.get(code, 0) + 1
    audited_count = len(movie_audits)
    summary = {
        "stage": stage,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "requested_language": language,
        "population_name": population_name,
        "population_movie_count": len(population_rows),
        **(
            {"fixed_holdout_movie_count": len(population_rows)}
            if population_name == "fixed_holdout" else {}
        ),
        "selected_movie_count": len(selected),
        "audited_movie_count": audited_count,
        "failed_movie_count": len(failures),
        "text_covered_movie_count": len(covered),
        "text_coverage_rate": round(len(covered) / audited_count, 4) if audited_count else 0.0,
        "language_movie_counts": dict(sorted(language_movie_counts.items())),
        "movie_audits": movie_audits,
        "failures": failures,
        "raw_review_text_published": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _summarize_movie(tmdb_id: int, record: dict[str, Any]) -> dict[str, Any]:
    payload = record["payload"]
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise ValueError("TMDB review results must be a list.")
    nonempty = [
        item for item in results
        if isinstance(item, dict) and str(item.get("content", "")).strip()
    ]
    languages = [
        str(item.get("iso_639_1") or "unknown") for item in nonempty
    ]
    created_at_count = sum(bool(item.get("created_at")) for item in nonempty)
    updated_at_count = sum(bool(item.get("updated_at")) for item in nonempty)
    return {
        "tmdb_id": tmdb_id,
        "reported_total_results": int(payload.get("total_results", len(results))),
        "first_page_review_count": len(results),
        "nonempty_review_count": len(nonempty),
        "languages": sorted(languages),
        "reviews_with_created_at": created_at_count,
        "reviews_with_updated_at": updated_at_count,
        "fetched_at_utc": record.get("request", {}).get("fetched_at_utc", ""),
    }
