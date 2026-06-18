"""
Metric-oriented evaluation module.

For each metric in the summary DataFrame, computes:
  - Delta between US-boas and US-ruins (mean_boas − mean_ruins)
  - Cohen's d (population std, deterministic)
  - Relevância Estatística  : Alta / Media / Baixa / Nula / Invertida / Nula (constante)
  - Recomendação            : Manter / Revisar / Remover

Classification rules
--------------------
Relevância:
  Correct direction required (direction=1 → boas > ruins; direction=-1 → boas < ruins).
  If direction is violated → "Invertida".
  |d| ≥ 2.0 → "Alta"
  |d| ≥ 0.8 → "Media"
  |d| ≥ 0.2 → "Baixa"
  |d| < 0.2 → "Nula"
  Both groups constant with delta=0 → "Nula (constante)"

  NOTE: With n=5 per group, even |d|=2.0 may not reach p<0.05.
  The classification is descriptive, not inferential.

Recomendação:
  "Alta"           → Manter
  "Nula (constante)" → Remover (zero information, saturated ceiling)
  "Invertida"      → Revisar (calibration / design issue)
  "Nula" (BDD)     → Remover
  "Nula" (other)   → Revisar
  "Media" / "Baixa" → Revisar (may improve with larger n or redesign)
"""
from __future__ import annotations

import math
from typing import Any

import pandas as pd


# ── Metric catalogue ──────────────────────────────────────────────────────────
# direction: +1 = higher is better (boas should score higher than ruins)
#            -1 = lower is better  (boas should score lower  than ruins)

METRIC_SPECS: list[dict[str, Any]] = [
    # INVEST Agent
    {"name": "invest_score",         "direction":  1, "max_range": 100, "agent": "INVEST"},
    # Compliance Agent
    {"name": "compliance_score",     "direction":  1, "max_range": 100, "agent": "Compliance"},
    # BDD Agent — raw counts
    {"name": "bdd_scenarios",        "direction":  1, "max_range": 15,  "agent": "BDD"},
    {"name": "edge_cases",           "direction":  1, "max_range": 10,  "agent": "BDD"},
    {"name": "ambiguidades",         "direction": -1, "max_range": 15,  "agent": "BDD"},
    {"name": "riscos",               "direction": -1, "max_range": 10,  "agent": "BDD"},
    {"name": "refinement_questions", "direction": -1, "max_range": 10,  "agent": "BDD"},
    {"name": "automation_suggestions","direction": 1, "max_range": 10,  "agent": "BDD"},
    {"name": "bdd_applicability_score", "direction": 1, "max_range": 10, "agent": "BDD"},
    # Derived / Composite
    {"name": "coverage",             "direction":  1, "max_range": 40,  "agent": "Derivada"},
    {"name": "coverage_normalized",  "direction":  1, "max_range": 10,  "agent": "Derivada"},
    {"name": "hallucination_score",  "direction": -1, "max_range": 10,  "agent": "Transversal"},
    {"name": "robustness_score",     "direction":  1, "max_range": 10,  "agent": "Composta"},
]


# ── Private helpers ───────────────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pop_std(values: list[float]) -> float:
    if not values:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _cohen_d(boas: list[float], ruins: list[float]) -> float:
    """Signed Cohen's d.  Positive → boas > ruins."""
    pooled = math.sqrt((_pop_std(boas) ** 2 + _pop_std(ruins) ** 2) / 2.0)
    if pooled == 0.0:
        diff = _mean(boas) - _mean(ruins)
        return 10.0 if diff > 0 else (-10.0 if diff < 0 else 0.0)
    return (_mean(boas) - _mean(ruins)) / pooled


def _classify_relevance(
    d_signed: float,
    direction: int,
    is_constant: bool,
) -> str:
    if is_constant:
        return "Nula (constante)"

    # Correct direction: d and direction must have the same sign
    correct = (direction > 0 and d_signed > 0) or (direction < 0 and d_signed < 0)
    if not correct:
        return "Invertida"

    d_abs = abs(d_signed)
    if d_abs >= 2.0:
        return "Alta"
    if d_abs >= 0.8:
        return "Media"
    if d_abs >= 0.2:
        return "Baixa"
    return "Nula"


def _recommend(relevance: str, agent: str) -> str:
    mapping: dict[str, str] = {
        "Alta":             "Manter",
        "Nula (constante)": "Remover",
    }
    if relevance in mapping:
        return mapping[relevance]
    if relevance == "Invertida":
        return "Revisar"
    if relevance == "Nula":
        return "Remover" if agent == "BDD" else "Revisar"
    # "Media" and "Baixa"
    return "Revisar"


# ── Public API ────────────────────────────────────────────────────────────────

def compute_metric_report(df: pd.DataFrame) -> pd.DataFrame:
    """
    Evaluates each metric in METRIC_SPECS against the summary DataFrame.

    Parameters
    ----------
    df : summary DataFrame from main.run().

    Returns
    -------
    pd.DataFrame with columns:
        metrica, agente, media_boas, media_ruins,
        delta_boas_minus_ruins, cohen_d,
        relevancia_estatistica, recomendacao
    """
    boas = df[df["tipo_us"].str.lower() == "boa"]
    ruins = df[df["tipo_us"].str.lower() == "ruim"]

    rows = []
    for spec in METRIC_SPECS:
        col = spec["name"]
        if col not in df.columns:
            continue

        direction: int = spec["direction"]
        boas_vals: list[float] = boas[col].tolist()
        ruins_vals: list[float] = ruins[col].tolist()

        mean_b = _mean(boas_vals)
        mean_r = _mean(ruins_vals)
        delta = round(mean_b - mean_r, 4)
        d_raw = _cohen_d(boas_vals, ruins_vals)

        is_constant = (
            _pop_std(boas_vals) == 0.0
            and _pop_std(ruins_vals) == 0.0
            and delta == 0.0
        )

        relevance = _classify_relevance(d_raw, direction, is_constant)
        recommendation = _recommend(relevance, spec["agent"])

        rows.append(
            {
                "metrica": col,
                "agente": spec["agent"],
                "media_boas": round(mean_b, 3),
                "media_ruins": round(mean_r, 3),
                "delta_boas_minus_ruins": delta,
                "cohen_d": round(d_raw, 3),
                "relevancia_estatistica": relevance,
                "recomendacao": recommendation,
            }
        )

    return pd.DataFrame(rows)
