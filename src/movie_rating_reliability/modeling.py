"""Interpretable IMDb rating baseline using only the standard library."""

from __future__ import annotations

import csv
from dataclasses import dataclass
import math
from pathlib import Path
from statistics import fmean
from typing import Callable, Sequence


RATING_MINIMUM = 1.0
RATING_MAXIMUM = 10.0


@dataclass(frozen=True)
class ModelDataset:
    """Numeric feature matrix and labels prepared from complete movie rows."""

    movie_ids: list[str]
    feature_names: list[str]
    features: list[list[float]]
    targets: list[float]
    reference_genre: str


def load_model_dataset(path: Path) -> ModelDataset:
    """Load complete rows and create explicit, reproducible model features."""

    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("Model dataset contains no rows.")

    required = {
        "release_year",
        "tmdb_rating_10",
        "tmdb_vote_count",
        "imdb_rating_10",
        "movielens_rating_10",
        "movielens_rating_count",
    }
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"Model dataset is missing columns: {sorted(missing)}")

    complete_rows = [
        row for row in rows if all(row[column].strip() for column in required)
    ]
    if len(complete_rows) < 3:
        raise ValueError("Model evaluation requires at least three complete rows.")

    id_column = "movie_id" if "movie_id" in rows[0] else "movielens_id"
    genre_column = "genre" if "genre" in rows[0] else "genres"
    if id_column not in rows[0] or genre_column not in rows[0]:
        raise ValueError("Model dataset requires a movie ID and genre column.")
    genres = sorted({_primary_genre(row[genre_column]) for row in complete_rows})
    reference_genre = genres[0]
    encoded_genres = genres[1:]
    feature_names = [
        "tmdb_rating_10",
        "movielens_rating_10",
        "log10_tmdb_vote_count",
        "log10_movielens_rating_count",
        "release_decades_since_2000",
        *(f"genre_{genre}" for genre in encoded_genres),
    ]

    movie_ids: list[str] = []
    features: list[list[float]] = []
    targets: list[float] = []
    for row in complete_rows:
        tmdb_count = int(row["tmdb_vote_count"])
        movielens_count = int(row["movielens_rating_count"])
        if tmdb_count <= 0 or movielens_count <= 0:
            raise ValueError("Rating counts must be positive before log transformation.")
        target = float(row["imdb_rating_10"])
        if not RATING_MINIMUM <= target <= RATING_MAXIMUM:
            raise ValueError("IMDb target rating is outside the 1–10 scale.")

        genre = _primary_genre(row[genre_column])
        movie_ids.append(row[id_column].strip())
        features.append(
            [
                float(row["tmdb_rating_10"]),
                float(row["movielens_rating_10"]),
                math.log10(tmdb_count),
                math.log10(movielens_count),
                (int(row["release_year"]) - 2000) / 10,
                *(1.0 if genre == candidate else 0.0 for candidate in encoded_genres),
            ]
        )
        targets.append(target)

    return ModelDataset(
        movie_ids=movie_ids,
        feature_names=feature_names,
        features=features,
        targets=targets,
        reference_genre=reference_genre,
    )


def _primary_genre(value: str) -> str:
    """Use the first declared genre for a stable, compact baseline encoding."""

    normalized = value.replace("|", ",")
    genre = normalized.split(",", 1)[0].strip()
    return genre or "Unknown"


