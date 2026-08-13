#!/usr/bin/env python3
"""Audit and freeze the local real V1 dataset."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.data_audit import audit_v1_dataset  # noqa: E402


def main() -> None:
    reports = PROJECT_ROOT / "reports" / "generated"
    report = audit_v1_dataset(
        candidate_path=PROJECT_ROOT / "data" / "interim" / "v1_candidates.csv",
        items_dir=PROJECT_ROOT / "data" / "raw" / "tmdb" / "v1_candidates" / "items",
        processed_path=PROJECT_ROOT / "data" / "processed" / "v1_movie_ratings.csv",
        collection_summary_path=reports / "v1_tmdb_collection.json",
        source_manifest_path=reports / "v1_source_manifest.json",
        report_path=reports / "v1_data_quality.json",
        review_path=reports / "v1_manual_review.csv",
        rejection_path=reports / "v1_rejections.csv",
        freeze_path=reports / "v1_dataset_freeze.json",
    )
    print(f"Audited {report['processed_complete_count']} complete rows.")
    print(f"Rejected candidates: {report['rejected_count']}")
    print(f"Manual review rows: {report['manual_review_count']}")
    print(f"Validation: {report['validation_status']}")


if __name__ == "__main__":
    main()
