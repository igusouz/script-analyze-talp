from analyzer.bdd_applicability import compute_bdd_applicability


def test_bdd_applicability_high_for_aligned_scenarios() -> None:
    acceptance_criteria = [
        "Dado validacao pendente quando confirmar entao sistema bloqueia liberacao",
        "Dado validacao aprovada quando confirmar entao sistema libera prescricao",
    ]
    bdd_payload = {
        "bddScenarios": [
            {
                "title": "Bloqueia com validacao pendente",
                "scenarioType": "negative",
                "given": ["validacao pendente"],
                "when": ["medico confirma prescricao"],
                "then": ["sistema bloqueia liberacao"],
            },
            {
                "title": "Libera com validacao aprovada",
                "scenarioType": "positive",
                "given": ["validacao aprovada"],
                "when": ["medico confirma prescricao"],
                "then": ["sistema libera prescricao"],
            },
        ]
    }

    result = compute_bdd_applicability(acceptance_criteria, bdd_payload)

    assert result.ac_total == 2
    assert result.ac_covered == 2
    assert result.scenarios_total == 2
    assert result.scenarios_applicable >= 1
    assert result.score_0_10 >= 6.0


def test_bdd_applicability_low_for_empty_scenarios() -> None:
    acceptance_criteria = ["Dado algo quando acao entao resultado"]
    bdd_payload = {"bddScenarios": []}

    result = compute_bdd_applicability(acceptance_criteria, bdd_payload)

    assert result.score_0_10 == 0.0
    assert result.level == "LOW"
    assert result.scenarios_total == 0
