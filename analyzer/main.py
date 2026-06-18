from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import pandas as pd

from analyzer.agent_report import compute_agent_report
from analyzer.bdd_applicability import compute_bdd_applicability, extract_acceptance_criteria
from analyzer.metric_report import compute_metric_report
from analyzer.exporter import (
    export_bdd_individual_report,
    export_compliance_individual_report,
    compute_statistics,
    export_agent_report,
    export_invest_individual_report,
    export_metric_report,
    export_statistics,
    export_summary,
)
from analyzer.hallucination import compute_hallucination_metrics
from analyzer.individual_reports import (
    build_bdd_individual_report,
    build_compliance_individual_report,
    build_invest_individual_report,
)
from analyzer.metrics import (
    BDDMetrics,
    ComplianceMetrics,
    CompositeMetrics,
    INVESTMetrics,
    compute_bdd_metrics,
    compute_compliance_metrics,
    compute_composite_metrics,
    compute_invest_metrics,
)
from analyzer.parser import AgentOutput, parse_json_folder
from analyzer.ranking import apply_ranking, classify_row


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y", "sim"}:
            return True
        if lowered in {"false", "0", "no", "n", "nao", "não"}:
            return False
    return None


def _can_use_bdd(output: AgentOutput) -> bool:
    metadata = output.compliance.get("metadata")
    if isinstance(metadata, dict):
        parsed = _parse_bool(metadata.get("can_continue_to_bdd"))
        if parsed is not None:
            return parsed
    return True


def _infer_tipo_us(story: str) -> str:
    lowered = story.lower()
    if "as a" in lowered and "i want" in lowered and "so that" in lowered:
        return "classic"
    if "dado" in lowered and "quando" in lowered and "entao" in lowered:
        return "bdd_style"
    return "custom"


def _row_from_output(output: AgentOutput) -> dict[str, Any]:
    invest: INVESTMetrics = compute_invest_metrics(output.invest)
    compliance: ComplianceMetrics = compute_compliance_metrics(output.compliance)
    bdd_enabled = _can_use_bdd(output)
    bdd_payload = output.bdd if bdd_enabled else {}
    bdd: BDDMetrics = compute_bdd_metrics(bdd_payload)
    applicability = compute_bdd_applicability(
        acceptance_criteria=extract_acceptance_criteria(output.raw),
        bdd_payload=bdd_payload,
    )

    composite: CompositeMetrics = compute_composite_metrics(
        invest_score_pct=invest.score_percent,
        compliance_score_pct=compliance.score_percent,
        bdd_metrics=bdd,
    )

    hallucination = compute_hallucination_metrics(
        user_story=output.user_story,
        invest_data=output.invest,
        compliance_data=output.compliance,
        bdd_data=bdd_payload,
    )

    classificacao = classify_row(
        robustness_0_10=composite.robustness_0_10,
        compliance_score_pct=compliance.score_percent,
        invest_score_pct=invest.score_percent,
        hallucination_score_0_10=hallucination.score_0_10,
    )

    return {
        "arquivo": output.file_name,
        "tipo_us": output.tipo_us if output.tipo_us and output.tipo_us != "unknown" else _infer_tipo_us(output.user_story),
        "invest_score": round(invest.score_percent, 4),
        "invest_aprovados": invest.approved_count,
        "invest_reprovados": invest.failed_count,
        "invest_criterios_reprovados": ";".join(invest.failed_criteria),
        "invest_status": invest.final_status,
        "compliance_score": round(compliance.score_percent, 4),
        "compliance_total_regras": compliance.total_rules_detected,
        "compliance_obrigatorias_satisfeitas": compliance.mandatory_satisfied,
        "compliance_gaps": compliance.compliance_gaps,
        "compliance_status": compliance.final_status,
        "bdd_positive": bdd.positive_scenarios,
        "bdd_negative": bdd.negative_scenarios,
        "bdd_scenarios": bdd.total_scenarios,
        "edge_cases": bdd.edge_cases,
        "ambiguidades": bdd.ambiguities,
        "riscos": bdd.risks,
        "refinement_questions": bdd.refinement_questions,
        "automation_suggestions": bdd.automation_suggestions,
        "bdd_applicability_score": round(applicability.score_0_10, 4),
        "bdd_applicability_level": applicability.level,
        "bdd_ac_coverage": round(applicability.ac_coverage_ratio, 4),
        "bdd_ac_covered": applicability.ac_covered,
        "bdd_ac_total": applicability.ac_total,
        "bdd_applicable_scenarios": applicability.scenarios_applicable,
        "bdd_applicability_reasons": " | ".join(applicability.reasons),
        "coverage": round(composite.coverage, 4),
        "coverage_normalized": round(composite.coverage_normalized_0_10, 4),
        "hallucination_score": round(hallucination.score_0_10, 4),
        "hallucination_level": hallucination.level,
        "hallucination_reasons": " | ".join(hallucination.reasons),
        "robustness_score": round(composite.robustness_0_10, 4),
        "classificacao": classificacao,
    }


