import pandas as pd

from analyzer.metric_report import (
    _classify_relevance,
    _cohen_d,
    _recommend,
    compute_metric_report,
)


def _base_row(tipo_us: str, invest: float, compliance: float, bdd: int) -> dict:
    return {
        "tipo_us": tipo_us,
        "invest_score": invest,
        "compliance_score": compliance,
        "bdd_scenarios": bdd,
        "edge_cases": 5,
        "ambiguidades": 8,
        "riscos": 5,
        "coverage": bdd + 5 + 8 + 5,
        "coverage_normalized": 10.0,
        "hallucination_score": 5.0,
        "robustness_score": 7.0,
        "refinement_questions": 7,
        "automation_suggestions": 5,
    }


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _base_row("boa",  66.67, 100.0, 6),
            _base_row("boa",  66.67, 100.0, 5),
            _base_row("boa",  66.67, 100.0, 6),
            _base_row("ruim", 83.33,  25.0, 3),
            _base_row("ruim", 66.67,  12.5, 2),
            _base_row("ruim", 66.67,  25.0, 7),
        ]
    )


def test_classify_relevance_constant() -> None:
    result = _classify_relevance(0.0, 1, is_constant=True)
    assert result == "Nula (constante)"


def test_classify_relevance_inverted() -> None:
    # d = -2.0, direction=1 (higher is better), but boas scored lower
    result = _classify_relevance(-2.0, 1, is_constant=False)
    assert result == "Invertida"


def test_classify_relevance_alta() -> None:
    result = _classify_relevance(2.5, 1, is_constant=False)
    assert result == "Alta"


def test_recommend_alta_returns_manter() -> None:
    assert _recommend("Alta", "Compliance") == "Manter"


def test_recommend_constant_returns_remover() -> None:
    assert _recommend("Nula (constante)", "Derivada") == "Remover"


def test_recommend_nula_bdd_returns_remover() -> None:
    assert _recommend("Nula", "BDD") == "Remover"


def test_compliance_score_should_be_manter() -> None:
    df = _make_df()
    report = compute_metric_report(df)
    row = report[report["metrica"] == "compliance_score"].iloc[0]
    assert row["relevancia_estatistica"] == "Alta"
    assert row["recomendacao"] == "Manter"


def test_coverage_normalized_should_be_remover() -> None:
    df = _make_df()
    report = compute_metric_report(df)
    row = report[report["metrica"] == "coverage_normalized"].iloc[0]
    assert "constante" in row["relevancia_estatistica"].lower()
    assert row["recomendacao"] == "Remover"


def test_invest_score_should_be_revisar_due_to_inversion() -> None:
    df = _make_df()
    report = compute_metric_report(df)
    row = report[report["metrica"] == "invest_score"].iloc[0]
    assert row["relevancia_estatistica"] == "Invertida"
    assert row["recomendacao"] == "Revisar"


def test_all_metrics_present() -> None:
    df = _make_df()
    report = compute_metric_report(df)
    expected = {
        "invest_score", "compliance_score", "bdd_scenarios",
        "edge_cases", "ambiguidades", "riscos",
        "coverage", "coverage_normalized", "hallucination_score",
        "robustness_score",
    }
    assert expected.issubset(set(report["metrica"]))
