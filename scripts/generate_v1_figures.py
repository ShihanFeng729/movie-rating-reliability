#!/usr/bin/env python3
"""Rebuild the two published aggregate V1 result figures."""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.figure_generation import (  # noqa: E402
    write_horizontal_bar_chart,
)


def main() -> None:
    generated = PROJECT_ROOT / "reports" / "generated"
    figures = PROJECT_ROOT / "reports" / "figures"
    reliability = json.loads(
        (generated / "v1_reliability_summary.json").read_text(encoding="utf-8")
    )
    prediction = json.loads(
        (generated / "v1_prediction_summary.json").read_text(encoding="utf-8")
    )
    pair_rows = [
        (
            f"{item['left_platform'].upper()} – {item['right_platform'].upper()}",
            float(item["mean_absolute_error"]),
        )
        for item in reliability["pairwise_metrics"]
    ]
    write_horizontal_bar_chart(
        figures / "v1_pairwise_mae.svg",
        title="Cross-platform rating disagreement",
        subtitle="Mean absolute error across 941 matched movies · lower is closer",
        rows=pair_rows,
        maximum=0.42,
        accent="#4f6bed",
    )
    write_horizontal_bar_chart(
        figures / "v1_model_mae.svg",
        title="IMDb prediction on newer movies",
        subtitle="Temporal holdout of 189 movies from 2015–2022 · lower is better",
        rows=[
            ("Training mean", float(prediction["baselines"]["training_mean"]["mae"])),
            (
                "TMDB + MovieLens average",
                float(prediction["baselines"]["tmdb_movielens_average"]["mae"]),
            ),
            ("Ridge", float(prediction["model_metrics"]["mae"])),
        ],
        maximum=0.8,
        accent="#1f9d78",
    )
    print("Wrote two aggregate V1 SVG figures.")


if __name__ == "__main__":
    main()
