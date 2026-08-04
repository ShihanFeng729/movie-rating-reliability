#!/usr/bin/env python3
"""Run the complete credential-free project demo."""

from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.demo_pipeline import run_demo_pipeline  # noqa: E402


def main() -> None:
    summary = run_demo_pipeline(PROJECT_ROOT)
    print("Demo pipeline completed successfully.")
    print(f"Movies: {summary['row_count']}")
    print(f"Complete across all platforms: {summary['complete_row_count']}")
    print(f"Data: {summary['data_path']}")
    print(f"Summary: {summary['report_path']}")
    print(f"Reliability metrics: {summary['evaluation_path']}")
    print(f"Prediction evaluation: {summary['prediction_path']}")


if __name__ == "__main__":
    main()
