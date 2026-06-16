import pandas as pd

from analyzer.ranking import apply_ranking, classify_row


def test_classify_row() -> None:
    assert classify_row(8.5, 90.0, 90.0, 1.0) == "Excelente"
    assert classify_row(7.0, 80.0, 75.0, 4.0) == "Boa"
    assert classify_row(5.5, 55.0, 60.0, 6.0) == "Aceitavel"
    assert classify_row(3.0, 40.0, 45.0, 8.0) == "Ruim"


def test_apply_ranking_ordering_rules() -> None:
    df = pd.DataFrame(
        [
            {
                "arquivo": "a.json",
                "robustness_score": 7.5,
                "compliance_score": 85.0,
                "invest_score": 90.0,
                "hallucination_score": 2.0,
            },
            {
                "arquivo": "b.json",
                "robustness_score": 7.5,
                "compliance_score": 85.0,
                "invest_score": 90.0,
                "hallucination_score": 1.0,
            },
            {
                "arquivo": "c.json",
                "robustness_score": 8.0,
                "compliance_score": 70.0,
                "invest_score": 70.0,
                "hallucination_score": 5.0,
            },
        ]
    )

    ranked = apply_ranking(df)

    assert ranked.iloc[0]["arquivo"] == "c.json"
    assert ranked.iloc[1]["arquivo"] == "b.json"
    assert ranked.iloc[2]["arquivo"] == "a.json"
    assert ranked.iloc[0]["ranking"] == 1
    assert ranked.iloc[2]["ranking"] == 3
