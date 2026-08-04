"""Conservative cross-platform movie matching."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Callable
import unicodedata


@dataclass(frozen=True)
class MovieRecord:
    """Minimal source record used by the matching layer."""

    source_id: str
    title: str
    release_year: int | None
    imdb_id: str | int | None = None
    tmdb_id: str | int | None = None


@dataclass(frozen=True)
class MovieMatch:
    left_source_id: str
    right_source_id: str
    method: str
    confidence: str


@dataclass(frozen=True)
class MatchReport:
    matches: tuple[MovieMatch, ...]
    unmatched_left_ids: tuple[str, ...]
    ambiguous_left_ids: tuple[str, ...]


def normalize_imdb_id(value: str | int | None) -> str | None:
    """Normalize IMDb strings and MovieLens numeric IDs to `tt` format."""

    if value is None:
        return None
    digits = str(value).strip().lower()
    if digits.startswith("tt"):
        digits = digits[2:]
    if not digits.isdigit():
        return None
    return f"tt{digits.zfill(7)}"


def normalize_tmdb_id(value: str | int | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return str(int(text)) if text.isdigit() else None


def normalize_title(title: str) -> str:
    """Create a comparison key without punctuation, accents, or casing."""

    decomposed = unicodedata.normalize("NFKD", title.casefold())
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    tokens = re.findall(r"[a-z0-9]+", ascii_text)
    return " ".join(tokens)


def match_catalogs(
    left_records: list[MovieRecord],
    right_records: list[MovieRecord],
    *,
    year_tolerance: int = 1,
) -> MatchReport:
    """Match two catalogs while rejecting conflicts and ambiguous candidates."""

    if year_tolerance < 0:
        raise ValueError("year_tolerance cannot be negative.")

    imdb_index = _index(right_records, lambda movie: normalize_imdb_id(movie.imdb_id))
    tmdb_index = _index(right_records, lambda movie: normalize_tmdb_id(movie.tmdb_id))
    title_index = _index(right_records, lambda movie: normalize_title(movie.title))

    matches: list[MovieMatch] = []
    unmatched: list[str] = []
    ambiguous: list[str] = []
    used_right_ids: set[str] = set()

    for left in left_records:
        id_candidates_by_method: dict[str, set[str]] = {}
        imdb_id = normalize_imdb_id(left.imdb_id)
        tmdb_id = normalize_tmdb_id(left.tmdb_id)
        if imdb_id and imdb_id in imdb_index:
            id_candidates_by_method["imdb_id"] = {
                movie.source_id for movie in imdb_index[imdb_id]
            }
        if tmdb_id and tmdb_id in tmdb_index:
            id_candidates_by_method["tmdb_id"] = {
                movie.source_id for movie in tmdb_index[tmdb_id]
            }

        if id_candidates_by_method:
            candidates = set.union(*id_candidates_by_method.values())
            if len(candidates) == 1:
                right_id = next(iter(candidates))
                if right_id in used_right_ids:
                    ambiguous.append(left.source_id)
                    continue
                methods = [
                    method
                    for method, method_candidates in id_candidates_by_method.items()
                    if right_id in method_candidates
                ]
                matches.append(
                    MovieMatch(
                        left.source_id,
                        right_id,
                        "+".join(methods),
                        "high",
                    )
                )
                used_right_ids.add(right_id)
                continue

            ambiguous.append(left.source_id)
            continue

        title_candidates = title_index.get(normalize_title(left.title), [])
        compatible = [
            right
            for right in title_candidates
            if _years_compatible(left.release_year, right.release_year, year_tolerance)
            and right.source_id not in used_right_ids
        ]
        if len(compatible) == 1:
            right_id = compatible[0].source_id
            matches.append(
                MovieMatch(left.source_id, right_id, "title_year", "medium")
            )
            used_right_ids.add(right_id)
        elif len(compatible) > 1:
            ambiguous.append(left.source_id)
        else:
            unmatched.append(left.source_id)

    return MatchReport(tuple(matches), tuple(unmatched), tuple(ambiguous))


def _index(
    records: list[MovieRecord],
    key_function: Callable[[MovieRecord], str | None],
) -> dict[str, list[MovieRecord]]:
    index: dict[str, list[MovieRecord]] = {}
    for record in records:
        key = key_function(record)
        if key:
            index.setdefault(key, []).append(record)
    return index


def _years_compatible(
    left_year: int | None,
    right_year: int | None,
    tolerance: int,
) -> bool:
    if left_year is None or right_year is None:
        return False
    return abs(left_year - right_year) <= tolerance
