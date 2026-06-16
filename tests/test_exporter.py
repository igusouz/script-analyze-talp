import pandas as pd

from analyzer.exporter import compute_statistics


def test_compute_statistics_uses_tipo_us_groups() -> None:
    df = pd.DataFrame(
        [
            {
                "tipo_us": "boa",
                "classificacao": "Aceitavel",
                "robustness_score": 8.0,
                "hallucination_score": 2.0,
                "compliance_score": 100.0,
                "invest_score": 70.0,
                "bdd_scenarios": 6,
                "ambiguidades": 8,
                "riscos": 5,
            },
            {
                "tipo_us": "ruim",
                "classificacao": "Ruim",
                "robustness_score": 6.0,
                "hallucination_score": 6.0,
                "compliance_score": 25.0,
                "invest_score": 65.0,
                "bdd_scenarios": 3,
                "ambiguidades": 9,
                "riscos": 6,
            },
        ]
    )

    stats = compute_statistics(df).iloc[0]

    assert stats["media_us_boas"] == 8.0
    assert stats["media_us_ruins"] == 6.0
