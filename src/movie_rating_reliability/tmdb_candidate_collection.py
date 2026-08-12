"""Collect TMDB details for a fixed candidate table with resumable outputs."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Protocol


class MovieDetailsClient(Protocol):
    def movie_details(
        self, tmdb_id: int, *, language: str, refresh: bool
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...


def collect_candidate_details(
    client: MovieDetailsClient,
    candidate_path: Path,
    output_dir: Path,
    processed_path: Path,
    summary_path: Path,
    *,
    tmdb_minimum_votes: int,
    target_complete: int,
    minimum_complete: int,
    expected_candidates: int,
    language: str = "en-US",
    refresh: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Collect details, preserve progress, and write the complete joined table."""

    candidates = _read_candidates(candidate_path)
    if len(candidates) != expected_candidates:
        raise ValueError(
            f"Candidate table has {len(candidates)} rows; expected {expected_candidates}."
        )
    ids = [int(row["tmdb_id"]) for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate table contains duplicate TMDB IDs.")
    if tmdb_minimum_votes < 0:
        raise ValueError("TMDB minimum votes cannot be negative.")

    items_dir = output_dir / "items"
    items_dir.mkdir(parents=True, exist_ok=True)
    attempted = candidates[:limit] if limit is not None else candidates
    succeeded = 0
    reused = 0
    failures: list[dict[str, object]] = []

    for candidate in attempted:
        tmdb_id = int(candidate["tmdb_id"])
        item_path = items_dir / f"{tmdb_id}.json"
        if item_path.exists() and not refresh:
            try:
                record = json.loads(item_path.read_text(encoding="utf-8"))
                if int(record["payload"]["id"]) == tmdb_id:
                    reused += 1
                    continue
            except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
                pass
        try:
            payload, request_metadata = client.movie_details(
                tmdb_id, language=language, refresh=refresh
            )
            if int(payload.get("id", -1)) != tmdb_id:
                raise ValueError("TMDB response ID did not match the requested ID.")
            record = {"payload": payload, "request": request_metadata}
            item_path.write_text(
                json.dumps(record, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            succeeded += 1
        except Exception as error:  # Continue so one unavailable movie does not lose progress.
            failures.append(
                {
                    "tmdb_id": tmdb_id,
                    "error_type": type(error).__name__,
                    "message": str(error),
                }
            )

    complete_rows = _join_complete_rows(
        candidates, items_dir, tmdb_minimum_votes=tmdb_minimum_votes
    )
    _write_processed(processed_path, complete_rows)

    complete_count = len(complete_rows)
    if complete_count >= target_complete:
        status = "target_met"
    elif complete_count >= minimum_complete:
        status = "minimum_met"
    else:
        status = "below_minimum"
    summary: dict[str, Any] = {
        "stage": "tmdb_candidate_detail_collection",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(candidates),
        "attempted_this_run": len(attempted),
        "fetched_this_run": succeeded,
        "reused_this_run": reused,
        "failed_this_run": len(failures),
        "failures": failures,
        "tmdb_minimum_votes": tmdb_minimum_votes,
        "complete_movie_count": complete_count,
        "target_complete_movies": target_complete,
        "minimum_complete_movies": minimum_complete,
        "validation_status": status,
        "processed_path": str(processed_path),
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def _read_candidates(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    required = {
        "movielens_id", "imdb_id", "tmdb_id", "title", "release_year",
        "genres", "movielens_rating_10", "movielens_rating_count",
        "imdb_rating_10", "imdb_vote_count", "release_decade",
        "movielens_rating_count_band",
    }
    if not rows or not required.issubset(rows[0]):
        raise ValueError("Candidate table is empty or missing required columns.")
    return rows


def _join_complete_rows(
    candidates: list[dict[str, str]], items_dir: Path, *, tmdb_minimum_votes: int
) -> list[dict[str, object]]:
    complete: list[dict[str, object]] = []
    for candidate in candidates:
        path = items_dir / f"{candidate['tmdb_id']}.json"
        if not path.exists():
            continue
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            payload = record["payload"]
            if int(payload["id"]) != int(candidate["tmdb_id"]):
                continue
            vote_count = int(payload["vote_count"])
            vote_average = float(payload["vote_average"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, OSError):
            continue
        if vote_count < tmdb_minimum_votes:
            continue
        genres = payload.get("genres", [])
        tmdb_genres = "|".join(
            str(genre["name"]) for genre in genres
            if isinstance(genre, dict) and genre.get("name")
        )
        complete.append(
            {
                **candidate,
                "tmdb_rating_10": vote_average,
                "tmdb_vote_count": vote_count,
                "tmdb_popularity": payload.get("popularity", ""),
                "tmdb_title": payload.get("title", ""),
                "tmdb_release_date": payload.get("release_date", ""),
                "tmdb_genres": tmdb_genres,
                "tmdb_fetched_at_utc": record.get("request", {}).get(
                    "fetched_at_utc", ""
                ),
            }
        )
    return complete


def _write_processed(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "movielens_id", "imdb_id", "tmdb_id", "title", "release_year",
        "genres", "movielens_rating_10", "movielens_rating_count",
        "imdb_rating_10", "imdb_vote_count", "release_decade",
        "movielens_rating_count_band", "tmdb_rating_10", "tmdb_vote_count",
        "tmdb_popularity", "tmdb_title", "tmdb_release_date", "tmdb_genres",
        "tmdb_fetched_at_utc",
    ]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
