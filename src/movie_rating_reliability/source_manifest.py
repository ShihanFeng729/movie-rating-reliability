"""Build an auditable source manifest without exposing secrets or raw data."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any


MOVIELENS_32M_OFFICIAL_MD5 = "d472be332d4daa821edc399621853b57"


def build_v1_source_manifest(
    project_root: Path,
    *,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Combine static-download and TMDB collection metadata into one manifest."""

    external_root = project_root / "data" / "external"
    download_path = external_root / "download_manifest.json"
    downloads = json.loads(download_path.read_text(encoding="utf-8"))
    static_sources = []
    for record in downloads:
        filename = str(record["filename"])
        relative_path = (
            Path("data") / "external" / str(record["dataset"]) / filename
        )
        item = {
            "source": record["dataset"],
            "dataset_or_version": (
                "MovieLens 32M (generated 2023-10-13)"
                if filename == "ml-32m.zip"
                else "IMDb non-commercial dataset (daily snapshot)"
            ),
            "filename": filename,
            "url": record["url"],
            "local_path": str(relative_path),
            "reference_time": (
                "2023-10-13"
                if filename == "ml-32m.zip"
                else record["recorded_at_utc"]
            ),
            "recorded_at_utc": record["recorded_at_utc"],
            "size_bytes": int(record["size_bytes"]),
            "sha256": record["sha256"],
        }
        if filename == "ml-32m.zip":
            item["official_md5"] = MOVIELENS_32M_OFFICIAL_MD5
        static_sources.append(item)

    items_dir = project_root / "data" / "raw" / "tmdb" / "v1_candidates" / "items"
    item_paths = sorted(items_dir.glob("*.json"), key=lambda path: int(path.stem))
    if not item_paths:
        raise ValueError("No TMDB candidate detail records were found.")
    digest = hashlib.sha256()
    fetched_times: list[str] = []
    total_size = 0
    for path in item_paths:
        content = path.read_bytes()
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
        total_size += len(content)
        record = json.loads(content)
        fetched_times.append(str(record["request"]["fetched_at_utc"]))

    collection_summary = json.loads(
        (project_root / "reports" / "generated" / "v1_tmdb_collection.json")
        .read_text(encoding="utf-8")
    )
    tmdb_source = {
        "source": "tmdb",
        "dataset_or_version": "TMDB API v3 movie details",
        "endpoint_template": "https://api.themoviedb.org/3/movie/{tmdb_id}",
        "language": "en-US",
        "reference_time_start_utc": min(fetched_times),
        "reference_time_end_utc": max(fetched_times),
        "successful_response_count": len(item_paths),
        "failed_response_count": int(collection_summary["failed_this_run"]),
        "total_response_size_bytes": total_size,
        "collection_sha256": digest.hexdigest(),
        "credential_recorded": False,
    }
    return {
        "manifest_version": "1.0",
        "contract_id": "real_snapshot_v1",
        "generated_at_utc": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "static_sources": static_sources,
        "api_source": tmdb_source,
        "temporal_alignment": (
            "Source reference times differ; ratings are not a simultaneous snapshot."
        ),
    }


def write_v1_source_manifest(project_root: Path, output_path: Path) -> dict[str, Any]:
    manifest = build_v1_source_manifest(project_root)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
