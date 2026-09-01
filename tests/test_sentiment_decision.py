from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from movie_rating_reliability.sentiment_decision import (  # noqa: E402
    apply_v1_1_success_decision,
)


def comparison_report(*, improvement: float, improved_groups: int) -> dict[str, object]:
    return {
        "stage": "v1_1_same_sample_sentiment_comparison",
        "comparison_movie_count": 149,
        "outer_test_movie_ids_sha256": "frozen-id-hash",
        "overall": {"mae_improvement_base_minus_augmented": improvement},
        "time_group_count": 4,
        "time_groups_with_mae_improvement": improved_groups,
        "predefined_success_thresholds": {
            "minimum_overall_mae_improvement": 0.01,
            "minimum_improved_time_groups": 3,
            "time_group_total": 4,
        },
        "success_decision_applied": False,
    }


class SentimentDecisionTests(unittest.TestCase):
    def test_stops_when_both_predefined_criteria_fail(self) -> None:
        result = apply_v1_1_success_decision(
            comparison_report(improvement=0.0011, improved_groups=2)
        )
        self.assertFalse(result["v1_1_success"])
        self.assertEqual(result["decision"], "stop_model_complexity")
        self.assertFalse(result["criteria"]["overall_mae_improvement"]["passed"])
        self.assertFalse(result["criteria"]["improved_time_groups"]["passed"])

    def test_continues_only_when_both_criteria_pass(self) -> None:
        result = apply_v1_1_success_decision(
            comparison_report(improvement=0.01, improved_groups=3)
        )
        self.assertTrue(result["v1_1_success"])
        self.assertEqual(result["decision"], "continue_sentiment_modeling")

    def test_rejects_decided_or_modified_contract(self) -> None:
        report = comparison_report(improvement=0.02, improved_groups=4)
        report["success_decision_applied"] = True
        with self.assertRaisesRegex(ValueError, "must be undecided"):
            apply_v1_1_success_decision(report)

        report = comparison_report(improvement=0.02, improved_groups=4)
        changed = deepcopy(report)
        changed["predefined_success_thresholds"]["extra"] = 1
        with self.assertRaisesRegex(ValueError, "unexpected thresholds"):
            apply_v1_1_success_decision(changed)


if __name__ == "__main__":
    unittest.main()
