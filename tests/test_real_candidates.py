from __future__ import annotations

from pathlib import Path
import gzip
import sys
import tempfile
import unittest
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.real_candidates import (  # noqa: E402
    RealCandidate,
    build_candidate_table,
    deterministic_stratified_sample,
    rating_count_band,
    write_candidates,
)


def candidate(movie_id: int, decade: int, band: str) -> RealCandidate:
    return RealCandidate(
        movielens_id=movie_id,
        imdb_id=f"tt{movie_id:07d}",
        tmdb_id=movie_id + 100,
        title=f"Movie {movie_id}",
        release_year=decade + 5,
        genres="Drama",
        movielens_rating_10=7.0,
        movielens_rating_count=100,
        imdb_rating_10=7.1,
        imdb_vote_count=1000,
        release_decade=decade,
        movielens_rating_count_band=band,
    )


class RealCandidateTests(unittest.TestCase):
    def test_rating_count_bands_have_declared_boundaries(self) -> None:
        self.assertEqual(rating_count_band(50), "50-199")
        self.assertEqual(rating_count_band(199), "50-199")
        self.assertEqual(rating_count_band(200), "200-999")
        self.assertEqual(rating_count_band(1000), "1000+")

    def test_stratified_sample_is_deterministic_and_proportional(self) -> None:
        population = [
            *(candidate(index, 1990, "50-199") for index in range(1, 7)),
            *(candidate(index, 2000, "1000+") for index in range(7, 11)),
        ]

        first = deterministic_stratified_sample(population, sample_size=5, seed=510)
        second = deterministic_stratified_sample(population, sample_size=5, seed=510)

        self.assertEqual(first, second)
        self.assertEqual(
            sum(item.release_decade == 1990 for item in first),
            3,
        )
        self.assertEqual(
            sum(item.release_decade == 2000 for item in first),
            2,
        )

    def test_sample_rejects_size_larger_than_population(self) -> None:
        with self.assertRaisesRegex(ValueError, "no larger than population"):
            deterministic_stratified_sample(
                [candidate(1, 2000, "50-199")],
                sample_size=2,
                seed=510,
            )

    def test_candidate_csv_has_stable_columns(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.csv"
            write_candidates(path, [candidate(1, 2000, "50-199")])

            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(lines[0].startswith("movielens_id,imdb_id,tmdb_id"))
            self.assertIn("Movie 1", lines[1])

    def test_small_source_files_build_linked_candidate_table(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            movielens = root / "movielens.zip"
            basics = root / "basics.tsv.gz"
            ratings = root / "ratings.tsv.gz"
            movielens_rows = ["userId,movieId,rating,timestamp"]
            movielens_rows.extend(
                f"{user_id},1,4.0,0" for user_id in range(1, 51)
            )
            movielens_rows.extend(
                f"{user_id},2,5.0,0" for user_id in range(51, 101)
            )
            with ZipFile(movielens, "w") as archive:
                archive.writestr(
                    "ml-test/ratings.csv",
                    "\n".join(movielens_rows) + "\n",
                )
                archive.writestr(
                    "ml-test/links.csv",
                    "movieId,imdbId,tmdbId\n1,1,101\n2,2,102\n",
                )
            with gzip.open(basics, "wt", encoding="utf-8") as file:
                file.write(
                    "tconst\ttitleType\tprimaryTitle\tisAdult\tstartYear\tgenres\n"
                    "tt0000001\tmovie\tFirst\t0\t1995\tDrama\n"
                    "tt0000002\tmovie\tSecond\t0\t2005\tComedy\n"
                )
            with gzip.open(ratings, "wt", encoding="utf-8") as file:
                file.write(
                    "tconst\taverageRating\tnumVotes\n"
                    "tt0000001\t7.0\t1000\n"
                    "tt0000002\t8.0\t2000\n"
                )
            contract: dict[str, object] = {
                "contract_id": "test",
                "random_seed": 510,
                "sample_size": {"candidate_movies": 2},
                "eligibility": {
                    "title_type": "movie",
                    "exclude_adult_titles": True,
                    "release_year_min": 1980,
                    "release_year_max": 2022,
                    "minimum_votes": {"movielens": 50, "imdb": 500, "tmdb": 50},
                },
            }

            summary = build_candidate_table(
                movielens_zip=movielens,
                imdb_basics_gz=basics,
                imdb_ratings_gz=ratings,
                contract=contract,
                output_path=root / "candidates.csv",
                summary_path=root / "summary.json",
            )

            self.assertEqual(summary["selected_candidate_count"], 2)
            self.assertEqual(summary["validation_status"], "passed")
            self.assertEqual(
                len((root / "candidates.csv").read_text(encoding="utf-8").splitlines()),
                3,
            )


if __name__ == "__main__":
    unittest.main()
