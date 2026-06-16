"""
Agent-oriented evaluation module.

Computes five independent dimensions for each agent in the TALP multiagent flow:
  - Discriminatory Capacity  : ability to score boas > ruins
  - Robustness               : directional correctness + internal consistency
  - Hallucination Tendency   : fraction of executions flagged for that agent
  - Stability                : within-group score variance (lower = better)
  - Flow Contribution        : net value added to the pipeline goal

All dimensions are on a 0-10 scale. The final score is a weighted average.

Design decisions
----------------
* Cohen's d is computed with population std for full determinism on small n.
* A sample-size penalty factor (n / N_REFERENCE) is applied to the discriminatory
  score because n=5 per group makes large d values unreliable.
* Robustness penalises directionally-wrong agents even when they are "stable".
* BDD Contribution has a structural floor of 4.0 because it adds testability
  artefacts (scenarios, edge cases, automation suggestions) regardless of
  discriminatory power.
* INVEST Contribution has a structural floor of 2.0 because it acts as the
  first gate in the pipeline workflow.
"""
from __future__ import annotations

import math
from typing import Sequence

import pandas as pd

# Reference n for the sample-size penalty (representative small-n evaluation)
N_REFERENCE: int = 20

# Final score weights — must sum to 1.0
WEIGHTS = {
    "discriminatory": 0.30,
    "robustness":     0.20,
    "stability":      0.15,
    "anti_halluc":    0.15,   # 10 - hallucination_tendency
    "contribution":   0.20,
}


# ── Private helpers ────────────────────────────────────────────────────────────

def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pop_std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _cohen_d_signed(group_a: Sequence[float], group_b: Sequence[float]) -> float:
    """
    Signed Cohen's d.  Positive value → group_a > group_b (boas scored higher).
    Uses pooled *population* std for full reproducibility.
    When pooled_std == 0, returns ±10 or 0 based on mean comparison.
    """
    var_a = _pop_std(group_a) ** 2
    var_b = _pop_std(group_b) ** 2
    pooled_std = math.sqrt((var_a + var_b) / 2.0)

    mean_a = _mean(group_a)
    mean_b = _mean(group_b)

    if pooled_std == 0.0:
        if mean_a > mean_b:
            return 10.0
        if mean_a < mean_b:
            return -10.0
        return 0.0

    return (mean_a - mean_b) / pooled_std


def _discriminatory_score(cohen_d: float, n: int) -> float:
    """
    Maps Cohen's d to a 0-10 discriminatory capacity score.
    Negative d (wrong direction: ruins scored higher than boas) → 0.
    A sample-size penalty n / N_REFERENCE shrinks the score for small samples.
    """
    if cohen_d <= 0.0:
        return 0.0
    n_factor = min(1.0, n / N_REFERENCE)
    return round(min(10.0, cohen_d * 5.0 * n_factor), 2)


def _stability_score(
    group_a: Sequence[float],
    group_b: Sequence[float],
    max_range: float,
) -> float:
    """
    Measures within-group consistency.
    pooled_avg_std / max_range is normalised so that 50 % of max_range → score 0.
    """
    avg_std = (_pop_std(group_a) + _pop_std(group_b)) / 2.0
    if max_range <= 0:
        return 10.0
    return round(max(0.0, 10.0 - (avg_std / max_range) * 20.0), 2)