def evaluate_temporal_holdout(
    path: Path, *, test_fraction: float = 0.2, minimum_test_movies: int = 100,
    alpha: float | None = None,
    outer_test_movie_ids: set[str] | None = None,
) -> dict[str, object]:
    """Evaluate Ridge on the newest movies, with preprocessing fixed by the file."""

    if not 0 < test_fraction < 1:
        raise ValueError("test_fraction must be between zero and one.")
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {
        "release_year", "genres", "tmdb_rating_10", "tmdb_vote_count",
        "imdb_rating_10", "movielens_rating_10", "movielens_rating_count",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Real V1 dataset is empty or missing required columns.")
    complete = [row for row in rows if all(row[column].strip() for column in required)]
    test_size = max(minimum_test_movies, math.ceil(len(complete) * test_fraction))
    if test_size >= len(complete):
        raise ValueError("Temporal holdout leaves no training movies.")
    ordered = sorted(
        complete,
        key=lambda row: (
            int(row["release_year"]),
            (row.get("movie_id") or row.get("movielens_id") or ""),
        ),
    )
    train_rows = ordered[:-test_size]
    full_test_rows = ordered[-test_size:]
    test_rows = full_test_rows
    if outer_test_movie_ids is not None:
        if not outer_test_movie_ids:
            raise ValueError("Outer-test movie ID filter cannot be empty.")
        available_ids = {row["movielens_id"] for row in full_test_rows}
        missing_ids = sorted(outer_test_movie_ids.difference(available_ids))
        if missing_ids:
            raise ValueError(
                "Outer-test movie IDs are outside the fixed temporal holdout: "
                f"{missing_ids[:5]}"
            )
        test_rows = [
            row for row in full_test_rows
            if row["movielens_id"] in outer_test_movie_ids
        ]
        if len(test_rows) < 2:
            raise ValueError("Filtered outer test requires at least two movies.")
    alpha_candidates = (0.1, 1.0, 10.0)
    validation_size = min(
        max(2, math.ceil(len(train_rows) * 0.2)),
        len(train_rows) - 2,
    )
    inner_train_rows = train_rows[:-validation_size]
    validation_rows = train_rows[-validation_size:]
    inner_transform, _, _ = _fit_real_transformer(inner_train_rows)
    inner_train_features = [inner_transform(row) for row in inner_train_rows]
    validation_features = [inner_transform(row) for row in validation_rows]
    inner_train_targets = [float(row["imdb_rating_10"]) for row in inner_train_rows]
    validation_targets = [float(row["imdb_rating_10"]) for row in validation_rows]
    alpha_validation = []
    for candidate_alpha in alpha_candidates:
        inner_coefficients = fit_ridge(
            inner_train_features, inner_train_targets, alpha=candidate_alpha
        )
        validation_predictions = [
            predict(inner_coefficients, features) for features in validation_features
        ]
        alpha_validation.append({
            "alpha": candidate_alpha,
            "validation_mae": round(
                regression_metrics(validation_targets, validation_predictions)["mae"], 4
            ),
        })
    selected_alpha = alpha if alpha is not None else min(
        alpha_validation, key=lambda item: (item["validation_mae"], item["alpha"])
    )["alpha"]
    transform, reference_genre, encoded_genres = _fit_real_transformer(train_rows)
    train_features = [transform(row) for row in train_rows]
    test_features = [transform(row) for row in test_rows]
    train_targets = [float(row["imdb_rating_10"]) for row in train_rows]
    actual = [float(row["imdb_rating_10"]) for row in test_rows]
    coefficients = fit_ridge(
        train_features, train_targets, alpha=float(selected_alpha),
    )
    train_mean = fmean(train_targets)
    predictions = [predict(coefficients, features) for features in test_features]
    mean_baseline = [train_mean] * len(test_rows)
    platform_average_baseline = [
        (float(row["tmdb_rating_10"]) + float(row["movielens_rating_10"])) / 2
        for row in test_rows
    ]
    model_metrics = regression_metrics(actual, predictions)
    mean_baseline_metrics = regression_metrics(actual, mean_baseline)
    platform_baseline_metrics = regression_metrics(actual, platform_average_baseline)
    feature_names = [
        "tmdb_rating_10_standardized", "movielens_rating_10_standardized",
        "log10_tmdb_vote_count_standardized",
        "log10_movielens_rating_count_standardized",
        "release_decades_since_2000_standardized",
        *(f"genre_{genre}" for genre in encoded_genres),
    ]
    coefficient_names = ["intercept", *feature_names]
    coefficient_sets = {
        str(candidate_alpha): dict(zip(
            coefficient_names,
            fit_ridge(train_features, train_targets, alpha=candidate_alpha),
        ))
        for candidate_alpha in alpha_candidates
    }
    coefficient_stability = {
        name: {
            "minimum": round(min(values), 4),
            "maximum": round(max(values), 4),
            "same_sign_across_alphas": min(values) * max(values) >= 0,
        }
        for name in coefficient_names
        for values in [[coefficient_sets[key][name] for key in coefficient_sets]]
    }
    prediction_rows = [
        {
            "movielens_id": row["movielens_id"],
            "title": row.get("title", ""),
            "release_year": int(row["release_year"]),
            "primary_genre": _primary_genre(row["genres"]),
            "movielens_rating_count_band": row.get("movielens_rating_count_band", ""),
            "actual": truth,
            "prediction": round(estimate, 4),
            "absolute_error": round(abs(truth - estimate), 4),
        }
        for row, truth, estimate in zip(test_rows, actual, predictions)
    ]
    grouped_errors = {}
    for dimension in ("primary_genre", "movielens_rating_count_band"):
        groups = sorted({str(row[dimension]) for row in prediction_rows})
        grouped_errors[dimension] = [
            {
                "group": group,
                "movie_count": len(group_rows),
                "mae": round(fmean(float(row["absolute_error"]) for row in group_rows), 4),
            }
            for group in groups
            for group_rows in [[row for row in prediction_rows if row[dimension] == group]]
            if len(group_rows) >= 5
        ]
    largest_errors = sorted(
        prediction_rows, key=lambda row: (-float(row["absolute_error"]), str(row["movielens_id"]))
    )[:10]
    return {
        "dataset": "real_v1_movie_ratings",
        "target": "imdb_rating_10",
        "evaluation_protocol": "newest_release_years_holdout",
        "train_movie_count": len(train_rows),
        "test_movie_count": len(test_rows),
        "full_outer_test_movie_count": len(full_test_rows),
        "outer_test_coverage_filter_applied": outer_test_movie_ids is not None,
        "test_year_min": min(int(row["release_year"]) for row in test_rows),
        "test_year_max": max(int(row["release_year"]) for row in test_rows),
        "ridge_alpha": selected_alpha,
        "alpha_selection": {
            "method": "newest_20_percent_of_training_rows_validation",
            "inner_training_movie_count": len(inner_train_targets),
            "validation_movie_count": len(validation_targets),
            "candidate_results": alpha_validation,
            "selected_alpha": selected_alpha,
            "outer_test_used_for_selection": False,
        },
        "preprocessing": (
            "Numeric standardization and genre categories learned separately from each "
            "training partition; validation and outer-test rows never define preprocessing."
        ),
        "reference_genre": reference_genre,
        "model_metrics": _rounded_metrics(model_metrics),
        "baselines": {
            "training_mean": _rounded_metrics(mean_baseline_metrics),
            "tmdb_movielens_average": _rounded_metrics(platform_baseline_metrics),
        },
        "mae_improvement_over_training_mean": round(
            mean_baseline_metrics["mae"] - model_metrics["mae"], 4
        ),
        "mae_improvement_over_platform_average": round(
            platform_baseline_metrics["mae"] - model_metrics["mae"], 4
        ),
        "coefficients_at_selected_alpha": {
            name: round(value, 4) for name, value in zip(coefficient_names, coefficients)
        },
        "coefficient_stability_across_alphas": coefficient_stability,
        "grouped_holdout_errors": grouped_errors,
        "largest_absolute_errors": largest_errors,
        "error_analysis_note": (
            "Large residuals identify information absent from this baseline, such as "
            "review text, audience composition, regional release context, and rating drift."
        ),
        "interpretation_note": (
            "The newest movies were held out before fitting. Ridge alpha was selected "
            "inside the older training portion without using outer-test outcomes."
        ),
    }


def _fit_real_transformer(
    training_rows: list[dict[str, str]],
) -> tuple[Callable[[dict[str, str]], list[float]], str, list[str]]:
    """Fit numeric scaling and genre encoding on one training partition only."""

    train_genres = sorted({_primary_genre(row["genres"]) for row in training_rows})
    reference_genre = train_genres[0]
    encoded_genres = train_genres[1:]
    train_numeric = [_real_numeric_features(row) for row in training_rows]
    means = [fmean(column) for column in zip(*train_numeric)]
    scales = [
        math.sqrt(fmean((value - mean) ** 2 for value in column)) or 1.0
        for column, mean in zip(zip(*train_numeric), means)
    ]

    def transform(row: dict[str, str]) -> list[float]:
        numeric = _real_numeric_features(row)
        genre = _primary_genre(row["genres"])
        return [
            *((value - mean) / scale for value, mean, scale in zip(numeric, means, scales)),
            *(1.0 if genre == candidate else 0.0 for candidate in encoded_genres),
        ]

    return transform, reference_genre, encoded_genres


def _real_numeric_features(row: dict[str, str]) -> list[float]:
    tmdb_count = int(row["tmdb_vote_count"])
    movielens_count = int(row["movielens_rating_count"])
    if tmdb_count <= 0 or movielens_count <= 0:
        raise ValueError("Rating counts must be positive before log transformation.")
    return [
        float(row["tmdb_rating_10"]),
        float(row["movielens_rating_10"]),
        math.log10(tmdb_count),
        math.log10(movielens_count),
        (int(row["release_year"]) - 2000) / 10,
    ]


def solve_linear_system(matrix: list[list[float]], vector: list[float]) -> list[float]:
    """Solve a square linear system with partial-pivot Gaussian elimination."""

    size = len(matrix)
    if size == 0 or len(vector) != size or any(len(row) != size for row in matrix):
        raise ValueError("Linear system dimensions do not match.")
    augmented = [row.copy() + [value] for row, value in zip(matrix, vector)]

    for column in range(size):
        pivot = max(range(column, size), key=lambda row: abs(augmented[row][column]))
        if abs(augmented[pivot][column]) < 1e-12:
            raise ValueError("Linear system is singular.")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]

        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                current - factor * pivot_current
                for current, pivot_current in zip(augmented[row], augmented[column])
            ]
    return [row[-1] for row in augmented]


