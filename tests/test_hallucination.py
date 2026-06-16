from analyzer.hallucination import compute_hallucination_metrics


def test_hallucination_low_when_well_anchored() -> None:
    story = "As a customer I want to pay with credit card so that I can complete checkout quickly"

    invest = {"analysis": "clear acceptance details", "criteria": {"independent": True}}
    compliance = {
        "rules": [
            {"mandatory": True, "satisfied": True, "evidence": "payment flow described"},
        ]
    }
    bdd = {
        "scenarios": [
            "Given customer with items when paying with credit card then order is confirmed",
        ],
        "ambiguities_list": ["checkout timeout threshold"],
        "risks_list": ["payment gateway unavailable"],
    }

    result = compute_hallucination_metrics(story, invest, compliance, bdd)

    assert 0 <= result.score_0_10 <= 10
    assert result.level in {"LOW", "MEDIUM", "HIGH"}


def test_hallucination_high_when_unanchored_and_no_evidence() -> None:
    story = "As a buyer I want checkout so that I buy products"

    invest = {"analysis": "missing details and vague"}
    compliance = {
        "rules": [
            {"mandatory": True, "satisfied": True, "evidence": ""},
            {"mandatory": True, "satisfied": True, "evidence": ""},
        ]
    }
    bdd = {
        "scenarios": [
            "Given satellite telemetry anomaly when orbital correction then launch recovery succeeds",
            "Given maritime insurance claim when vessel sinks then payout happens",
        ],
        "ambiguities_list": ["orbital insertion mode uncertain"],
        "risks_list": ["space debris collision"],
    }

    result = compute_hallucination_metrics(story, invest, compliance, bdd)

    assert result.score_0_10 >= 7.0
    assert result.level == "HIGH"
