"""Leakage-controlled Ridge extension using fixed sentiment features."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path
from typing import Any

from .modeling import evaluate_temporal_holdout
from .review_coverage import temporal_holdout_rows, temporal_training_rows


ID_FIELDS = ("movielens_id", "imdb_id", "tmdb_id")
SENTIMENT_FIELDS = ("sentiment_score", "sentiment_available")


def evaluate_sentiment_augmented_ridge(
    ratings_path: Path,
    training_features_path: Path,
    test_features_path: Path,
    enriched_path: Path,
    *,
    test_fraction: float = 0.2,
    minimum_test_movies: int = 100,
) -> dict[str, Any]:
    """Fit Ridge plus sentiment without changing the fixed V1 row partitions."""

    ratings_rows = _read_rows(ratings_path)
    ratings = _index_rows(ratings_rows, ratings_path)
    training_features = _index_rows(
        _read_rows(training_features_path), training_features_path
    )
    test_features = _index_rows(_read_rows(test_features_path), test_features_path)
    expected_training_ids = {
        row["movielens_id"] for row in temporal_training_rows(
            ratings_path, test_fraction=test_fraction,
            minimum_test_movies=minimum_test_movies,
        )
    }
    expected_test_ids = {
        row["movielens_id"] for row in temporal_holdout_rows(
            ratings_path, test_fraction=test_fraction,
            minimum_test_movies=minimum_test_movies,
        )
    }
    if not set(training_features).issubset(expected_training_ids):
        raise ValueError("Training sentiment contains movies outside V1 training rows.")
    if not set(test_features).issubset(expected_test_ids):
        raise ValueError("Test sentiment contains movies outside the V1 outer holdout.")
    if set(training_features).intersection(test_features):
        raise ValueError("Training and outer-test sentiment movie IDs overlap.")
    for feature_rows in (training_features, test_features):
        for movie_id, feature in feature_rows.items():
            rating = ratings.get(movie_id)
            if rating is None:
                raise ValueError(f"Sentiment movie {movie_id} is absent from ratings.")
            for field in ID_FIELDS:
                if feature[field].strip() != rating[field].strip():
                    raise ValueError(f"Stable ID mismatch for {movie_id}: {field}")

    enriched_rows = []
    for row in ratings_rows:
        feature = training_features.get(row["movielens_id"])
        if feature is None:
            feature = test_features.get(row["movielens_id"])
        enriched_rows.append({
            **row,
            "sentiment_score": feature["sentiment_score"] if feature else "0.0",
            "sentiment_available": "1.0" if feature else "0.0",
        })
    enriched_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [*ratings_rows[0], *SENTIMENT_FIELDS]
    with enriched_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_rows)

    result = evaluate_temporal_holdout(
        enriched_path,
        test_fraction=test_fraction,
        minimum_test_movies=minimum_test_movies,
        outer_test_movie_ids=set(test_features),
        extra_numeric_fields=SENTIMENT_FIELDS,
    )
    result.update({
        "dataset": "real_v1_1_sentiment_augmented_ridge",
        "comparison_role": "sentiment_augmented_ridge",
        "sentiment_feature_used_by_model": True,
        "sentiment_method": "fixed_english_lexicon_with_three_token_negation_v1",
        "missing_training_sentiment_score": 0.0,
        "missingness_indicator_used": True,
        "training_sentiment_available_count": len(training_features),
        "training_sentiment_missing_count": len(expected_training_ids) - len(training_features),
        "test_sentiment_available_count": len(test_features),
        "training_features_sha256": _sha256(training_features_path),
        "test_features_sha256": _sha256(test_features_path),
        "outer_test_movie_ids_sha256": hashlib.sha256(
            ("\n".join(sorted(test_features)) + "\n").encode("utf-8")
        ).hexdigest(),
        "outer_test_used_for_sentiment_preprocessing": False,
    })
    return result


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = set(ID_FIELDS)
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"{path.name} must contain stable cross-platform IDs.")
    return rows


def _index_rows(rows: list[dict[str, str]], path: Path) -> dict[str, dict[str, str]]:
    indexed: dict[str, dict[str, str]] = {}
    for row in rows:
        movie_id = row["movielens_id"].strip()
        if not movie_id or movie_id in indexed:
            raise ValueError(f"Blank or duplicate MovieLens ID in {path.name}.")
        indexed[movie_id] = row
    return indexed


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
