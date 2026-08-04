"""Pairwise movie-rating reliability metrics using only the standard library."""

from __future__ import annotations

import csv
from itertools import combinations
import math
from pathlib import Path
import random
from statistics import fmean
from typing import Callable


PLATFORM_COLUMNS = {
    "tmdb": "tmdb_rating_10",
    "imdb": "imdb_rating_10",
    "movielens": "movielens_rating_10",
}


def pearson_correlation(left: list[float], right: list[float]) -> float | None:
    """Return Pearson's linear correlation, or None for constant input."""

    _validate_pair(left, right)
    left_mean = fmean(left)
    right_mean = fmean(right)
    left_deviations = [value - left_mean for value in left]
    right_deviations = [value - right_mean for value in right]
    denominator = math.sqrt(
        sum(value**2 for value in left_deviations)
        * sum(value**2 for value in right_deviations)
    )
    if denominator == 0:
        return None
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left_deviations, right_deviations)
    ) / denominator


def average_ranks(values: list[float]) -> list[float]:
    """Assign average ranks to ties, using ranks that begin at one."""

    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    position = 0
    while position < len(indexed):
        end = position + 1
        while end < len(indexed) and indexed[end][1] == indexed[position][1]:
            end += 1
        average_rank = ((position + 1) + end) / 2
        for original_index, _ in indexed[position:end]:
            ranks[original_index] = average_rank
        position = end
    return ranks


def spearman_correlation(left: list[float], right: list[float]) -> float | None:
    """Return Spearman's rank correlation with average ranks for ties."""

    _validate_pair(left, right)
    return pearson_correlation(average_ranks(left), average_ranks(right))


def percentile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value.")
    if not 0 <= probability <= 1:
        raise ValueError("probability must be between zero and one.")
    ordered = sorted(values)
    location = (len(ordered) - 1) * probability
    lower = math.floor(location)
    upper = math.ceil(location)
    if lower == upper:
        return ordered[lower]
    fraction = location - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def paired_bootstrap_interval(
    left: list[float],
    right: list[float],
    statistic: Callable[[list[float], list[float]], float],
    *,
    confidence_level: float = 0.95,
    resamples: int = 2_000,
    seed: int = 510,
) -> dict[str, object]:
    """Return a deterministic paired percentile-bootstrap interval."""

    _validate_pair(left, right)
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level must be between zero and one.")
    if resamples < 1:
        raise ValueError("resamples must be positive.")

    rng = random.Random(seed)
    sample_size = len(left)
    distribution = []
    for _ in range(resamples):
        indices = [rng.randrange(sample_size) for _ in range(sample_size)]
        left_sample = [left[index] for index in indices]
        right_sample = [right[index] for index in indices]
        distribution.append(statistic(left_sample, right_sample))

    tail = (1 - confidence_level) / 2
    return {
        "lower": percentile(distribution, tail),
        "upper": percentile(distribution, 1 - tail),
        "confidence_level": confidence_level,
        "method": "paired_percentile_bootstrap",
        "resamples": resamples,
        "seed": seed,
    }


def mean_difference(left: list[float], right: list[float]) -> float:
    _validate_pair(left, right)
    return fmean(a - b for a, b in zip(left, right))


def mean_absolute_error(left: list[float], right: list[float]) -> float:
    _validate_pair(left, right)
    return fmean(abs(a - b) for a, b in zip(left, right))


def evaluate_rating_csv(path: Path) -> dict[str, object]:
    """Compute pairwise metrics from a common-scale rating CSV."""

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("Rating CSV contains no rows.")

    pair_results = []
    for pair_index, (left_name, right_name) in enumerate(
        combinations(PLATFORM_COLUMNS, 2)
    ):
        left_column = PLATFORM_COLUMNS[left_name]
        right_column = PLATFORM_COLUMNS[right_name]
        paired_values = [
            (float(row[left_column]), float(row[right_column]))
            for row in rows
            if row[left_column].strip() and row[right_column].strip()
        ]
        if len(paired_values) < 2:
            raise ValueError(
                f"{left_name} and {right_name} require at least two paired ratings."
            )
        left_values = [pair[0] for pair in paired_values]
        right_values = [pair[1] for pair in paired_values]
        bias = mean_difference(left_values, right_values)
        mae = mean_absolute_error(left_values, right_values)
        seed = 510 + pair_index
        pair_results.append(
            {
                "left_platform": left_name,
                "right_platform": right_name,
                "overlap_count": len(paired_values),
                "coverage_rate": round(len(paired_values) / len(rows), 4),
                "mean_difference_left_minus_right": round(bias, 4),
                "mean_absolute_error": round(mae, 4),
                "pearson_r": _rounded_optional(
                    pearson_correlation(left_values, right_values)
                ),
                "spearman_rho": _rounded_optional(
                    spearman_correlation(left_values, right_values)
                ),
                "mean_difference_95_ci": _rounded_interval(
                    paired_bootstrap_interval(
                        left_values,
                        right_values,
                        mean_difference,
                        seed=seed,
                    )
                ),
                "mae_95_ci": _rounded_interval(
                    paired_bootstrap_interval(
                        left_values,
                        right_values,
                        mean_absolute_error,
                        seed=seed,
                    )
                ),
            }
        )

    return {
        "scale": "1–10",
        "row_count": len(rows),
        "missing_policy": "pairwise_complete",
        "pairwise_metrics": pair_results,
        "interpretation_note": (
            "Correlation describes association, not agreement. Bias and MAE "
            "must be interpreted alongside Pearson and Spearman correlation."
        ),
    }


def _validate_pair(left: list[float], right: list[float]) -> None:
    if len(left) != len(right):
        raise ValueError("paired inputs must have equal length.")
    if len(left) < 2:
        raise ValueError("paired metrics require at least two observations.")


def _rounded_optional(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def _rounded_interval(interval: dict[str, object]) -> dict[str, object]:
    return {
        **interval,
        "lower": round(float(interval["lower"]), 4),
        "upper": round(float(interval["upper"]), 4),
    }
