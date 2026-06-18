from __future__ import annotations

from typing import Any

import pandas as pd

from analyzer.bdd_applicability import compute_bdd_applicability, extract_acceptance_criteria
from analyzer.metrics import (
    BDDMetrics,
    ComplianceMetrics,
    INVESTMetrics,
    compute_bdd_metrics,
    compute_compliance_metrics,
    compute_coverage,
    compute_invest_metrics,
)
from analyzer.parser import AgentOutput


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


def _safe_tipo_us(output: AgentOutput) -> str:
    if output.tipo_us and output.tipo_us != "unknown":
        return output.tipo_us
    return _infer_tipo_us(output.user_story)


def _count_matching(items: Any, status: str) -> int:
    if not isinstance(items, list):
        return 0
    target = status.strip().lower()
    count = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        item_status = str(item.get("status", "")).strip().lower()
        if item_status == target:
            count += 1
    return count


def build_invest_individual_report(outputs: list[AgentOutput]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for output in outputs:
        invest: INVESTMetrics = compute_invest_metrics(output.invest)
        rows.append(
            {
                "arquivo": output.file_name,
                "tipo_us": _safe_tipo_us(output),
                "invest_score": round(invest.score_percent, 4),
                "invest_status": invest.final_status,
                "invest_aprovados": invest.approved_count,
                "invest_reprovados": invest.failed_count,
                "invest_criterios_reprovados": ";".join(invest.failed_criteria),
                "invest_evidencias_total": sum(
                    len(item.get("evidence", []))
                    for item in output.invest.values()
                    if isinstance(item, dict)
                ),
            }
        )

    return pd.DataFrame(rows)


def build_compliance_individual_report(outputs: list[AgentOutput]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for output in outputs:
        compliance: ComplianceMetrics = compute_compliance_metrics(output.compliance)
        detected_rules = output.compliance.get("detectedRules")
        rules = output.compliance.get("rules")
        requirements = output.compliance.get("requirements")

        rows.append(
            {
                "arquivo": output.file_name,
                "tipo_us": _safe_tipo_us(output),
                "compliance_score": round(compliance.score_percent, 4),
                "compliance_status": compliance.final_status,
                "compliance_total_regras": compliance.total_rules_detected,
                "compliance_regras_obrigatorias": compliance.mandatory_rules,
                "compliance_obrigatorias_satisfeitas": compliance.mandatory_satisfied,
                "compliance_gaps": compliance.compliance_gaps,
                "compliance_regras_detectadas_lista": len(detected_rules)
                if isinstance(detected_rules, list)
                else (len(rules) if isinstance(rules, list) else 0),
                "compliance_requirements_satisfied": _count_matching(requirements, "satisfied"),
            }
        )

    return pd.DataFrame(rows)


def build_bdd_individual_report(outputs: list[AgentOutput]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for output in outputs:
        bdd_enabled = _can_use_bdd(output)
        bdd_payload = output.bdd if bdd_enabled else {}
        bdd: BDDMetrics = compute_bdd_metrics(bdd_payload)
        applicability = compute_bdd_applicability(
            acceptance_criteria=extract_acceptance_criteria(output.raw),
            bdd_payload=bdd_payload,
        )
        coverage = float(compute_coverage(bdd))
        coverage_normalized = (min(max(coverage, 0.0), 20.0) / 20.0) * 10.0

        rows.append(
            {
                "arquivo": output.file_name,
                "tipo_us": _safe_tipo_us(output),
                "can_continue_to_bdd": bdd_enabled,
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
                "bdd_scenario_quality_avg": round(applicability.scenario_quality_avg, 4),
                "bdd_applicability_reasons": " | ".join(applicability.reasons),
                "coverage": round(coverage, 4),
                "coverage_normalized": round(coverage_normalized, 4),
            }
        )

    return pd.DataFrame(rows)