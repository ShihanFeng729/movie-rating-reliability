"""Build a deterministic three-platform candidate table from local source files."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
import gzip
import hashlib
import io
import json
from pathlib import Path
from typing import Iterable, TextIO
from zipfile import ZipFile


@dataclass(frozen=True)
class RealCandidate:
    """One pre-TMDB candidate linked by stable platform identifiers."""

    movielens_id: int
    imdb_id: str
    tmdb_id: int
    title: str
    release_year: int
    genres: str
    movielens_rating_10: float
    movielens_rating_count: int
    imdb_rating_10: float
    imdb_vote_count: int
    release_decade: int
    movielens_rating_count_band: str


def build_candidate_table(
    *,
    movielens_zip: Path,
    imdb_basics_gz: Path,
    imdb_ratings_gz: Path,
    contract: dict[str, object],
    output_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    """Build, write, and summarize the contract-defined pre-TMDB sample."""

    eligibility = _mapping(contract, "eligibility")
    sample_size = _mapping(contract, "sample_size")
    thresholds = _mapping(eligibility, "minimum_votes")
    candidate_count = int(sample_size["candidate_movies"])

    rating_aggregates = aggregate_movielens_ratings(movielens_zip)
    links = load_movielens_links(movielens_zip)
    eligible_link_ids = {
        movie_id: identifiers
        for movie_id, identifiers in links.items()
        if identifiers[0]
        and identifiers[1] is not None
        and rating_aggregates.get(movie_id, (0.0, 0))[1]
        >= int(thresholds["movielens"])
    }
    wanted_imdb_ids = {identifiers[0] for identifiers in eligible_link_ids.values()}
    basics = load_imdb_basics(imdb_basics_gz, wanted_imdb_ids)
    imdb_ratings = load_imdb_ratings(imdb_ratings_gz, wanted_imdb_ids)

    eligible: list[RealCandidate] = []
    for movie_id, (imdb_id, tmdb_id) in eligible_link_ids.items():
        basic = basics.get(imdb_id)
        imdb_rating = imdb_ratings.get(imdb_id)
        if basic is None or imdb_rating is None or tmdb_id is None:
            continue
        title, title_type, is_adult, year, genres = basic
        rating, imdb_votes = imdb_rating
        if title_type != eligibility["title_type"]:
            continue
        if bool(eligibility["exclude_adult_titles"]) and is_adult:
            continue
        if not int(eligibility["release_year_min"]) <= year <= int(
            eligibility["release_year_max"]
        ):
            continue
        if imdb_votes < int(thresholds["imdb"]):
            continue
        movielens_sum, movielens_count = rating_aggregates[movie_id]
        eligible.append(
            RealCandidate(
                movielens_id=movie_id,
                imdb_id=imdb_id,
                tmdb_id=tmdb_id,
                title=title,
                release_year=year,
                genres=genres,
                movielens_rating_10=round((movielens_sum / movielens_count) * 2, 4),
                movielens_rating_count=movielens_count,
                imdb_rating_10=rating,
                imdb_vote_count=imdb_votes,
                release_decade=(year // 10) * 10,
                movielens_rating_count_band=rating_count_band(movielens_count),
            )
        )

    if len(eligible) < candidate_count:
        raise ValueError(
            f"Only {len(eligible)} eligible movies remain; {candidate_count} required."
        )
    selected = deterministic_stratified_sample(
        eligible,
        sample_size=candidate_count,
        seed=int(contract["random_seed"]),
    )
    write_candidates(output_path, selected)

    stratum_counts: dict[str, int] = {}
    for candidate in selected:
        key = (
            f"{candidate.release_decade}|"
            f"{candidate.movielens_rating_count_band}"
        )
        stratum_counts[key] = stratum_counts.get(key, 0) + 1
    summary: dict[str, object] = {
        "contract_id": contract["contract_id"],
        "stage": "pre_tmdb_candidate_selection",
        "movielens_aggregate_movie_count": len(rating_aggregates),
        "linked_movies_after_movielens_threshold": len(eligible_link_ids),
        "imdb_basics_matches": len(basics),
        "imdb_rating_matches": len(imdb_ratings),
        "eligible_movie_count": len(eligible),
        "selected_candidate_count": len(selected),
        "selected_stratum_counts": dict(sorted(stratum_counts.items())),
        "output_path": str(output_path),
        "next_filter": (
            f"TMDB vote_count >= {thresholds['tmdb']} after movie-detail collection"
        ),
        "validation_status": "passed",
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return summary


def aggregate_movielens_ratings(path: Path) -> dict[int, tuple[float, int]]:
    """Stream MovieLens ratings and return sum/count aggregates per movie."""

    totals: dict[int, list[float | int]] = {}
    with ZipFile(path) as archive, _open_zip_csv(archive, "ratings.csv") as file:
        for row in csv.DictReader(file):
            movie_id = int(row["movieId"])
            aggregate = totals.setdefault(movie_id, [0.0, 0])
            aggregate[0] = float(aggregate[0]) + float(row["rating"])
            aggregate[1] = int(aggregate[1]) + 1
    return {
        movie_id: (float(values[0]), int(values[1]))
        for movie_id, values in totals.items()
    }


def load_movielens_links(path: Path) -> dict[int, tuple[str, int | None]]:
    """Return MovieLens IDs mapped to normalized IMDb and TMDB IDs."""

    links: dict[int, tuple[str, int | None]] = {}
    with ZipFile(path) as archive, _open_zip_csv(archive, "links.csv") as file:
        for row in csv.DictReader(file):
            raw_imdb = row["imdbId"].strip()
            raw_tmdb = row["tmdbId"].strip()
            imdb_id = f"tt{raw_imdb.zfill(7)}" if raw_imdb else ""
            links[int(row["movieId"])] = (
                imdb_id,
                int(raw_tmdb) if raw_tmdb else None,
            )
    return links


def load_imdb_basics(
    path: Path,
    wanted_ids: set[str],
) -> dict[str, tuple[str, str, bool, int, str]]:
    """Stream IMDb basics and retain only linked, usable title rows."""

    basics: dict[str, tuple[str, str, bool, int, str]] = {}
    with gzip.open(path, mode="rt", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter="\t"):
            imdb_id = row["tconst"]
            if imdb_id not in wanted_ids or row["startYear"] == "\\N":
                continue
            basics[imdb_id] = (
                row["primaryTitle"],
                row["titleType"],
                row["isAdult"] == "1",
                int(row["startYear"]),
                "" if row["genres"] == "\\N" else row["genres"],
            )
    return basics


def load_imdb_ratings(
    path: Path,
    wanted_ids: set[str],
) -> dict[str, tuple[float, int]]:
    """Stream IMDb ratings and retain only linked titles."""

    ratings: dict[str, tuple[float, int]] = {}
    with gzip.open(path, mode="rt", encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter="\t"):
            imdb_id = row["tconst"]
            if imdb_id in wanted_ids:
                ratings[imdb_id] = (
                    float(row["averageRating"]),
                    int(row["numVotes"]),
                )
    return ratings


def rating_count_band(count: int) -> str:
    """Return the contract-defined MovieLens rating-count band."""

    if count < 50:
        raise ValueError("MovieLens count bands begin at 50 ratings.")
    if count < 200:
        return "50-199"
    if count < 1000:
        return "200-999"
    return "1000+"


def deterministic_stratified_sample(
    candidates: Iterable[RealCandidate],
    *,
    sample_size: int,
    seed: int,
) -> list[RealCandidate]:
    """Sample proportionally by decade/count band using stable hash ordering."""

    groups: dict[tuple[int, str], list[RealCandidate]] = {}
    for candidate in candidates:
        key = (candidate.release_decade, candidate.movielens_rating_count_band)
        groups.setdefault(key, []).append(candidate)
    population_size = sum(len(group) for group in groups.values())
    if sample_size <= 0 or sample_size > population_size:
        raise ValueError("sample_size must be positive and no larger than population.")

    quotas: dict[tuple[int, str], int] = {}
    remainders: list[tuple[float, tuple[int, str]]] = []
    for key, group in groups.items():
        exact = sample_size * len(group) / population_size
        quotas[key] = int(exact)
        remainders.append((exact - int(exact), key))
    remaining = sample_size - sum(quotas.values())
    for _, key in sorted(remainders, key=lambda item: (-item[0], item[1]))[:remaining]:
        quotas[key] += 1

    selected: list[RealCandidate] = []
    for key in sorted(groups):
        ordered = sorted(
            groups[key],
            key=lambda candidate: _stable_sample_key(seed, candidate.movielens_id),
        )
        selected.extend(ordered[: quotas[key]])
    return sorted(selected, key=lambda candidate: candidate.movielens_id)


def write_candidates(path: Path, candidates: list[RealCandidate]) -> None:
    """Write candidates as a portable CSV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(RealCandidate.__dataclass_fields__)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(asdict(candidate) for candidate in candidates)


def _open_zip_csv(archive: ZipFile, suffix: str) -> TextIO:
    matches = [name for name in archive.namelist() if name.endswith(f"/{suffix}")]
    if len(matches) != 1:
        raise ValueError(f"Expected one {suffix} file in MovieLens archive.")
    return io.TextIOWrapper(archive.open(matches[0]), encoding="utf-8", newline="")


def _stable_sample_key(seed: int, movie_id: int) -> str:
    return hashlib.sha256(f"{seed}:{movie_id}".encode()).hexdigest()


def _mapping(parent: dict[str, object], key: str) -> dict[str, object]:
    value = parent[key]
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be a mapping.")
    return value
