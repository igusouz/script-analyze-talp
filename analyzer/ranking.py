from __future__ import annotations

import pandas as pd


def classify_row(
    robustness_0_10: float,
    compliance_score_pct: float,
    invest_score_pct: float,
    hallucination_score_0_10: float,
) -> str:
    if (
        robustness_0_10 >= 8.0
        and compliance_score_pct >= 85.0
        and invest_score_pct >= 85.0
        and hallucination_score_0_10 <= 2.5
    ):
        return "Excelente"

    if (
        robustness_0_10 >= 6.5
        and compliance_score_pct >= 70.0
        and invest_score_pct >= 70.0
        and hallucination_score_0_10 <= 4.5
    ):
        return "Boa"

    if (
        robustness_0_10 >= 5.0
        and compliance_score_pct >= 50.0
        and invest_score_pct >= 50.0
        and hallucination_score_0_10 <= 7.0
    ):
        return "Aceitavel"

    return "Ruim"


def apply_ranking(df: pd.DataFrame) -> pd.DataFrame:
    ranked = df.sort_values(
        by=[
            "robustness_score",
            "compliance_score",
            "invest_score",
            "hallucination_score",
        ],
        ascending=[False, False, False, True],
    ).reset_index(drop=True)

    ranked["ranking"] = ranked.index + 1
    return ranked
