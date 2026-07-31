from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.matching import (  # noqa: E402
    MovieRecord,
    match_catalogs,
    normalize_imdb_id,
    normalize_title,
)


class MatchingTests(unittest.TestCase):
    def test_movielens_numeric_imdb_id_is_normalized(self) -> None:
        self.assertEqual(normalize_imdb_id(114709), "tt0114709")
        self.assertEqual(normalize_imdb_id("tt0114709"), "tt0114709")

    def test_title_normalization_handles_case_accents_and_punctuation(self) -> None:
        self.assertEqual(normalize_title("Amélie!"), "amelie")
        self.assertEqual(normalize_title("  THE--MOVIE "), "the movie")

    def test_shared_id_has_priority_over_different_title(self) -> None:
        left = [MovieRecord("tmdb-1", "Localized Title", 1995, tmdb_id=10)]
        right = [MovieRecord("ml-1", "Different Title", 1995, tmdb_id="10")]

        report = match_catalogs(left, right)

        self.assertEqual(report.matches[0].right_source_id, "ml-1")
        self.assertEqual(report.matches[0].confidence, "high")
        self.assertEqual(report.matches[0].method, "tmdb_id")

    def test_unique_title_and_nearby_year_can_match(self) -> None:
        left = [MovieRecord("left-1", "Amélie", 2001)]
        right = [MovieRecord("right-1", "Amelie!", 2002)]

        report = match_catalogs(left, right)

        self.assertEqual(report.matches[0].method, "title_year")
        self.assertEqual(report.matches[0].confidence, "medium")

    def test_ambiguous_title_candidates_are_rejected(self) -> None:
        left = [MovieRecord("left-1", "The Return", 2020)]
        right = [
            MovieRecord("right-1", "The Return", 2020),
            MovieRecord("right-2", "The Return", 2021),
        ]

        report = match_catalogs(left, right)

        self.assertEqual(report.matches, ())
        self.assertEqual(report.ambiguous_left_ids, ("left-1",))

    def test_missing_year_prevents_title_only_guess(self) -> None:
        left = [MovieRecord("left-1", "Same", None)]
        right = [MovieRecord("right-1", "Same", 2020)]

        report = match_catalogs(left, right)

        self.assertEqual(report.unmatched_left_ids, ("left-1",))
