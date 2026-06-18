import json
from pathlib import Path

from analyzer.individual_reports import (
    build_bdd_individual_report,
    build_compliance_individual_report,
    build_invest_individual_report,
)
from analyzer.parser import parse_json_folder


def test_build_individual_reports_from_talp_schema(tmp_path: Path) -> None:
    payload = {
        "originalStory": {
            "title": "Triagem",
            "description": "Dado atendimento quando confirmar entao liberar",
            "acceptanceCriteria": ["A", "B"],
        },
        "investAnalysis": {
            "independent": {"status": "pass", "evidence": ["e1"]},
            "negotiable": {"status": "pass", "evidence": ["e2"]},
            "valuable": {"status": "pass", "evidence": ["e3"]},
            "estimable": {"status": "fail", "evidence": ["e4"]},
            "small": {"status": "pass", "evidence": ["e5"]},
            "testable": {"status": "pass", "evidence": ["e6"]},
        },
        "complianceAnalysis": {
            "status": "compliant",
            "detectedRules": [{"matched": True}, {"matched": True}],
            "requirements": [{"status": "satisfied"}, {"status": "satisfied"}],
            "metadata": {"can_continue_to_bdd": False},
        },
        "bddAnalysis": {
            "bddScenarios": [
                {"scenarioType": "positive", "title": "cenario 1"},
                {"scenarioType": "negative", "title": "cenario 2"},
            ],
            "edgeCases": ["borda 1"],
            "ambiguities": ["amb 1"],
            "risks": ["risk 1"],
            "questionsForRefinement": ["q1"],
            "automationSuggestions": ["a1"],
        },
    }

    input_dir = tmp_path / "inputs"
    input_dir.mkdir(parents=True)
    (input_dir / "sample.json").write_text(json.dumps(payload), encoding="utf-8")

    outputs = parse_json_folder(input_dir)

    invest_df = build_invest_individual_report(outputs)
    compliance_df = build_compliance_individual_report(outputs)
    bdd_df = build_bdd_individual_report(outputs)

    invest_row = invest_df.iloc[0]
    assert invest_row["arquivo"] == "sample.json"
    assert invest_row["invest_aprovados"] == 5
    assert invest_row["invest_reprovados"] == 1
    assert invest_row["invest_criterios_reprovados"] == "estimable"
    assert invest_row["invest_evidencias_total"] == 6

    compliance_row = compliance_df.iloc[0]
    assert compliance_row["compliance_total_regras"] == 2
    assert compliance_row["compliance_obrigatorias_satisfeitas"] == 2
    assert compliance_row["compliance_regras_detectadas_lista"] == 2
    assert compliance_row["compliance_requirements_satisfied"] == 2

    bdd_row = bdd_df.iloc[0]
    assert bool(bdd_row["can_continue_to_bdd"]) is False
    assert bdd_row["bdd_scenarios"] == 0
    assert bdd_row["coverage"] == 0
