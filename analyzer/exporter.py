from __future__ import annotations

from pathlib import Path

import pandas as pd


def export_summary(df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "summary.csv"
    df.to_csv(destination, index=False)
    return destination


def compute_statistics(df: pd.DataFrame) -> pd.DataFrame:
    if "tipo_us" in df.columns and df["tipo_us"].notna().any():
        good = df[df["tipo_us"].astype(str).str.lower() == "boa"]
        bad = df[df["tipo_us"].astype(str).str.lower() == "ruim"]
    else:
        good = df[df["classificacao"].isin(["Excelente", "Boa"])]
        bad = df[df["classificacao"] == "Ruim"]

    def _mean_or_zero(series: pd.Series) -> float:
        return float(series.mean()) if not series.empty else 0.0

    stats = {
        "media_us_boas": _mean_or_zero(good["robustness_score"]),
        "media_us_ruins": _mean_or_zero(bad["robustness_score"]),
        "ganho_medio_fluxo": _mean_or_zero(df["robustness_score"] - (df["hallucination_score"] / 10.0)),
        "taxa_media_compliance": _mean_or_zero(df["compliance_score"]),
        "taxa_media_aprovacao_invest": _mean_or_zero(df["invest_score"]),
        "media_cenarios_gerados": _mean_or_zero(df["bdd_scenarios"]),
        "media_ambiguidades_detectadas": _mean_or_zero(df["ambiguidades"]),
        "media_riscos_detectados": _mean_or_zero(df["riscos"]),
    }

    return pd.DataFrame([stats])


def export_statistics(stats_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "statistics.csv"
    stats_df.to_csv(destination, index=False)
    return destination


def export_agent_report(agent_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "agent_report.csv"
    agent_df.to_csv(destination, index=False)
    return destination


def export_metric_report(metric_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "metric_report.csv"
    metric_df.to_csv(destination, index=False)
    return destination


def export_invest_individual_report(invest_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "invest_individual_report.csv"
    invest_df.to_csv(destination, index=False)
    return destination


def export_compliance_individual_report(compliance_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "compliance_individual_report.csv"
    compliance_df.to_csv(destination, index=False)
    return destination


def export_bdd_individual_report(bdd_df: pd.DataFrame, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / "bdd_individual_report.csv"
    bdd_df.to_csv(destination, index=False)
    return destination
