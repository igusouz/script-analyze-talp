import json
from pathlib import Path

from analyzer.metrics import compute_bdd_metrics, compute_compliance_metrics, compute_invest_metrics
from analyzer.parser import parse_json_file


def test_parse_talp_schema_file(tmp_path: Path) -> None:
    payload = {
        "originalStory": {
            "title": "Triagem",
            "description": "Como enfermeira quero registrar triagem para agilizar atendimento",
            "acceptanceCriteria": ["Campo A obrigatorio", "Campo B obrigatorio"],
        },
        "investAnalysis": {
            "independent": {"status": "pass"},
            "negotiable": {"status": "pass"},
            "valuable": {"status": "pass"},
            "estimable": {"status": "fail", "reason": "generic"},
            "small": {"status": "fail", "reason": "generic"},
            "testable": {"status": "pass"},
        },
        "complianceAnalysis": {
            "status": "non_compliant",
            "detectedRules": [{"matched": True}],
            "requirements": [{"status": "satisfied"}],
            "complianceGaps": [{"id": "gap-1"}, {"id": "gap-2"}],
        },
        "bddAnalysis": {
            "bddScenarios": [
                {"scenarioType": "positive", "title": "cenario 1"},
                {"scenarioType": "positive", "title": "cenario 2"},
            ],
            "negativeCases": ["erro 1", "erro 2", "erro 3"],
            "edgeCases": ["borda 1"],
            "ambiguities": ["amb 1"],
            "risks": ["risk 1"],
            "questionsForRefinement": ["q1"],
            "automationSuggestions": ["a1", "a2"],
        },
    }

    file_path = tmp_path / "us_b_demo.json"
    file_path.write_text(json.dumps(payload), encoding="utf-8")

    parsed = parse_json_file(file_path)

    assert parsed.tipo_us == "boa"
    assert "Acceptance criteria" in parsed.user_story
    assert parsed.invest
    assert parsed.compliance
    assert parsed.bdd

    invest_metrics = compute_invest_metrics(parsed.invest)
    assert invest_metrics.approved_count == 4
    assert invest_metrics.failed_count == 2

    compliance_metrics = compute_compliance_metrics(parsed.compliance)
    assert compliance_metrics.total_rules_detected == 1
    assert compliance_metrics.mandatory_rules == 3
    assert compliance_metrics.mandatory_satisfied == 1
    assert compliance_metrics.compliance_gaps == 2

    bdd_metrics = compute_bdd_metrics(parsed.bdd)
    assert bdd_metrics.positive_scenarios == 2
    assert bdd_metrics.negative_scenarios == 3
    assert bdd_metrics.total_scenarios == 5
    assert bdd_metrics.edge_cases == 1
    assert bdd_metrics.ambiguities == 1
    assert bdd_metrics.risks == 1
