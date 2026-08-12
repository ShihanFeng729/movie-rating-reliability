from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.source_manifest import (  # noqa: E402
    build_v1_source_manifest,
)


class SourceManifestTests(unittest.TestCase):
    def test_manifest_normalizes_paths_and_excludes_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            external = root / "data" / "external"
            external.mkdir(parents=True)
            (external / "download_manifest.json").write_text(json.dumps([{
                "dataset": "movielens", "filename": "ml-32m.zip",
                "url": "https://example.test/ml-32m.zip",
                "path": "/private/machine/path/ml-32m.zip",
                "size_bytes": 10, "sha256": "a" * 64,
                "recorded_at_utc": "2026-08-11T00:00:00+00:00",
            }]))
            items = root / "data" / "raw" / "tmdb" / "v1_candidates" / "items"
            items.mkdir(parents=True)
            (items / "1.json").write_text(json.dumps({
                "payload": {"id": 1},
                "request": {"fetched_at_utc": "2026-08-12T00:00:00+00:00"},
            }))
            reports = root / "reports" / "generated"
            reports.mkdir(parents=True)
            (reports / "v1_tmdb_collection.json").write_text(
                json.dumps({"failed_this_run": 1})
            )
            manifest = build_v1_source_manifest(
                root, generated_at=datetime(2026, 8, 12, tzinfo=timezone.utc)
            )
            text = json.dumps(manifest)
            self.assertEqual(
                manifest["static_sources"][0]["local_path"],
                "data/external/movielens/ml-32m.zip",
            )
            self.assertEqual(manifest["api_source"]["successful_response_count"], 1)
            self.assertFalse(manifest["api_source"]["credential_recorded"])
            self.assertNotIn("private/machine", text)
            self.assertNotIn("token", text.lower())