def fit_ridge(
    features: Sequence[Sequence[float]],
    targets: Sequence[float],
    *,
    alpha: float = 1.0,
) -> list[float]:
    """Fit ridge regression; the first returned coefficient is the intercept."""

    if alpha < 0:
        raise ValueError("Ridge alpha cannot be negative.")
    if len(features) != len(targets) or len(features) < 2:
        raise ValueError("Features and targets require at least two matching rows.")
    width = len(features[0])
    if width == 0 or any(len(row) != width for row in features):
        raise ValueError("Feature rows must have one consistent positive width.")

    design = [[1.0, *map(float, row)] for row in features]
    parameter_count = width + 1
    gram = [
        [sum(row[left] * row[right] for row in design) for right in range(parameter_count)]
        for left in range(parameter_count)
    ]
    for index in range(1, parameter_count):
        gram[index][index] += alpha
    rhs = [
        sum(row[index] * target for row, target in zip(design, targets))
        for index in range(parameter_count)
    ]
    return solve_linear_system(gram, rhs)


def predict(coefficients: Sequence[float], features: Sequence[float]) -> float:
    """Return one prediction, clipped to the declared rating scale."""

    if len(coefficients) != len(features) + 1:
        raise ValueError("Coefficient and feature dimensions do not match.")
    raw_prediction = coefficients[0] + sum(
        coefficient * value
        for coefficient, value in zip(coefficients[1:], features)
    )
    return min(RATING_MAXIMUM, max(RATING_MINIMUM, raw_prediction))


