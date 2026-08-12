#!/usr/bin/env python3
"""Build the local V1 source provenance manifest."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.source_manifest import (  # noqa: E402
    write_v1_source_manifest,
)


def main() -> None:
    output = PROJECT_ROOT / "reports" / "generated" / "v1_source_manifest.json"
    manifest = write_v1_source_manifest(PROJECT_ROOT, output)
    print(f"Recorded {len(manifest['static_sources'])} static files.")
    print(
        f"Recorded {manifest['api_source']['successful_response_count']} "
        "TMDB responses."
    )
    print(f"Manifest: {output}")


if __name__ == "__main__":
    main()
