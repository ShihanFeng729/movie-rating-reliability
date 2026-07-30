#!/usr/bin/env python3
"""Command-line entry point for downloading project data."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.data_download import download_datasets  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download IMDb and MovieLens source files into data/external."
    )
    parser.add_argument(
        "--skip-imdb",
        action="store_true",
        help="Do not download the two IMDb files.",
    )
    parser.add_argument(
        "--movielens",
        choices=("none", "small", "research"),
        default="small",
        help="Choose no MovieLens file, the small development file, or MovieLens 32M.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace files that already exist.",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "external",
        help="Directory where downloaded files and their manifest are stored.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = download_datasets(
        args.data_dir,
        include_imdb=not args.skip_imdb,
        movielens=args.movielens,
        overwrite=args.overwrite,
    )

    if not records:
        print("No datasets selected. An empty manifest was created.")
        return

    for record in records:
        size_mb = int(record["size_bytes"]) / (1024 * 1024)
        print(
            f"{record['status']:>10}  {record['dataset']}/{record['filename']}  "
            f"({size_mb:.1f} MB)"
        )
    print(f"Manifest saved to: {args.data_dir / 'download_manifest.json'}")


if __name__ == "__main__":
    main()
