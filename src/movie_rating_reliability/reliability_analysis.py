"""Grouped and sensitivity analysis for the real V1 reliability snapshot."""

from __future__ import annotations

import csv
from itertools import combinations
from pathlib import Path
from typing import Callable

from movie_rating_reliability.evaluation import (
    PLATFORM_COLUMNS,
    mean_absolute_error,
    mean_difference,
    pearson_correlation,
    percentile,
    spearman_correlation,
)


def analyze_reliability_segments(path: Path, *, minimum_group_size: int = 20) -> dict[str, object]:
    """Compare platform agreement across prespecified groups and sensitivities."""

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("Reliability dataset contains no rows.")
    if minimum_group_size < 2:
        raise ValueError("minimum_group_size must be at least two.")

    dimensions: dict[str, Callable[[dict[str, str]], str]] = {
        "release_decade": lambda row: str(row["release_decade"]),
        "primary_genre": lambda row: _primary_genre(row["genres"]),
        "movielens_rating_count_band": lambda row: row["movielens_rating_count_band"],
    }
    grouped: dict[str, list[dict[str, object]]] = {}
    for dimension, classifier in dimensions.items():
        buckets: dict[str, list[dict[str, str]]] = {}
        for row in rows:
            buckets.setdefault(classifier(row), []).append(row)
        grouped[dimension] = [
            {"group": group, "row_count": len(group_rows), "pairwise_metrics": _metrics(group_rows)}
            for group, group_rows in sorted(buckets.items())
            if len(group_rows) >= minimum_group_size
        ]

    popularity_cutoff = percentile([float(row["tmdb_popularity"]) for row in rows], 0.9)
    sensitivities = [
        {"name": "all_eligible_movies", "rule": "TMDB votes >= 50", "rows": rows},
        {
            "name": "exclude_top_10_percent_tmdb_popularity",
            "rule": f"TMDB popularity <= {popularity_cutoff:.4f}",
            "rows": [row for row in rows if float(row["tmdb_popularity"]) <= popularity_cutoff],
        },
        {
            "name": "higher_support_thresholds",
            "rule": "TMDB votes >= 500, IMDb votes >= 1000, MovieLens ratings >= 200",
            "rows": [
                row for row in rows
                if int(row["tmdb_vote_count"]) >= 500
                and int(row["imdb_vote_count"]) >= 1000
                and int(row["movielens_rating_count"]) >= 200
            ],
        },
    ]
    sensitivity_results = [
        {
            "name": item["name"],
            "rule": item["rule"],
            "row_count": len(item["rows"]),
            "pairwise_metrics": _metrics(item["rows"]),
        }
        for item in sensitivities if len(item["rows"]) >= minimum_group_size
    ]
    return {
        "row_count": len(rows),
        "minimum_group_size": minimum_group_size,
        "grouped_results": grouped,
        "sensitivity_results": sensitivity_results,
        "matching_sensitivity": {
            "available": False,
            "reason": (
                "All included movies use stable MovieLens, IMDb, and TMDB identifiers; "
                "no fuzzy-match subgroup exists for comparison."
            ),
        },
        "interpretation_boundaries": {
            "correlation": "Pearson and Spearman measure shared ordering or movement.",
            "agreement": "Bias and MAE measure score-level differences and are not replaced by correlation.",
            "prediction": "Predictive performance requires a held-out target and is evaluated separately.",
        },
    }


def _metrics(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    results = []
    for left, right in combinations(PLATFORM_COLUMNS, 2):
        left_values = [float(row[PLATFORM_COLUMNS[left]]) for row in rows]
        right_values = [float(row[PLATFORM_COLUMNS[right]]) for row in rows]
        results.append({
            "pair": f"{left}-{right}",
            "mean_difference_left_minus_right": round(mean_difference(left_values, right_values), 4),
            "mean_absolute_error": round(mean_absolute_error(left_values, right_values), 4),
            "pearson_r": _rounded(pearson_correlation(left_values, right_values)),
            "spearman_rho": _rounded(spearman_correlation(left_values, right_values)),
        })
    return results


def _primary_genre(value: str) -> str:
    return value.replace("|", ",").split(",", 1)[0].strip() or "Unknown"


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 4)
