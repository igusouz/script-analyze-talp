from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ParsedExecution:
    file_name: str
    file_path: Path
    tipo_us: str
    user_story: str
    invest: dict[str, Any]
    compliance: dict[str, Any]
    bdd: dict[str, Any]
    raw: dict[str, Any]


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _deep_get(source: dict[str, Any], path: str) -> Any:
    current: Any = source
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _pick(source: dict[str, Any], candidates: list[str], default: Any) -> Any:
    for candidate in candidates:
        value = _deep_get(source, candidate)
        if value is not None:
            return value
    return default


def parse_json_file(path: Path) -> ParsedExecution:
    with path.open("r", encoding="utf-8") as file_obj:
        raw = json.load(file_obj)

    original_story = _as_dict(raw.get("originalStory"))
    title = str(original_story.get("title", "")).strip()
    description = str(original_story.get("description", "")).strip()
    acceptance = original_story.get("acceptanceCriteria", [])

    acceptance_lines: list[str] = []
    if isinstance(acceptance, list):
        acceptance_lines = [str(item).strip() for item in acceptance if str(item).strip()]

    rich_story_parts: list[str] = []
    if title:
        rich_story_parts.append(f"Title: {title}")
    if description:
        rich_story_parts.append(description)
    if acceptance_lines:
        rich_story_parts.append("Acceptance criteria:\n- " + "\n- ".join(acceptance_lines))

    user_story = str(
        _pick(
            raw,
            [
                "user_story",
                "userStory",
                "original_user_story",
                "story",
                "input.user_story",
                "input.story",
                "context.user_story",
            ],
            "\n\n".join(rich_story_parts),
        )
    ).strip()

    tipo_us = str(
        _pick(
            raw,
            [
                "tipo_us",
                "us_type",
                "type",
                "metadata.tipo_us",
                "input.tipo_us",
            ],
            "unknown",
        )
    ).strip()
    file_name_lower = path.name.lower()
    if tipo_us == "unknown":
        if file_name_lower.startswith("us_b_"):
            tipo_us = "boa"
        elif file_name_lower.startswith("us_f_"):
            tipo_us = "ruim"

    invest = _as_dict(
        _pick(
            raw,
            [
                "investAnalysis",
                "invest",
                "invest_result",
                "invest_agent",
                "agents.invest",
                "result.invest",
                "outputs.invest",
            ],
            {},
        )
    )

    compliance = _as_dict(
        _pick(
            raw,
            [
                "complianceAnalysis",
                "compliance",
                "compliance_result",
                "compliance_agent",
                "agents.compliance",
                "result.compliance",
                "outputs.compliance",
            ],
            {},
        )
    )

    bdd = _as_dict(
        _pick(
            raw,
            [
                "bddAnalysis",
                "bdd",
                "bdd_result",
                "bdd_agent",
                "agents.bdd",
                "result.bdd",
                "outputs.bdd",
            ],
            {},
        )
    )

    return ParsedExecution(
        file_name=path.name,
        file_path=path,
        tipo_us=tipo_us,
        user_story=user_story,
        invest=invest,
        compliance=compliance,
        bdd=bdd,
        raw=raw,
    )


def parse_folder(folder: Path, pattern: str = "*.json") -> list[ParsedExecution]:
    files = sorted(folder.glob(pattern), key=lambda item: item.name.lower())
    return [parse_json_file(path) for path in files if path.is_file()]


# Backward-compatible aliases used by the pipeline/tests.
AgentOutput = ParsedExecution


def parse_json_folder(folder: Path) -> list[ParsedExecution]:
    return parse_folder(folder)
