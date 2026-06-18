from __future__ import annotations

from dataclasses import dataclass
import re
import unicodedata
from typing import Any


STOPWORDS = {
    "a", "o", "os", "as", "de", "da", "do", "das", "dos", "e", "ou", "em", "no", "na", "nos", "nas",
    "um", "uma", "uns", "umas", "para", "por", "com", "sem", "que", "se", "ao", "aos", "ate", "ser",
    "dado", "quando", "entao", "then", "when", "given", "the", "and", "or", "to", "for", "of", "in",
}

VAGUE_TERMS = {
    "adequado", "adequada", "correto", "corretamente", "bom", "boa", "melhor", "util", "apropriado",
    "apropriada", "sem", "problemas", "esperado", "esperada", "suficiente", "otimo", "otima",
}


@dataclass(frozen=True)
class BDDAplicabilityMetrics:
    score_0_10: float
    level: str
    ac_total: int
    ac_covered: int
    ac_coverage_ratio: float
    scenarios_total: int
    scenarios_applicable: int
    scenario_quality_avg: float
    reasons: list[str]


def _to_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    return []


def extract_acceptance_criteria(raw: dict[str, Any]) -> list[str]:
    original_story = raw.get("originalStory") if isinstance(raw, dict) else None
    approved_story = raw.get("approvedStory") if isinstance(raw, dict) else None

    for story in (original_story, approved_story):
        if isinstance(story, dict):
            criteria = story.get("acceptanceCriteria")
            if isinstance(criteria, list):
                cleaned = [str(item).strip() for item in criteria if str(item).strip()]
                if cleaned:
                    return cleaned
    return []


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def _tokenize(text: str) -> set[str]:
    normalized = _normalize(text)
    tokens = set(re.findall(r"[a-z0-9_]{3,}", normalized))
    return {token for token in tokens if token not in STOPWORDS}


def _scenario_text(scenario: dict[str, Any]) -> str:
    pieces: list[str] = []
    pieces.append(str(scenario.get("title", "")).strip())
    for key in ("given", "when", "then", "notes"):
        values = scenario.get(key)
        if isinstance(values, list):
            pieces.extend(str(item).strip() for item in values if str(item).strip())
    return " ".join(piece for piece in pieces if piece)


def _max_overlap_ratio(base_tokens: set[str], candidates: list[set[str]]) -> float:
    if not base_tokens or not candidates:
        return 0.0
    max_ratio = 0.0
    for candidate in candidates:
        if not candidate:
            continue
        overlap = len(base_tokens.intersection(candidate))
        ratio = overlap / float(len(base_tokens))
        if ratio > max_ratio:
            max_ratio = ratio
    return max_ratio


def _has_vague_then(scenario: dict[str, Any]) -> bool:
    then_values = scenario.get("then")
    if not isinstance(then_values, list):
        return True
    then_text = " ".join(str(item).strip() for item in then_values if str(item).strip())
    if not then_text:
        return True
    tokens = _tokenize(then_text)
    return len(tokens.intersection(VAGUE_TERMS)) > 0


def _level_from_score(score_0_10: float) -> str:
    if score_0_10 >= 8.0:
        return "HIGH"
    if score_0_10 >= 6.0:
        return "MEDIUM"
    return "LOW"


def compute_bdd_applicability(
    acceptance_criteria: list[str],
    bdd_payload: dict[str, Any],
) -> BDDAplicabilityMetrics:
    scenarios = _to_list(bdd_payload.get("bddScenarios"))
    if not scenarios:
        scenarios = _to_list(bdd_payload.get("scenarios"))

    scenario_dicts = [item for item in scenarios if isinstance(item, dict)]
    scenarios_total = len(scenario_dicts)

    if scenarios_total == 0:
        return BDDAplicabilityMetrics(
            score_0_10=0.0,
            level="LOW",
            ac_total=len(acceptance_criteria),
            ac_covered=0,
            ac_coverage_ratio=0.0,
            scenarios_total=0,
            scenarios_applicable=0,
            scenario_quality_avg=0.0,
            reasons=["Nenhum cenario BDD gerado para avaliar aplicabilidade."],
        )

    ac_tokens = [_tokenize(item) for item in acceptance_criteria if item.strip()]
    scenario_tokens = [_tokenize(_scenario_text(item)) for item in scenario_dicts]

    covered = 0
    for tokens in ac_tokens:
        if not tokens:
            continue
        overlap = _max_overlap_ratio(tokens, scenario_tokens)
        if overlap >= 0.25:
            covered += 1

    ac_total = len(ac_tokens)
    ac_coverage_ratio = (covered / float(ac_total)) if ac_total > 0 else 0.0

    scenario_scores: list[float] = []
    scenarios_applicable = 0

    for idx, scenario in enumerate(scenario_dicts):
        has_given = isinstance(scenario.get("given"), list) and len(_to_list(scenario.get("given"))) > 0
        has_when = isinstance(scenario.get("when"), list) and len(_to_list(scenario.get("when"))) > 0
        has_then = isinstance(scenario.get("then"), list) and len(_to_list(scenario.get("then"))) > 0
        completeness = 1.0 if (has_given and has_when and has_then) else 0.0

        alignment = 0.0
        if ac_tokens:
            alignment = _max_overlap_ratio(scenario_tokens[idx], ac_tokens)
            alignment = min(1.0, alignment * 2.0)

        testability = 0.4 if _has_vague_then(scenario) else 1.0

        score = 0.4 * completeness + 0.4 * alignment + 0.2 * testability
        scenario_scores.append(score)
        if score >= 0.6:
            scenarios_applicable += 1

    scenario_quality_avg = sum(scenario_scores) / float(len(scenario_scores)) if scenario_scores else 0.0
    applicable_ratio = scenarios_applicable / float(scenarios_total)

    score_0_10 = round(
        (0.45 * ac_coverage_ratio + 0.35 * applicable_ratio + 0.20 * scenario_quality_avg) * 10.0,
        4,
    )

    reasons: list[str] = []
    reasons.append(f"Cobertura de criterios de aceite: {covered}/{ac_total if ac_total else 0}.")
    reasons.append(f"Cenarios aplicaveis: {scenarios_applicable}/{scenarios_total}.")
    if scenario_quality_avg < 0.6:
        reasons.append("Qualidade media dos cenarios baixa (falta de alinhamento ou testabilidade).")
    if ac_total > 0 and ac_coverage_ratio < 0.5:
        reasons.append("Menos de 50% dos criterios de aceite cobertos por cenarios.")

    return BDDAplicabilityMetrics(
        score_0_10=score_0_10,
        level=_level_from_score(score_0_10),
        ac_total=ac_total,
        ac_covered=covered,
        ac_coverage_ratio=round(ac_coverage_ratio, 4),
        scenarios_total=scenarios_total,
        scenarios_applicable=scenarios_applicable,
        scenario_quality_avg=round(scenario_quality_avg, 4),
        reasons=reasons,
    )