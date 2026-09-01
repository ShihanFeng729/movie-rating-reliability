"""Coverage-matched V1.1 baseline using the unchanged V1 Ridge workflow."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from .modeling import evaluate_temporal_holdout


STABLE_ID_FIELDS = ("movielens_id", "imdb_id", "tmdb_id")


def evaluate_coverage_matched_ridge(
    ratings_path: Path,
    sentiment_features_path: Path,
    *,
    test_fraction: float = 0.2,
    minimum_test_movies: int = 100,
) -> dict[str, Any]:
    """Evaluate base Ridge on the exact outer-test movies with sentiment data."""

    ratings = _read_unique_rows(ratings_path, "movielens_id")
    coverage = _read_unique_rows(sentiment_features_path, "movielens_id")
    for movie_id, coverage_row in coverage.items():
        rating_row = ratings.get(movie_id)
        if rating_row is None:
            raise ValueError(f"Coverage movie {movie_id} is absent from ratings data.")
        for field in STABLE_ID_FIELDS:
            if coverage_row[field].strip() != rating_row[field].strip():
                raise ValueError(
                    f"Stable ID mismatch for MovieLens ID {movie_id}: {field}"
                )

    result = evaluate_temporal_holdout(
        ratings_path,
        test_fraction=test_fraction,
        minimum_test_movies=minimum_test_movies,
        outer_test_movie_ids=set(coverage),
    )
    result.update({
        "dataset": "real_v1_1_coverage_matched_movie_ratings",
        "coverage_definition": (
            "Fixed V1 outer-test movies with strict pre-2023-10-13 English "
            "review features; training rows remain the original older V1 rows."
        ),
        "coverage_join_fields": list(STABLE_ID_FIELDS),
        "coverage_movie_count": len(coverage),
        "ratings_input_sha256": hashlib.sha256(ratings_path.read_bytes()).hexdigest(),
        "sentiment_features_input_sha256": hashlib.sha256(
            sentiment_features_path.read_bytes()
        ).hexdigest(),
        "coverage_movie_ids_sha256": hashlib.sha256(
            ("\n".join(sorted(coverage)) + "\n").encode("utf-8")
        ).hexdigest(),
        "sentiment_feature_used_by_model": False,
        "comparison_role": "coverage_matched_base_ridge",
    })
    return result


def _read_unique_rows(path: Path, id_field: str) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = set(STABLE_ID_FIELDS)
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{path.name} must contain stable cross-platform IDs.")
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        movie_id = row[id_field].strip()
        if not movie_id:
            raise ValueError(f"{path.name} contains a blank {id_field}.")
        if movie_id in indexed:
            raise ValueError(f"Duplicate {id_field} {movie_id} in {path.name}.")
        indexed[movie_id] = row
    return indexed