def run(
    input_dir: Path, output_dir: Path
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    outputs = parse_json_folder(input_dir)
    rows = [_row_from_output(output) for output in outputs]

    df = pd.DataFrame(rows)
    if df.empty:
        # Keep deterministic schema for empty runs.
        df = pd.DataFrame(
            columns=[
                "arquivo",
                "tipo_us",
                "invest_score",
                "compliance_score",
                "bdd_scenarios",
                "edge_cases",
                "ambiguidades",
                "riscos",
                "hallucination_score",
                "robustness_score",
                "classificacao",
                "ranking",
            ]
        )
        stats_df = compute_statistics(
            df.assign(
                compliance_score=0,
                invest_score=0,
                bdd_scenarios=0,
                ambiguidades=0,
                riscos=0,
                robustness_score=0,
                hallucination_score=0,
                classificacao="Ruim",
            )
        )
        empty_agent = pd.DataFrame(
            columns=[
                "agente", "capacidade_discriminatoria", "robustez",
                "tendencia_alucinacao", "estabilidade", "contribuicao_fluxo",
                "nota_final", "evidencias",
            ]
        )
        empty_metric = pd.DataFrame(
            columns=[
                "metrica", "agente", "media_boas", "media_ruins",
                "delta_boas_minus_ruins", "cohen_d",
                "relevancia_estatistica", "recomendacao",
            ]
        )
        export_summary(df, output_dir)
        export_statistics(stats_df, output_dir)
        export_agent_report(empty_agent, output_dir)
        export_metric_report(empty_metric, output_dir)
        export_invest_individual_report(pd.DataFrame(), output_dir)
        export_compliance_individual_report(pd.DataFrame(), output_dir)
        export_bdd_individual_report(pd.DataFrame(), output_dir)
        return df, stats_df, empty_agent, empty_metric

    ranked = apply_ranking(df)
    ranked = ranked[
        [
            "arquivo",
            "tipo_us",
            "invest_score",
            "compliance_score",
            "bdd_scenarios",
            "edge_cases",
            "ambiguidades",
            "riscos",
            "hallucination_score",
            "robustness_score",
            "classificacao",
            "ranking",
            "invest_aprovados",
            "invest_reprovados",
            "invest_criterios_reprovados",
            "invest_status",
            "compliance_total_regras",
            "compliance_obrigatorias_satisfeitas",
            "compliance_gaps",
            "compliance_status",
            "bdd_positive",
            "bdd_negative",
            "refinement_questions",
            "automation_suggestions",
            "bdd_applicability_score",
            "bdd_applicability_level",
            "bdd_ac_coverage",
            "bdd_ac_covered",
            "bdd_ac_total",
            "bdd_applicable_scenarios",
            "bdd_applicability_reasons",
            "coverage",
            "coverage_normalized",
            "hallucination_level",
            "hallucination_reasons",
        ]
    ]

    stats_df = compute_statistics(ranked)
    agent_df = compute_agent_report(ranked)
    metric_df = compute_metric_report(ranked)
    invest_individual_df = build_invest_individual_report(outputs)
    compliance_individual_df = build_compliance_individual_report(outputs)
    bdd_individual_df = build_bdd_individual_report(outputs)

    export_summary(ranked, output_dir)
    export_statistics(stats_df, output_dir)
    export_agent_report(agent_df, output_dir)
    export_metric_report(metric_df, output_dir)
    export_invest_individual_report(invest_individual_df, output_dir)
    export_compliance_individual_report(compliance_individual_df, output_dir)
    export_bdd_individual_report(bdd_individual_df, output_dir)

    return ranked, stats_df, agent_df, metric_df


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TALP Multi-Agent quantitative analyzer")
    parser.add_argument("--input-dir", type=Path, required=True, help="Directory containing JSON files")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs"), help="Directory for CSV exports")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    run(args.input_dir, args.output_dir)


if __name__ == "__main__":
    main()