def regression_metrics(actual: Sequence[float], predicted: Sequence[float]) -> dict[str, float]:
    """Return MAE, RMSE, and R-squared for matching observations."""

    if len(actual) != len(predicted) or len(actual) < 2:
        raise ValueError("Regression metrics require matching observations.")
    mean_actual = fmean(actual)
    squared_errors = [(truth - estimate) ** 2 for truth, estimate in zip(actual, predicted)]
    total_squares = sum((truth - mean_actual) ** 2 for truth in actual)
    if total_squares == 0:
        raise ValueError("R-squared is undefined for a constant target.")
    return {
        "mae": fmean(abs(truth - estimate) for truth, estimate in zip(actual, predicted)),
        "rmse": math.sqrt(fmean(squared_errors)),
        "r_squared": 1 - sum(squared_errors) / total_squares,
    }


def evaluate_prediction_model(path: Path, *, alpha: float = 1.0) -> dict[str, object]:
    """Compare ridge and training-mean predictions with leave-one-out validation."""

    dataset = load_model_dataset(path)
    model_predictions: list[float] = []
    baseline_predictions: list[float] = []
    for test_index, test_features in enumerate(dataset.features):
        train_features = [
            row for index, row in enumerate(dataset.features) if index != test_index
        ]
        train_targets = [
            target for index, target in enumerate(dataset.targets) if index != test_index
        ]
        coefficients = fit_ridge(train_features, train_targets, alpha=alpha)
        model_predictions.append(predict(coefficients, test_features))
        baseline_predictions.append(fmean(train_targets))

    model_metrics = regression_metrics(dataset.targets, model_predictions)
    baseline_metrics = regression_metrics(dataset.targets, baseline_predictions)
    final_coefficients = fit_ridge(dataset.features, dataset.targets, alpha=alpha)
    coefficient_names = ["intercept", *dataset.feature_names]

    return {
        "dataset": "fictional_demo_movie_ratings",
        "target": "imdb_rating_10",
        "rating_scale": "1–10",
        "complete_row_count": len(dataset.targets),
        "evaluation_protocol": "leave_one_out_cross_validation",
        "ridge_alpha": alpha,
        "prediction_clipped_to_scale": True,
        "baseline": "mean_imdb_rating_of_each_training_fold",
        "feature_definitions": {
            "tmdb_rating_10": "TMDB rating on the common 1–10 scale.",
            "movielens_rating_10": "MovieLens rating converted to the 1–10 scale.",
            "log10_tmdb_vote_count": "Base-10 logarithm of the TMDB vote count.",
            "log10_movielens_rating_count": (
                "Base-10 logarithm of the MovieLens rating count."
            ),
            "release_decades_since_2000": (
                "Release year centered on 2000 and measured in decades."
            ),
            "genre_indicators": (
                f"One-hot genre indicators; {dataset.reference_genre} is the "
                "reference category."
            ),
        },
        "model_metrics": _rounded_metrics(model_metrics),
        "baseline_metrics": _rounded_metrics(baseline_metrics),
        "mae_improvement_over_baseline": round(
            baseline_metrics["mae"] - model_metrics["mae"], 4
        ),
        "rmse_improvement_over_baseline": round(
            baseline_metrics["rmse"] - model_metrics["rmse"], 4
        ),
        "coefficients_fitted_on_all_complete_rows": {
            name: round(value, 4)
            for name, value in zip(coefficient_names, final_coefficients)
        },
        "cross_validation_predictions": [
            {
                "movie_id": movie_id,
                "actual_imdb_rating_10": actual,
                "model_prediction": round(model_prediction, 4),
                "baseline_prediction": round(baseline_prediction, 4),
                "model_residual_actual_minus_prediction": round(
                    actual - model_prediction, 4
                ),
            }
            for movie_id, actual, model_prediction, baseline_prediction in zip(
                dataset.movie_ids,
                dataset.targets,
                model_predictions,
                baseline_predictions,
            )
        ],
        "interpretation_note": (
            "This synthetic-data result validates the workflow only. It is not "
            "evidence of performance on real or future movies."
        ),
    }


def _rounded_metrics(metrics: dict[str, float]) -> dict[str, float]:
    return {name: round(value, 4) for name, value in metrics.items()}
