from __future__ import annotations

from dataclasses import dataclass
from typing import Any


INVEST_CRITERIA = [
    "independent",
    "negotiable",
    "valuable",
    "estimable",
    "small",
    "testable",
]


@dataclass(frozen=True)
class INVESTMetrics:
    approved_count: int
    failed_count: int
    score_percent: float
    failed_criteria: list[str]
    final_status: str


@dataclass(frozen=True)
class ComplianceMetrics:
    total_rules_detected: int
    mandatory_rules: int
    mandatory_satisfied: int
    compliance_gaps: int
    final_status: str
    score_percent: float


@dataclass(frozen=True)
class BDDMetrics:
    positive_scenarios: int
    negative_scenarios: int
    total_scenarios: int
    edge_cases: int
    ambiguities: int
    risks: int
    refinement_questions: int
    automation_suggestions: int


@dataclass(frozen=True)
class CoreMetrics:
    invest: INVESTMetrics
    compliance: ComplianceMetrics
    bdd: BDDMetrics
    coverage: int


@dataclass(frozen=True)
class CompositeMetrics:
    coverage: float
    coverage_normalized_0_10: float
    robustness_0_10: float


def _to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"approved", "pass", "passed", "ok", "true", "yes", "y", "1"}:
            return True
        if normalized in {"rejected", "fail", "failed", "false", "no", "n", "0"}:
            return False
    return None


def _to_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def _to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _count_or_length(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, list):
        return len(value)
    return 0


def compute_invest_metrics(invest: dict[str, Any]) -> INVESTMetrics:
    criteria_values: dict[str, bool] = {}

    criteria_dict = _to_dict(invest.get("criteria"))
    for criterion in INVEST_CRITERIA:
        value = _to_bool(criteria_dict.get(criterion))
        if value is not None:
            criteria_values[criterion] = value

    for criterion in INVEST_CRITERIA:
        if criterion in criteria_values:
            continue
        direct_value = _to_bool(invest.get(criterion))
        if direct_value is not None:
            criteria_values[criterion] = direct_value

    # TALP format: each criterion is an object with {status, evidence, reason}
    for criterion in INVEST_CRITERIA:
        if criterion in criteria_values:
            continue
        criterion_payload = _to_dict(invest.get(criterion))
        status_value = _to_bool(criterion_payload.get("status"))
        if status_value is not None:
            criteria_values[criterion] = status_value

    approved_criteria = {str(item).strip().lower() for item in _to_list(invest.get("approved_criteria"))}
    failed_criteria = {str(item).strip().lower() for item in _to_list(invest.get("failed_criteria"))}

    for criterion in INVEST_CRITERIA:
        if criterion in criteria_values:
            continue
        if criterion in approved_criteria:
            criteria_values[criterion] = True
        elif criterion in failed_criteria:
            criteria_values[criterion] = False

    approved_count = sum(1 for value in criteria_values.values() if value)
    failed_list = [name for name in INVEST_CRITERIA if criteria_values.get(name) is False]
    failed_count = len(failed_list)
    evaluated_total = len(criteria_values)
    denominator = evaluated_total if evaluated_total else len(INVEST_CRITERIA)
    score_percent = round((approved_count / denominator) * 100.0, 2) if denominator else 0.0

    explicit_status = str(invest.get("status", "")).strip().lower()
    if explicit_status in {"approved", "rejected"}:
        final_status = explicit_status
    else:
        final_status = "approved" if failed_count == 0 and denominator > 0 else "rejected"

    return INVESTMetrics(
        approved_count=approved_count,
        failed_count=failed_count,
        score_percent=score_percent,
        failed_criteria=failed_list,
        final_status=final_status,
    )


def compute_compliance_metrics(compliance: dict[str, Any]) -> ComplianceMetrics:
    rules = _to_list(compliance.get("rules"))
    if not rules:
        rules = _to_list(compliance.get("detectedRules"))

    total_rules_detected = _count_or_length(compliance.get("total_rules_detected"))
    if total_rules_detected == 0:
        total_rules_detected = len(rules)

    mandatory_rules = _count_or_length(compliance.get("mandatory_rules"))
    mandatory_satisfied = _count_or_length(compliance.get("mandatory_rules_satisfied"))

    if mandatory_rules == 0:
        metadata = _to_dict(compliance.get("metadata"))
        mandatory_rules = _count_or_length(metadata.get("mandatory_rules"))

    if mandatory_rules == 0 and rules:
        mandatory_rules = sum(1 for rule in rules if _to_bool(_to_dict(rule).get("mandatory")) is not False)

    if mandatory_satisfied == 0:
        requirements = _to_list(compliance.get("requirements"))
        if requirements:
            mandatory_satisfied = sum(
                1
                for requirement in requirements
                if str(_to_dict(requirement).get("status", "")).strip().lower() == "satisfied"
            )

    if mandatory_satisfied == 0 and rules:
        mandatory_satisfied = sum(
            1
            for rule in rules
            if _to_bool(_to_dict(rule).get("mandatory")) is not False
            and (
                _to_bool(_to_dict(rule).get("satisfied")) is True
                or _to_bool(_to_dict(rule).get("matched")) is True
            )
        )

    compliance_gaps = _count_or_length(compliance.get("compliance_gaps"))
    if compliance_gaps == 0:
        compliance_gaps = _count_or_length(compliance.get("complianceGaps"))

    requirements = _to_list(compliance.get("requirements"))
    if mandatory_rules == 0 and (requirements or compliance_gaps):
        mandatory_rules = len(requirements) + compliance_gaps
    elif mandatory_rules > 0 and compliance_gaps > 0 and mandatory_rules < (len(requirements) + compliance_gaps):
        mandatory_rules = len(requirements) + compliance_gaps
    if compliance_gaps == 0 and mandatory_rules:
        compliance_gaps = max(mandatory_rules - mandatory_satisfied, 0)

    score_percent = round((mandatory_satisfied / mandatory_rules) * 100.0, 2) if mandatory_rules else 0.0

    explicit_status = str(compliance.get("status", "")).strip().lower()
    if explicit_status in {"approved", "rejected", "compliant", "non_compliant"}:
        final_status = "approved" if explicit_status in {"approved", "compliant"} else "rejected"
    else:
        final_status = "approved" if compliance_gaps == 0 and mandatory_rules > 0 else "rejected"

    return ComplianceMetrics(
        total_rules_detected=total_rules_detected,
        mandatory_rules=mandatory_rules,
        mandatory_satisfied=mandatory_satisfied,
        compliance_gaps=compliance_gaps,
        final_status=final_status,
        score_percent=score_percent,
    )


