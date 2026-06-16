from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


STOPWORDS = {
    "a",
    "ao",
    "as",
    "com",
    "da",
    "das",
    "de",
    "do",
    "dos",
    "e",
    "em",
    "o",
    "os",
    "para",
    "por",
    "que",
    "se",
    "the",
    "to",
    "in",
    "of",
    "and",
    "for",
}

GENERIC_REASON_HINTS = {
    "falta detalhes",
    "falta de detalhes",
    "insuficiente",
    "genérico",
    "generic",
    "unclear",
    "vago",
    "não está claro",
    "needs refinement",
}


@dataclass(frozen=True)
class HallucinationResult:
    score: float
    level: str
    bdd_unrelated_ratio: float
    compliance_no_evidence_ratio: float
    invest_generic_ratio: float
    orphan_findings_ratio: float


@dataclass(frozen=True)
class HallucinationMetrics:
    score_0_10: float
    level: str
    reasons: list[str]


def _tokenize(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z0-9_À-ÿ]+", text.lower())
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


def _safe_ratio(num: float, den: float) -> float:
    if den <= 0:
        return 0.0
    return num / den


def _dict(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return item
    return {}


def _list(item: Any) -> list[Any]:
    if isinstance(item, list):
        return item
    return []


def _string(item: Any) -> str:
    if item is None:
        return ""
    return str(item)


def _collect_scenario_texts(bdd: dict[str, Any]) -> list[str]:
    scenarios = _list(bdd.get("scenarios"))
    if not scenarios:
        scenarios = _list(bdd.get("bddScenarios"))
    texts: list[str] = []
    for scenario in scenarios:
        if isinstance(scenario, str):
            text = scenario.strip()
            if text:
                texts.append(text)
            continue
        data = _dict(scenario)
        chunks = [
            _string(data.get("title")),
            _string(data.get("name")),
            _string(data.get("notes")),
            _string(data.get("given")),
            _string(data.get("when")),
            _string(data.get("then")),
            _string(data.get("description")),
        ]
        text = " ".join(part for part in chunks if part).strip()
        if text:
            texts.append(text)
    return texts


def _collect_text_items(section: dict[str, Any], key: str) -> list[str]:
    values = _list(section.get(key))
    texts: list[str] = []
    for value in values:
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict):
            text = _string(value.get("text") or value.get("description") or value.get("title"))
            if text:
                texts.append(text)
    return texts


def evaluate_hallucination(
    user_story: str,
    invest: dict[str, Any],
    compliance: dict[str, Any],
    bdd: dict[str, Any],
) -> HallucinationResult:
    story_tokens = _tokenize(user_story)

    scenario_texts = _collect_scenario_texts(bdd)
    unrelated_scenarios = 0
    for scenario_text in scenario_texts:
        tokens = _tokenize(scenario_text)
        overlap = len(tokens & story_tokens)
        ratio = _safe_ratio(overlap, len(tokens) if tokens else 1)
        if ratio < 0.15:
            unrelated_scenarios += 1
    bdd_unrelated_ratio = _safe_ratio(unrelated_scenarios, len(scenario_texts))

    compliance_rules = _list(compliance.get("rules"))
    if not compliance_rules:
        compliance_rules = _list(compliance.get("detectedRules"))
    rules_without_evidence = 0
    considered_rules = 0
    for rule in compliance_rules:
        rule_data = _dict(rule)
        mandatory = rule_data.get("mandatory")
        if mandatory is False:
            continue
        considered_rules += 1
        evidence = _string(rule_data.get("evidence") or rule_data.get("found_evidence") or rule_data.get("evidence_found"))
        satisfied = rule_data.get("satisfied")
        matched = rule_data.get("matched")
        if (satisfied is True or matched is True) and not evidence.strip():
            rules_without_evidence += 1
    compliance_no_evidence_ratio = _safe_ratio(rules_without_evidence, considered_rules)

    failed_reasons = _collect_text_items(invest, "failed_reasons")
    if not failed_reasons:
        for key, value in invest.items():
            if not isinstance(value, dict):
                continue
            status = str(value.get("status", "")).strip().lower()
            if status in {"fail", "failed", "rejected", "false"}:
                reason = _string(value.get("reason"))
                if reason:
                    failed_reasons.append(reason)
    generic_reasons = 0
    for reason in failed_reasons:
        low = reason.lower().strip()
        short_reason = len(_tokenize(low)) <= 3
        contains_hint = any(hint in low for hint in GENERIC_REASON_HINTS)
        if short_reason or contains_hint:
            generic_reasons += 1
    invest_generic_ratio = _safe_ratio(generic_reasons, len(failed_reasons))

    orphan_texts = (
        _collect_text_items(bdd, "ambiguities")
        + _collect_text_items(bdd, "ambiguities_list")
        + _collect_text_items(bdd, "risks")
        + _collect_text_items(bdd, "risks_list")
        + _collect_text_items(bdd, "edgeCases")
        + _collect_text_items(bdd, "negativeCases")
        + _collect_text_items(bdd, "questionsForRefinement")
        + _collect_text_items(bdd, "requirements")
    )
    orphan_items = 0
    for text in orphan_texts:
        tokens = _tokenize(text)
        overlap = len(tokens & story_tokens)
        ratio = _safe_ratio(overlap, len(tokens) if tokens else 1)
        if ratio < 0.2:
            orphan_items += 1
    orphan_findings_ratio = _safe_ratio(orphan_items, len(orphan_texts))

    score = round(
        min(
            10.0,
            (bdd_unrelated_ratio * 4.0)
            + (compliance_no_evidence_ratio * 2.5)
            + (invest_generic_ratio * 1.5)
            + (orphan_findings_ratio * 2.0),
        ),
        2,
    )

    if score < 3.5:
        level = "LOW"
    elif score < 7.0:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return HallucinationResult(
        score=score,
        level=level,
        bdd_unrelated_ratio=round(bdd_unrelated_ratio, 4),
        compliance_no_evidence_ratio=round(compliance_no_evidence_ratio, 4),
        invest_generic_ratio=round(invest_generic_ratio, 4),
        orphan_findings_ratio=round(orphan_findings_ratio, 4),
    )


def compute_hallucination_metrics(
    user_story: str,
    invest_data: dict[str, Any],
    compliance_data: dict[str, Any],
    bdd_data: dict[str, Any],
) -> HallucinationMetrics:
    result = evaluate_hallucination(
        user_story=user_story,
        invest=invest_data,
        compliance=compliance_data,
        bdd=bdd_data,
    )

    reasons: list[str] = []
    if result.bdd_unrelated_ratio > 0.3:
        reasons.append("BDD possui cenarios pouco ancorados na User Story")
    if result.compliance_no_evidence_ratio > 0.2:
        reasons.append("Compliance identifica regras satisfeitas sem evidencia")
    if result.invest_generic_ratio > 0.2:
        reasons.append("INVEST reprova criterios com justificativas genericas")
    if result.orphan_findings_ratio > 0.3:
        reasons.append("Ambiguidades/riscos sem relacao clara com a User Story")

    return HallucinationMetrics(
        score_0_10=result.score,
        level=result.level,
        reasons=reasons,
    )
