"""Audit and freeze the V1 analysis-ready movie-rating dataset."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


ID_COLUMNS = ("movielens_id", "imdb_id", "tmdb_id")
RATING_COLUMNS = ("movielens_rating_10", "imdb_rating_10", "tmdb_rating_10")
REVIEW_FIELDS = (
    "movielens_id", "imdb_id", "tmdb_id", "candidate_title",
    "candidate_year", "tmdb_title", "tmdb_year", "review_reason",
)
REJECTION_FIELDS = ("movielens_id", "imdb_id", "tmdb_id", "reason", "detail")


def audit_v1_dataset(
    *,
    candidate_path: Path,
    items_dir: Path,
    processed_path: Path,
    collection_summary_path: Path,
    source_manifest_path: Path,
    report_path: Path,
    review_path: Path,
    rejection_path: Path,
    freeze_path: Path,
    tmdb_minimum_votes: int = 50,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Write quality, rejection, review, and frozen-dataset metadata outputs."""

    candidates = _read_csv(candidate_path)
    processed = _read_csv(processed_path)
    candidate_by_tmdb = {row["tmdb_id"]: row for row in candidates}
    if len(candidate_by_tmdb) != len(candidates):
        raise ValueError("Candidate TMDB IDs are not unique.")

    responses: dict[str, dict[str, Any]] = {}
    invalid_responses: list[str] = []
    for path in items_dir.glob("*.json"):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            payload = record["payload"]
            tmdb_id = str(int(payload["id"]))
            if tmdb_id != path.stem or tmdb_id in responses:
                raise ValueError
            responses[tmdb_id] = record
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            invalid_responses.append(path.name)

    rejections: list[dict[str, str]] = []
    year_diagnostics: list[dict[str, object]] = []
    stable_imdb_mismatches = 0
    for tmdb_id, candidate in candidate_by_tmdb.items():
        record = responses.get(tmdb_id)
        if record is None:
            rejections.append(_rejection(candidate, "tmdb_unavailable", "No valid response"))
            continue
        payload = record["payload"]
        if str(payload.get("imdb_id", "")) != candidate["imdb_id"]:
            stable_imdb_mismatches += 1
        if int(payload.get("vote_count", -1)) < tmdb_minimum_votes:
            rejections.append(
                _rejection(
                    candidate,
                    "tmdb_vote_count_below_threshold",
                    str(payload.get("vote_count", "missing")),
                )
            )
        release_date = str(payload.get("release_date", ""))
        if len(release_date) >= 4 and release_date[:4].isdigit():
            year_difference = int(release_date[:4]) - int(candidate["release_year"])
            if abs(year_difference) > 1:
                year_diagnostics.append(
                    {
                        "tmdb_id": int(tmdb_id),
                        "candidate_year": int(candidate["release_year"]),
                        "tmdb_year": int(release_date[:4]),
                        "difference": year_difference,
                        "resolution": "accepted_shared_imdb_id",
                    }
                )

    duplicate_counts = {
        column: len(processed) - len({row[column] for row in processed})
        for column in ID_COLUMNS
    }
    missing_counts = {
        column: sum(not row[column].strip() for row in processed)
        for column in processed[0]
    }
    out_of_range_counts = {
        column: sum(not 1 <= float(row[column]) <= 10 for row in processed)
        for column in RATING_COLUMNS
    }
    processed_ids = {row["tmdb_id"] for row in processed}
    expected_ids = {
        tmdb_id for tmdb_id, record in responses.items()
        if int(record["payload"].get("vote_count", -1)) >= tmdb_minimum_votes
        and tmdb_id in candidate_by_tmdb
    }
    manual_review: list[dict[str, str]] = []
    if stable_imdb_mismatches:
        for tmdb_id, record in responses.items():
            candidate = candidate_by_tmdb.get(tmdb_id)
            if candidate and str(record["payload"].get("imdb_id", "")) != candidate["imdb_id"]:
                payload = record["payload"]
                manual_review.append({
                    "movielens_id": candidate["movielens_id"],
                    "imdb_id": candidate["imdb_id"],
                    "tmdb_id": tmdb_id,
                    "candidate_title": candidate["title"],
                    "candidate_year": candidate["release_year"],
                    "tmdb_title": str(payload.get("title", "")),
                    "tmdb_year": str(payload.get("release_date", ""))[:4],
                    "review_reason": "stable_imdb_id_mismatch",
                })

    validation_checks = {
        "candidate_count_is_1000": len(candidates) == 1000,
        "processed_ids_match_eligible_responses": processed_ids == expected_ids,
        "all_ids_unique": all(count == 0 for count in duplicate_counts.values()),
        "no_missing_processed_fields": all(count == 0 for count in missing_counts.values()),
        "ratings_within_1_to_10": all(count == 0 for count in out_of_range_counts.values()),
        "no_invalid_response_files": not invalid_responses,
        "no_stable_id_mismatches": stable_imdb_mismatches == 0,
    }
    report: dict[str, Any] = {
        "stage": "v1_data_integration_quality_audit",
        "generated_at_utc": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "candidate_count": len(candidates),
        "valid_tmdb_response_count": len(responses),
        "processed_complete_count": len(processed),
        "coverage_rate_from_candidates": round(len(processed) / len(candidates), 4),
        "rejected_count": len(rejections),
        "rejection_reason_counts": _counts(row["reason"] for row in rejections),
        "duplicate_counts": duplicate_counts,
        "missing_counts": missing_counts,
        "out_of_range_rating_counts": out_of_range_counts,
        "stable_imdb_id_mismatch_count": stable_imdb_mismatches,
        "release_year_diagnostic_count": len(year_diagnostics),
        "release_year_diagnostics": year_diagnostics,
        "manual_review_count": len(manual_review),
        "invalid_response_files": sorted(invalid_responses),
        "validation_checks": validation_checks,
        "validation_status": "passed" if all(validation_checks.values()) else "failed",
        "matching_policy": "stable MovieLens-to-IMDb-to-TMDB identifiers only",
    }
    _write_json(report_path, report)
    _write_csv(review_path, REVIEW_FIELDS, manual_review)
    _write_csv(rejection_path, REJECTION_FIELDS, rejections)

    collection_summary = json.loads(collection_summary_path.read_text(encoding="utf-8"))
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8"))
    freeze = {
        "freeze_version": "v1.0",
        "contract_id": "real_snapshot_v1",
        "row_count": len(processed),
        "column_count": len(processed[0]),
        "columns": list(processed[0]),
        "processed_relative_path": "data/processed/v1_movie_ratings.csv",
        "processed_sha256": _sha256(processed_path),
        "candidate_sha256": _sha256(candidate_path),
        "tmdb_collection_sha256": source_manifest["api_source"]["collection_sha256"],
        "tmdb_collection_generated_at_utc": collection_summary["generated_at_utc"],
        "quality_report_sha256": _sha256(report_path),
        "quality_validation_status": report["validation_status"],
        "generation_entrypoint": "scripts/collect_candidate_tmdb.py",
        "audit_entrypoint": "scripts/audit_real_v1.py",
    }
    _write_json(freeze_path, freeze)
    return report


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError(f"CSV contains no data rows: {path}")
    return rows


def _rejection(candidate: dict[str, str], reason: str, detail: str) -> dict[str, str]:
    return {
        "movielens_id": candidate["movielens_id"],
        "imdb_id": candidate["imdb_id"],
        "tmdb_id": candidate["tmdb_id"],
        "reason": reason,
        "detail": detail,
    }


def _counts(values: Any) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