def _hallucination_rate(df: pd.DataFrame, keyword: str) -> float:
    """
    Returns the fraction of executions (×10) where hallucination_reasons
    contains the given keyword — i.e., a 0-10 suspicion rate for this agent.
    """
    n = len(df)
    if n == 0:
        return 0.0
    count = (
        df["hallucination_reasons"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains(keyword.lower(), regex=False)
        .sum()
    )
    return round(float(count) / n * 10.0, 2)


# ── Public API ─────────────────────────────────────────────────────────────────

def compute_agent_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Produces a one-row-per-agent DataFrame with all evaluation dimensions.

    Parameters
    ----------
    df : pd.DataFrame
        The summary DataFrame produced by main.run().  Must contain columns:
        tipo_us, invest_score, compliance_score, bdd_scenarios, edge_cases,
        ambiguidades, riscos, hallucination_reasons.

    Returns
    -------
    pd.DataFrame with columns:
        agente, capacidade_discriminatoria, robustez, tendencia_alucinacao,
        estabilidade, contribuicao_fluxo, nota_final, evidencias
    """
    boas = df[df["tipo_us"].str.lower() == "boa"]
    ruins = df[df["tipo_us"].str.lower() == "ruim"]
    n = min(len(boas), len(ruins))

    # ── INVEST Agent ────────────────────────────────────────────────────────
    inv_b = boas["invest_score"].tolist()
    inv_r = ruins["invest_score"].tolist()
    inv_d = _cohen_d_signed(inv_b, inv_r)
    inv_disc = _discriminatory_score(inv_d, n)
    inv_stab = _stability_score(inv_b, inv_r, 100.0)
    inv_halluc = _hallucination_rate(df, "invest")
    inv_directional_10 = 10.0 if inv_d > 0 else 0.0
    inv_robust = round(
        inv_directional_10 * 0.4 + inv_stab * 0.4 + (10.0 - inv_halluc) * 0.2, 2
    )
    # Structural floor 2.0: INVEST is the mandatory first gate in the pipeline.
    inv_contrib = round(max(2.0, inv_disc * 0.6 + inv_directional_10 * 0.3), 2)
    inv_final = round(
        inv_disc      * WEIGHTS["discriminatory"]
        + inv_robust  * WEIGHTS["robustness"]
        + inv_stab    * WEIGHTS["stability"]
        + (10.0 - inv_halluc) * WEIGHTS["anti_halluc"]
        + inv_contrib * WEIGHTS["contribution"],
        2,
    )
    inv_evidence = (
        f"invest_score — boas={round(_mean(inv_b),2)}, ruins={round(_mean(inv_r),2)}, "
        f"delta={round(_mean(inv_b)-_mean(inv_r),2)} (invertido); "
        f"Cohen's d={round(inv_d,2)}; std_boas={round(_pop_std(inv_b),2)}, "
        f"std_ruins={round(_pop_std(inv_r),2)}"
    )

    # ── Compliance Agent ────────────────────────────────────────────────────
    comp_b = boas["compliance_score"].tolist()
    comp_r = ruins["compliance_score"].tolist()
    comp_d = _cohen_d_signed(comp_b, comp_r)
    comp_disc = _discriminatory_score(comp_d, n)
    comp_stab = _stability_score(comp_b, comp_r, 100.0)
    comp_halluc = _hallucination_rate(df, "compliance")
    comp_directional_10 = 10.0 if comp_d > 0 else 0.0
    comp_robust = round(
        comp_directional_10 * 0.4 + comp_stab * 0.4 + (10.0 - comp_halluc) * 0.2, 2
    )
    comp_contrib = round(min(10.0, max(2.0, comp_disc * 0.6 + comp_directional_10 * 0.3)), 2)
    comp_final = round(
        comp_disc      * WEIGHTS["discriminatory"]
        + comp_robust  * WEIGHTS["robustness"]
        + comp_stab    * WEIGHTS["stability"]
        + (10.0 - comp_halluc) * WEIGHTS["anti_halluc"]
        + comp_contrib * WEIGHTS["contribution"],
        2,
    )
    comp_evidence = (
        f"compliance_score — boas={round(_mean(comp_b),2)}, ruins={round(_mean(comp_r),2)}, "
        f"delta={round(_mean(comp_b)-_mean(comp_r),2)}; "
        f"Cohen's d={round(comp_d,2)} (maior discriminador do fluxo); "
        f"std_boas={round(_pop_std(comp_b),2)}, std_ruins={round(_pop_std(comp_r),2)}"
    )

    # ── BDD Agent ───────────────────────────────────────────────────────────
    bdd_cov_b = (
        boas["bdd_scenarios"] + boas["edge_cases"] + boas["ambiguidades"] + boas["riscos"]
    ).tolist()
    bdd_cov_r = (
        ruins["bdd_scenarios"] + ruins["edge_cases"] + ruins["ambiguidades"] + ruins["riscos"]
    ).tolist()
    bdd_d = _cohen_d_signed(bdd_cov_b, bdd_cov_r)
    bdd_disc = _discriminatory_score(bdd_d, n)
    bdd_stab = _stability_score(bdd_cov_b, bdd_cov_r, 40.0)
    bdd_halluc = _hallucination_rate(df, "bdd")
    bdd_directional_10 = 10.0 if bdd_d > 0 else 0.0
    bdd_robust = round(
        bdd_directional_10 * 0.4 + bdd_stab * 0.4 + (10.0 - bdd_halluc) * 0.2, 2
    )
    # Structural floor 4.0: BDD always contributes artefacts regardless of discrimination.
    bdd_contrib = round(max(4.0, bdd_disc * 0.6 + bdd_directional_10 * 0.3), 2)
    bdd_final = round(
        bdd_disc      * WEIGHTS["discriminatory"]
        + bdd_robust  * WEIGHTS["robustness"]
        + bdd_stab    * WEIGHTS["stability"]
        + (10.0 - bdd_halluc) * WEIGHTS["anti_halluc"]
        + bdd_contrib * WEIGHTS["contribution"],
        2,
    )
    bdd_halluc_count = int(
        df["hallucination_reasons"]
        .fillna("")
        .astype(str)
        .str.lower()
        .str.contains("bdd", regex=False)
        .sum()
    )
    bdd_evidence = (
        f"coverage(cenarios+edge+ambig+risco) — boas={round(_mean(bdd_cov_b),2)}, "
        f"ruins={round(_mean(bdd_cov_r),2)}, delta={round(_mean(bdd_cov_b)-_mean(bdd_cov_r),2)}; "
        f"Cohen's d={round(bdd_d,2)}; hallucination_reasons contendo 'bdd': "
        f"{bdd_halluc_count}/{len(df)} execucoes"
    )

    return pd.DataFrame(
        [
            {
                "agente": "INVEST Agent",
                "capacidade_discriminatoria": inv_disc,
                "robustez": inv_robust,
                "tendencia_alucinacao": inv_halluc,
                "estabilidade": inv_stab,
                "contribuicao_fluxo": inv_contrib,
                "nota_final": inv_final,
                "evidencias": inv_evidence,
            },
            {
                "agente": "Compliance Agent",
                "capacidade_discriminatoria": comp_disc,
                "robustez": comp_robust,
                "tendencia_alucinacao": comp_halluc,
                "estabilidade": comp_stab,
                "contribuicao_fluxo": comp_contrib,
                "nota_final": comp_final,
                "evidencias": comp_evidence,
            },
            {
                "agente": "BDD Agent",
                "capacidade_discriminatoria": bdd_disc,
                "robustez": bdd_robust,
                "tendencia_alucinacao": bdd_halluc,
                "estabilidade": bdd_stab,
                "contribuicao_fluxo": bdd_contrib,
                "nota_final": bdd_final,
                "evidencias": bdd_evidence,
            },
        ]
    )
