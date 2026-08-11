"""Download public movie-rating datasets without committing large data files."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import ssl
import time
from typing import BinaryIO, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class DatasetFile:
    """Description of one downloadable source file."""

    dataset: str
    filename: str
    url: str
    note: str


IMDB_FILES = (
    DatasetFile(
        dataset="imdb",
        filename="title.basics.tsv.gz",
        url="https://datasets.imdbws.com/title.basics.tsv.gz",
        note="Movie identifiers, titles, years, genres, and title types.",
    ),
    DatasetFile(
        dataset="imdb",
        filename="title.ratings.tsv.gz",
        url="https://datasets.imdbws.com/title.ratings.tsv.gz",
        note="IMDb average ratings and vote counts.",
    ),
)

MOVIELENS_FILES = {
    "small": DatasetFile(
        dataset="movielens",
        filename="ml-latest-small.zip",
        url="https://files.grouplens.org/datasets/movielens/ml-latest-small.zip",
        note="Small development dataset; convenient for learning and fast tests.",
    ),
    "research": DatasetFile(
        dataset="movielens",
        filename="ml-32m.zip",
        url="https://files.grouplens.org/datasets/movielens/ml-32m.zip",
        note="Stable MovieLens 32M research dataset for full analysis.",
    ),
}

StreamOpener = Callable[[str, int], BinaryIO]
Sleeper = Callable[[float], None]


def _open_url(url: str, timeout: int) -> BinaryIO:
    request = Request(
        url,
        headers={"User-Agent": "movie-rating-reliability/0.1 (research project)"},
    )
    return urlopen(request, timeout=timeout, context=_default_ssl_context())


def _default_ssl_context() -> ssl.SSLContext:
    """Use verified HTTPS, including the macOS system bundle when needed."""

    verify_paths = ssl.get_default_verify_paths()
    system_bundle = Path("/etc/ssl/cert.pem")
    if verify_paths.cafile is None and verify_paths.capath is None:
        if system_bundle.is_file():
            return ssl.create_default_context(cafile=str(system_bundle))
    return ssl.create_default_context()


def sha256_file(path: Path) -> str:
    """Return a SHA-256 checksum so a downloaded file can be verified."""

    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    source: DatasetFile,
    data_dir: Path,
    *,
    overwrite: bool = False,
    timeout: int = 60,
    opener: StreamOpener = _open_url,
    attempts: int = 3,
    sleeper: Sleeper = time.sleep,
) -> dict[str, object]:
    """Download one source safely and return its metadata."""

    destination = data_dir / source.dataset / source.filename
    destination.parent.mkdir(parents=True, exist_ok=True)

    if attempts < 1:
        raise ValueError("attempts must be positive.")

    status = "downloaded"
    if destination.exists() and not overwrite:
        status = "existing"
    else:
        partial = destination.with_suffix(destination.suffix + ".part")
        for attempt in range(1, attempts + 1):
            try:
                with opener(source.url, timeout) as response, partial.open(
                    "wb"
                ) as output:
                    shutil.copyfileobj(response, output)
                partial.replace(destination)
                break
            except Exception as error:
                partial.unlink(missing_ok=True)
                if attempt == attempts or not _is_retryable_download_error(error):
                    raise
                sleeper(float(2 ** (attempt - 1)))

    return {
        **asdict(source),
        "path": str(destination),
        "status": status,
        "size_bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _is_retryable_download_error(error: Exception) -> bool:
    if isinstance(error, HTTPError):
        return error.code in {408, 429} or 500 <= error.code < 600
    return isinstance(error, (URLError, TimeoutError, ConnectionError, ssl.SSLError))


def selected_sources(*, include_imdb: bool, movielens: str) -> list[DatasetFile]:
    """Build the list of files requested by the command-line options."""

    sources = list(IMDB_FILES) if include_imdb else []
    if movielens != "none":
        sources.append(MOVIELENS_FILES[movielens])
    return sources


def download_datasets(
    data_dir: Path,
    *,
    include_imdb: bool = True,
    movielens: str = "small",
    overwrite: bool = False,
    timeout: int = 60,
    opener: StreamOpener = _open_url,
) -> list[dict[str, object]]:
    """Download selected datasets and save a machine-readable manifest."""

    records = [
        download_file(
            source,
            data_dir,
            overwrite=overwrite,
            timeout=timeout,
            opener=opener,
        )
        for source in selected_sources(
            include_imdb=include_imdb,
            movielens=movielens,
        )
    ]

    data_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = data_dir / "download_manifest.json"
    manifest_path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return records
