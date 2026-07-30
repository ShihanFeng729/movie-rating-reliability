"""Create timestamped TMDB movie snapshots."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from movie_rating_reliability.tmdb_client import TmdbClient


def snapshot_label(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def collect_discover_snapshot(
    client: TmdbClient,
    output_root: Path,
    *,
    pages: int = 1,
    start_page: int = 1,
    language: str = "en-US",
    sort_by: str = "popularity.desc",
    minimum_votes: int = 0,
    refresh: bool = False,
    collected_at: datetime | None = None,
) -> dict[str, Any]:
    """Collect discover pages into one JSONL file plus snapshot metadata."""

    if pages < 1:
        raise ValueError("pages must be at least 1.")
    if start_page < 1 or start_page + pages - 1 > 500:
        raise ValueError("Requested TMDB pages must remain between 1 and 500.")

    timestamp = collected_at or datetime.now(timezone.utc)
    snapshot_dir = output_root / snapshot_label(timestamp)
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    movies_path = snapshot_dir / "movies.jsonl"

    page_records: list[dict[str, Any]] = []
    movie_count = 0
    with movies_path.open("w", encoding="utf-8") as movie_file:
        for page in range(start_page, start_page + pages):
            payload, request_metadata = client.discover_movies(
                page=page,
                language=language,
                sort_by=sort_by,
                minimum_votes=minimum_votes,
                refresh=refresh,
            )
            results = payload.get("results", [])
            if not isinstance(results, list):
                raise ValueError("TMDB response field 'results' was not a list.")

            for movie in results:
                record = {
                    **movie,
                    "_snapshot_collected_at_utc": timestamp.isoformat(),
                    "_source_page": page,
                }
                movie_file.write(json.dumps(record, ensure_ascii=False) + "\n")
            movie_count += len(results)
            page_records.append(
                {
                    "requested_page": page,
                    "returned_page": payload.get("page"),
                    "result_count": len(results),
                    "total_pages": payload.get("total_pages"),
                    **request_metadata,
                }
            )

    metadata = {
        "dataset": "tmdb_discover_movies",
        "collected_at_utc": timestamp.isoformat(),
        "movie_count": movie_count,
        "requested_pages": pages,
        "start_page": start_page,
        "language": language,
        "sort_by": sort_by,
        "minimum_votes": minimum_votes,
        "refresh_requested": refresh,
        "pages": page_records,
        "movies_path": str(movies_path),
    }
    (snapshot_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return metadata
