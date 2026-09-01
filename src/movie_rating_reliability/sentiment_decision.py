"""Apply the frozen V1.1 continuation rule to comparison evidence."""

from __future__ import annotations

from typing import Any


def apply_v1_1_success_decision(comparison: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic decision without changing evidence or thresholds."""

    if comparison.get("stage") != "v1_1_same_sample_sentiment_comparison":
        raise ValueError("Expected the fixed V1.1 same-sample comparison report.")
    if comparison.get("success_decision_applied") is not False:
        raise ValueError("Comparison report must be undecided before this step.")

    thresholds = comparison.get("predefined_success_thresholds", {})
    required = {
        "minimum_overall_mae_improvement",
        "minimum_improved_time_groups",
        "time_group_total",
    }
    if set(thresholds) != required:
        raise ValueError("Comparison report has incomplete or unexpected thresholds.")
    if int(thresholds["time_group_total"]) != int(comparison["time_group_count"]):
        raise ValueError("Threshold and reported time-group totals differ.")

    observed_mae_improvement = float(
        comparison["overall"]["mae_improvement_base_minus_augmented"]
    )
    observed_improved_groups = int(comparison["time_groups_with_mae_improvement"])
    required_mae_improvement = float(thresholds["minimum_overall_mae_improvement"])
    required_improved_groups = int(thresholds["minimum_improved_time_groups"])

    overall_passed = observed_mae_improvement >= required_mae_improvement
    subgroup_passed = observed_improved_groups >= required_improved_groups
    success = overall_passed and subgroup_passed
    return {
        "stage": "v1_1_predefined_success_decision",
        "source_stage": comparison["stage"],
        "comparison_movie_count": comparison["comparison_movie_count"],
        "outer_test_movie_ids_sha256": comparison["outer_test_movie_ids_sha256"],
        "success_decision_applied": True,
        "criteria": {
            "overall_mae_improvement": {
                "observed": observed_mae_improvement,
                "required_minimum": required_mae_improvement,
                "passed": overall_passed,
            },
            "improved_time_groups": {
                "observed": observed_improved_groups,
                "required_minimum": required_improved_groups,
                "total": int(thresholds["time_group_total"]),
                "passed": subgroup_passed,
            },
        },
        "v1_1_success": success,
        "decision": "continue_sentiment_modeling" if success else "stop_model_complexity",
        "conclusion": (
            "The fixed sentiment extension met both predefined criteria."
            if success
            else "The fixed sentiment extension did not meet both predefined criteria."
        ),
        "scope_note": (
            "This decision closes the current V1.1 model-complexity branch. It does "
            "not prevent a separately specified future study with new data or a new "
            "predeclared evaluation design."
        ),
    }
