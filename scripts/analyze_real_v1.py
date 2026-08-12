#!/usr/bin/env python3
"""Generate V1 reliability and temporal Ridge reports from the real snapshot."""

from __future__ import annotations

import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.evaluation import evaluate_rating_csv  # noqa: E402
from movie_rating_reliability.modeling import evaluate_temporal_holdout  # noqa: E402


def main() -> None:
    data_path = PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv"
    if not data_path.exists():
        raise SystemExit("Real V1 dataset is missing. Run collect_candidate_tmdb.py first.")
    report_dir = PROJECT_ROOT / "reports" / "generated"
    report_dir.mkdir(parents=True, exist_ok=True)
    reliability = evaluate_rating_csv(data_path)
    prediction = evaluate_temporal_holdout(data_path)
    for name, report in (
        ("v1_reliability_summary.json", reliability),
        ("v1_prediction_summary.json", prediction),
    ):
        (report_dir / name).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(f"Analyzed {reliability['row_count']} complete real movies.")
    print(json.dumps(prediction["model_metrics"], indent=2))


if __name__ == "__main__":
    main()
