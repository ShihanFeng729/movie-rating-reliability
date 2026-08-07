from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.snapshot_contract import (  # noqa: E402
    load_snapshot_contract,
    summarize_snapshot_contract,
    validate_snapshot_contract,
)


CONTRACT_PATH = PROJECT_ROOT / "config" / "real_snapshot_v1.json"


class SnapshotContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_snapshot_contract(CONTRACT_PATH)

    def test_tracked_contract_is_valid(self) -> None:
        summary = summarize_snapshot_contract(self.contract)

        self.assertEqual(summary["candidate_movies"], 1000)
        self.assertEqual(summary["target_complete_movies"], 750)
        self.assertEqual(summary["minimum_complete_movies"], 500)
        self.assertEqual(summary["validation_status"], "passed")

    def test_sample_sizes_must_be_ordered(self) -> None:
        invalid = deepcopy(self.contract)
        invalid["sample_size"]["target_complete_movies"] = 1200

        with self.assertRaisesRegex(ValueError, "minimum <= target <= candidates"):
            validate_snapshot_contract(invalid)

    def test_all_platform_identifiers_are_required(self) -> None:
        invalid = deepcopy(self.contract)
        invalid["eligibility"]["required_identifiers"].remove("tmdb_id")

        with self.assertRaisesRegex(ValueError, "All three stable"):
            validate_snapshot_contract(invalid)

    def test_minimum_sample_must_support_holdout(self) -> None:
        invalid = deepcopy(self.contract)
        invalid["evaluation_split"]["minimum_test_movies"] = 150

        with self.assertRaisesRegex(ValueError, "cannot supply"):
            validate_snapshot_contract(invalid)

    def test_temporal_mismatch_cannot_be_hidden(self) -> None:
        invalid = deepcopy(self.contract)
        invalid["temporal_alignment"]["status"] = "fully_aligned"

        with self.assertRaisesRegex(ValueError, "mismatch must be explicit"):
            validate_snapshot_contract(invalid)


if __name__ == "__main__":
    unittest.main()
