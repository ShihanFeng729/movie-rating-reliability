"""Build the frozen, local-only V1.1 review-text sample."""

from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Callable


WORD = re.compile(r"\b\w+[\w'-]*\b", re.UNICODE)
LanguageDetector = Callable[[str], str]


def build_strict_review_sample(
    ratings_path: Path,
    raw_dir: Path,
    output_path: Path,
    summary_path: Path,
    *,
    cutoff: datetime,
    language_detector: LanguageDetector | None = None,
    language_seed: int = 510,
) -> dict[str, Any]:
    """Freeze pre-cutoff English reviews by stable TMDB movie ID.

    The text-bearing output and its summary are local runtime artifacts. The
    summary deliberately contains aggregate counts and hashes, never text.
    """

    if cutoff.tzinfo is None:
        raise ValueError("cutoff must be timezone-aware")
    detector = language_detector or _langdetect_detector(language_seed)
    ratings = _read_ratings(ratings_path)
    raw_paths = sorted(raw_dir.glob("*.json"), key=lambda path: int(path.stem))
    if not raw_paths:
        raise ValueError(f"No review response files found in {raw_dir}")

    source_nonempty = 0
    missing_timestamp = 0
    after_cutoff = 0
    eligible_language_counts: Counter[str] = Counter()
    language_rejected = 0
    frozen_rows: list[dict[str, Any]] = []

    for path in raw_paths:
        tmdb_id = int(path.stem)
        if tmdb_id not in ratings:
            raise ValueError(f"TMDB ID {tmdb_id} is absent from the ratings table")
        record = json.loads(path.read_text(encoding="utf-8"))
        payload = record.get("payload", {})
        if payload.get("id") not in (None, tmdb_id):
            raise ValueError(f"TMDB ID mismatch in {path.name}")
        accepted: list[tuple[datetime, str, str]] = []
        for review in payload.get("results", []):
            if not isinstance(review, dict):
                continue
            content = str(review.get("content", "")).strip()
            if not content:
                continue
            source_nonempty += 1
            created_at = _parse_timestamp(str(review.get("created_at", "")))
            if created_at is None:
                missing_timestamp += 1
                continue
            if created_at > cutoff:
                after_cutoff += 1
                continue
            try:
                language = detector(content)
            except Exception:
                language = "undetermined"
            eligible_language_counts[language] += 1
            if language != "en":
                language_rejected += 1
                continue
            accepted.append((created_at, _text_digest(content), content))

        if not accepted:
            continue
        accepted.sort(key=lambda item: (item[0], item[1]))
        texts = [item[2] for item in accepted]
        combined = "\n\n".join(texts)
        rating = ratings[tmdb_id]
        frozen_rows.append({
            "movielens_id": rating["movielens_id"],
            "imdb_id": rating["imdb_id"],
            "tmdb_id": tmdb_id,
            "release_year": int(rating["release_year"]),
            "review_count": len(texts),
            "word_count": len(WORD.findall(combined)),
            "character_count": len(combined),
            "earliest_review_created_at_utc": accepted[0][0].isoformat(),
            "latest_review_created_at_utc": accepted[-1][0].isoformat(),
            "aggregated_review_text": combined,
        })

    frozen_rows.sort(key=lambda row: row["tmdb_id"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in frozen_rows
    )
    output_path.write_text(serialized, encoding="utf-8")
    final_review_count = sum(row["review_count"] for row in frozen_rows)
    source_movie_count = len(raw_paths)
    summary = {
        "stage": "v1_1_strict_review_sample_freeze",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "cutoff_utc": cutoff.isoformat(),
        "language_method": "langdetect_1.0.9_per_review",
        "language_seed": language_seed,
        "source_movie_count": source_movie_count,
        "source_nonempty_review_count": source_nonempty,
        "reviews_missing_created_at": missing_timestamp,
        "reviews_after_cutoff": after_cutoff,
        "time_eligible_review_count": (
            source_nonempty - missing_timestamp - after_cutoff
        ),
        "time_eligible_language_counts": dict(sorted(eligible_language_counts.items())),
        "reviews_rejected_by_language": language_rejected,
        "frozen_review_count": final_review_count,
        "frozen_movie_count": len(frozen_rows),
        "coverage_rate_over_source_movies": round(
            len(frozen_rows) / source_movie_count, 4
        ),
        "total_word_count": sum(row["word_count"] for row in frozen_rows),
        "total_character_count": sum(
            row["character_count"] for row in frozen_rows
        ),
        "output_schema": list(frozen_rows[0]) if frozen_rows else [],
        "output_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "raw_input_sha256": _combined_file_digest(raw_paths),
        "author_fields_in_output": False,
        "raw_review_text_published": False,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _read_ratings(path: Path) -> dict[int, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {"movielens_id", "imdb_id", "tmdb_id", "release_year"}
    if not rows or not required.issubset(rows[0]):
        raise ValueError(f"Ratings table must contain {sorted(required)}")
    indexed: dict[int, dict[str, str]] = {}
    for row in rows:
        tmdb_id = int(row["tmdb_id"])
        if tmdb_id in indexed:
            raise ValueError(f"Duplicate TMDB ID {tmdb_id} in ratings table")
        indexed[tmdb_id] = row
    return indexed


def _langdetect_detector(seed: int) -> LanguageDetector:
    try:
        from langdetect import DetectorFactory, detect
    except ImportError as error:
        raise RuntimeError(
            "Install the pinned dependencies from requirements-dev.txt."
        ) from error
    DetectorFactory.seed = seed
    return detect


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _text_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _combined_file_digest(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()
