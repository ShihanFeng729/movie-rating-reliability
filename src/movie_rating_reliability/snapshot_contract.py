"""Load and validate the first real-data snapshot contract."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EXPECTED_IDENTIFIERS = {"movielens_id", "imdb_id", "tmdb_id"}
EXPECTED_SOURCES = {"movielens", "imdb", "tmdb"}


def load_snapshot_contract(path: Path) -> dict[str, Any]:
    """Read a JSON contract, validate its invariants, and return it."""

    contract = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(contract, dict):
        raise ValueError("Snapshot contract must be a JSON object.")
    validate_snapshot_contract(contract)
    return contract


def validate_snapshot_contract(contract: dict[str, Any]) -> None:
    """Reject sample definitions that cannot support the planned analysis."""

    if contract.get("sampling_frame") != "movielens_32m":
        raise ValueError("V1 sampling frame must be MovieLens 32M.")

    sample_size = _mapping(contract, "sample_size")
    candidate_count = _positive_integer(sample_size, "candidate_movies")
    target_count = _positive_integer(sample_size, "target_complete_movies")
    minimum_count = _positive_integer(sample_size, "minimum_complete_movies")
    if not minimum_count <= target_count <= candidate_count:
        raise ValueError(
            "Sample sizes must satisfy minimum <= target <= candidates."
        )
    if minimum_count < 500:
        raise ValueError("V1 requires at least 500 complete movies.")

    eligibility = _mapping(contract, "eligibility")
    minimum_year = _positive_integer(eligibility, "release_year_min")
    maximum_year = _positive_integer(eligibility, "release_year_max")
    if minimum_year > maximum_year:
        raise ValueError("Release-year range is reversed.")
    identifiers = set(eligibility.get("required_identifiers", []))
    if identifiers != EXPECTED_IDENTIFIERS:
        raise ValueError("All three stable platform identifiers are required.")

    vote_thresholds = _mapping(eligibility, "minimum_votes")
    for source in EXPECTED_SOURCES:
        _positive_integer(vote_thresholds, source)

    sources = _mapping(contract, "sources")
    if set(sources) != EXPECTED_SOURCES:
        raise ValueError("Contract must define MovieLens, IMDb, and TMDB sources.")

    strategy = _mapping(contract, "sampling_strategy")
    if strategy.get("method") != "deterministic_stratified_random_sample":
        raise ValueError("V1 requires deterministic stratified sampling.")
    seed = contract.get("random_seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("random_seed must be an integer.")

    split = _mapping(contract, "evaluation_split")
    test_fraction = split.get("test_fraction")
    if not isinstance(test_fraction, (int, float)) or isinstance(test_fraction, bool):
        raise ValueError("test_fraction must be numeric.")
    if not 0 < float(test_fraction) < 0.5:
        raise ValueError("test_fraction must be greater than 0 and less than 0.5.")
    minimum_test = _positive_integer(split, "minimum_test_movies")
    if int(minimum_count * float(test_fraction)) < minimum_test:
        raise ValueError("Minimum complete sample cannot supply the planned test set.")

    alignment = _mapping(contract, "temporal_alignment")
    if alignment.get("status") != "source_reference_times_differ":
        raise ValueError("The source reference-time mismatch must be explicit.")


def summarize_snapshot_contract(contract: dict[str, Any]) -> dict[str, object]:
    """Return the decisions most useful at the command line."""

    sample_size = contract["sample_size"]
    eligibility = contract["eligibility"]
    return {
        "contract_id": contract["contract_id"],
        "candidate_movies": sample_size["candidate_movies"],
        "target_complete_movies": sample_size["target_complete_movies"],
        "minimum_complete_movies": sample_size["minimum_complete_movies"],
        "release_year_range": (
            f"{eligibility['release_year_min']}–{eligibility['release_year_max']}"
        ),
        "sampling_frame": contract["sampling_frame"],
        "validation_status": "passed",
    }


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a JSON object.")
    return value


def _positive_integer(parent: dict[str, Any], key: str) -> int:
    value = parent.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{key} must be a positive integer.")
    return value
