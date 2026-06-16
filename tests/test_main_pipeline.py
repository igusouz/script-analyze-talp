import json
from pathlib import Path

from analyzer.main import run


def test_run_pipeline_generates_csvs(tmp_path: Path) -> None:
    input_dir = tmp_path / "inputs"
    output_dir = tmp_path / "outputs"
    input_dir.mkdir(parents=True)

    payload = {
        "user_story": "As a user I want to reset password so that I regain account access",
        "invest": {
            "criteria": {
                "independent": True,
                "negotiable": True,
                "valuable": True,
                "estimable": True,
                "small": True,
                "testable": True,
            }
        },
        "compliance": {
            "rules": [
                {"mandatory": True, "satisfied": True, "evidence": "reset token required"},
                {"mandatory": True, "satisfied": True, "evidence": "token expiration set"},
            ]
        },
        "bdd": {
            "positive_scenarios": 2,
            "negative_scenarios": 1,
            "edge_cases": 1,
            "ambiguities": 1,
            "risks": 1,
            "refinement_questions": 1,
            "automation_suggestions": 1,
        },
    }

    (input_dir / "sample.json").write_text(json.dumps(payload), encoding="utf-8")

    summary_df, stats_df, agent_df, metric_df = run(input_dir=input_dir, output_dir=output_dir)

    assert not summary_df.empty
    assert not stats_df.empty
    assert not agent_df.empty
    assert not metric_df.empty
    assert (output_dir / "summary.csv").exists()
    assert (output_dir / "statistics.csv").exists()
    assert (output_dir / "agent_report.csv").exists()
    assert (output_dir / "metric_report.csv").exists()