def compute_bdd_metrics(bdd: dict[str, Any]) -> BDDMetrics:
    scenarios = _to_list(bdd.get("scenarios"))
    if not scenarios:
        scenarios = _to_list(bdd.get("bddScenarios"))

    positive_scenarios = _count_or_length(bdd.get("positive_scenarios"))
    negative_scenarios = _count_or_length(bdd.get("negative_scenarios"))

    if positive_scenarios == 0:
        positive_scenarios = _count_or_length(bdd.get("positiveScenarios"))
    if negative_scenarios == 0:
        negative_scenarios = _count_or_length(bdd.get("negativeScenarios"))

    if (positive_scenarios == 0 and negative_scenarios == 0) and scenarios:
        for scenario in scenarios:
            data = _to_dict(scenario)
            scenario_type = str(data.get("type", data.get("scenarioType", ""))).strip().lower()
            if scenario_type == "negative":
                negative_scenarios += 1
            else:
                positive_scenarios += 1

    if negative_scenarios == 0:
        negative_scenarios = _count_or_length(bdd.get("negativeCases"))

    total_scenarios = _count_or_length(bdd.get("total_scenarios"))
    if total_scenarios == 0:
        if scenarios and any(isinstance(item, dict) for item in scenarios):
            total_scenarios = positive_scenarios + negative_scenarios
        else:
            total_scenarios = positive_scenarios + negative_scenarios

    edge_cases = _count_or_length(bdd.get("edge_cases"))
    if edge_cases == 0:
        edge_cases = _count_or_length(bdd.get("edgeCases"))

    ambiguities = _count_or_length(bdd.get("ambiguities"))
    risks = _count_or_length(bdd.get("risks"))
    refinement_questions = _count_or_length(bdd.get("refinement_questions"))
    if refinement_questions == 0:
        refinement_questions = _count_or_length(bdd.get("questionsForRefinement"))
    automation_suggestions = _count_or_length(bdd.get("automation_suggestions"))
    if automation_suggestions == 0:
        automation_suggestions = _count_or_length(bdd.get("automationSuggestions"))

    return BDDMetrics(
        positive_scenarios=positive_scenarios,
        negative_scenarios=negative_scenarios,
        total_scenarios=total_scenarios,
        edge_cases=edge_cases,
        ambiguities=ambiguities,
        risks=risks,
        refinement_questions=refinement_questions,
        automation_suggestions=automation_suggestions,
    )


def compute_coverage(bdd_metrics: BDDMetrics) -> int:
    return (
        bdd_metrics.total_scenarios
        + bdd_metrics.edge_cases
        + bdd_metrics.ambiguities
        + bdd_metrics.risks
    )


def compute_core_metrics(
    invest: dict[str, Any], compliance: dict[str, Any], bdd: dict[str, Any]
) -> CoreMetrics:
    invest_metrics = compute_invest_metrics(invest)
    compliance_metrics = compute_compliance_metrics(compliance)
    bdd_metrics = compute_bdd_metrics(bdd)
    coverage = compute_coverage(bdd_metrics)

    return CoreMetrics(
        invest=invest_metrics,
        compliance=compliance_metrics,
        bdd=bdd_metrics,
        coverage=coverage,
    )


def compute_composite_metrics(
    invest_score_pct: float,
    compliance_score_pct: float,
    bdd_metrics: BDDMetrics,
    coverage_cap: int = 20,
) -> CompositeMetrics:
    coverage = float(compute_coverage(bdd_metrics))
    capped_coverage = min(max(coverage, 0.0), float(coverage_cap))
    coverage_normalized_0_10 = (capped_coverage / float(coverage_cap)) * 10.0 if coverage_cap > 0 else 0.0

    robustness_0_10 = ((compliance_score_pct / 10.0) + (invest_score_pct / 10.0) + coverage_normalized_0_10) / 3.0

    return CompositeMetrics(
        coverage=round(coverage, 4),
        coverage_normalized_0_10=round(coverage_normalized_0_10, 4),
        robustness_0_10=round(robustness_0_10, 4),
    )
