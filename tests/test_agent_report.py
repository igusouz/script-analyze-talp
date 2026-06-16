import pandas as pd

from analyzer.agent_report import (
    _cohen_d_signed,
    _discriminatory_score,
    _stability_score,
    compute_agent_report,
)


def _make_df() -> pd.DataFrame:
    """Minimal DataFrame mimicking the real summary structure."""
    return pd.DataFrame(
        [
            # 5 boas: invest inverted (66.67 < 80 ruins), compliance perfect
            {
                "tipo_us": "boa",
                "invest_score": 66.67,
                "compliance_score": 100.0,
                "bdd_scenarios": 6,
                "edge_cases": 5,
                "ambiguidades": 8,
                "riscos": 5,
                "hallucination_reasons": "Ambiguidades/riscos sem relacao",
            },
            {
                "tipo_us": "boa",
                "invest_score": 66.67,
                "compliance_score": 100.0,
                "bdd_scenarios": 5,
                "edge_cases": 6,
                "ambiguidades": 9,
                "riscos": 6,
                "hallucination_reasons": "BDD possui cenarios | Ambiguidades/riscos sem relacao",
            },
            # 2 ruins: invest higher (inverted), compliance low
            {
                "tipo_us": "ruim",
                "invest_score": 83.33,
                "compliance_score": 25.0,
                "bdd_scenarios": 3,
                "edge_cases": 5,
                "ambiguidades": 8,
                "riscos": 5,
                "hallucination_reasons": "BDD possui cenarios | Ambiguidades/riscos sem relacao",
            },
            {
                "tipo_us": "ruim",
                "invest_score": 66.67,
                "compliance_score": 12.5,
                "bdd_scenarios": 2,
                "edge_cases": 5,
                "ambiguidades": 8,
                "riscos": 5,
                "hallucination_reasons": "BDD possui cenarios | Ambiguidades/riscos sem relacao",
            },
        ]
    )


def test_invest_discriminatory_is_zero_when_d_negative() -> None:
    d = _cohen_d_signed([66.67, 66.67], [83.33, 66.67])
    score = _discriminatory_score(d, n=2)
    assert d < 0
    assert score == 0.0


def test_compliance_discriminatory_maximum_when_d_very_large() -> None:
    # Perfect separation: all boas=100, all ruins=25 → d >> 0
    d = _cohen_d_signed([100.0, 100.0], [25.0, 12.5])
    score = _discriminatory_score(d, n=5)
    assert d > 0
    assert score == 10.0


def test_stability_perfect_when_no_variance() -> None:
    score = _stability_score([100.0, 100.0, 100.0], [100.0, 100.0, 100.0], 100.0)
    assert score == 10.0


def test_stability_decreases_with_high_variance() -> None:
    low_var = _stability_score([50.0, 50.0, 50.0], [50.0, 50.0, 50.0], 100.0)
    high_var = _stability_score([10.0, 90.0, 50.0], [10.0, 90.0, 50.0], 100.0)
    assert high_var < low_var


def test_compute_agent_report_columns() -> None:
    df = _make_df()
    report = compute_agent_report(df)
    expected_cols = {
        "agente",
        "capacidade_discriminatoria",
        "robustez",
        "tendencia_alucinacao",
        "estabilidade",
        "contribuicao_fluxo",
        "nota_final",
        "evidencias",
    }
    assert set(report.columns) >= expected_cols
    assert len(report) == 3


def test_compliance_beats_invest_and_bdd_on_final_score() -> None:
    df = _make_df()
    report = compute_agent_report(df)
    scores = dict(zip(report["agente"], report["nota_final"]))
    assert scores["Compliance Agent"] > scores["INVEST Agent"]
    assert scores["Compliance Agent"] > scores["BDD Agent"]


def test_invest_discriminatory_is_zero_in_full_report() -> None:
    df = _make_df()
    report = compute_agent_report(df)
    invest = report[report["agente"] == "INVEST Agent"].iloc[0]
    assert invest["capacidade_discriminatoria"] == 0.0


def test_scores_bounded_0_10() -> None:
    df = _make_df()
    report = compute_agent_report(df)
    numeric_cols = [
        "capacidade_discriminatoria", "robustez", "tendencia_alucinacao",
        "estabilidade", "contribuicao_fluxo", "nota_final",
    ]
    for col in numeric_cols:
        for val in report[col]:
            assert 0.0 <= val <= 10.0, f"{col}={val} out of [0,10]"
