from analyzer.metrics import (
    compute_bdd_metrics,
    compute_compliance_metrics,
    compute_composite_metrics,
    compute_invest_metrics,
)


def test_invest_metrics_counts_and_score() -> None:
    payload = {
        "criteria": {
            "independent": True,
            "negotiable": True,
            "valuable": False,
            "estimable": True,
            "small": False,
            "testable": True,
        }
    }

    result = compute_invest_metrics(payload)

    assert result.approved_count == 4
    assert result.failed_count == 2
    assert result.score_percent == round((4 / 6) * 100, 2)
    assert set(result.failed_criteria) == {"valuable", "small"}
    assert result.final_status == "rejected"


def test_compliance_metrics_from_rules() -> None:
    payload = {
        "rules": [
            {"mandatory": True, "satisfied": True},
            {"mandatory": True, "satisfied": False},
            {"mandatory": False, "satisfied": True},
        ]
    }

    result = compute_compliance_metrics(payload)

    assert result.total_rules_detected == 3
    assert result.mandatory_satisfied == 1
    assert result.compliance_gaps == 1
    assert result.score_percent == 50.0
    assert result.final_status == "rejected"


def test_bdd_and_composite_metrics() -> None:
    payload = {
        "positive_scenarios": 3,
        "negative_scenarios": 2,
        "edge_cases": 4,
        "ambiguities": 1,
        "risks": 2,
        "refinement_questions": 3,
        "automation_suggestions": 1,
    }

    bdd = compute_bdd_metrics(payload)
    assert bdd.total_scenarios == 5

    composite = compute_composite_metrics(
        invest_score_pct=80.0,
        compliance_score_pct=70.0,
        bdd_metrics=bdd,
        coverage_cap=20,
    )

    expected_coverage = 5 + 4 + 1 + 2
    assert composite.coverage == expected_coverage
    assert composite.coverage_normalized_0_10 == (expected_coverage / 20) * 10
    assert 0 <= composite.robustness_0_10 <= 10


def test_bdd_total_scenarios_uses_explicit_value() -> None:
    payload = {
        "positive_scenarios": 10,
        "negative_scenarios": 8,
        "total_scenarios": 7,
    }

    bdd = compute_bdd_metrics(payload)
    assert bdd.total_scenarios == 7
