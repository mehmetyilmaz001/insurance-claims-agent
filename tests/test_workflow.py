"""Fast offline checks of the graph's decisions and reviewer resume."""

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from insurance_claims_agent.intake_graph import (
    ReviewResponse,
    build_intake_graph,
    make_initial_state,
)
from insurance_claims_agent.policies import lookup_policy


BASE_CLAIM = {
    "claimant_name": "Alex Morgan",
    "policy_number": "POL-123",
    "incident_description": "A stone hit the windshield.",
    "incident_date": "2026-11-05",
    "estimated_damage": 900.0,
}


def run_case(claim: dict, claim_id: str = "TEST"):
    def extractor(_state):
        return {"claim": claim}

    def policy_fetcher(state):
        number = state["claim"]["policy_number"]
        policy = lookup_policy(number)
        if policy is None:
            return {"policy": None, "status": "policy_not_found", "message": "Not found"}
        status = "ready_for_review" if policy["status"] == "active" else "policy_inactive_needs_review"
        return {"policy": policy, "status": status, "message": "Policy checked"}

    graph = build_intake_graph(
        InMemorySaver(), extractor=extractor, policy_fetcher=policy_fetcher
    )
    config = {"configurable": {"thread_id": claim_id}}
    result = graph.invoke(make_initial_state(claim_id, "offline example"), config=config)
    return graph, config, result


@pytest.mark.parametrize(
    ("field", "expected"),
    [("incident_date", "incident_date"), ("policy_number", "policy_number")],
)
def test_incomplete_claim_stops_before_lookup(field, expected):
    _, _, result = run_case({**BASE_CLAIM, field: None})
    assert result["status"] == "needs_information"
    assert result["missing_fields"] == [expected]
    assert result["policy"] is None
    assert "__interrupt__" not in result


def test_unknown_policy_stops_without_review():
    _, _, result = run_case({**BASE_CLAIM, "policy_number": "POL-999"})
    assert result["status"] == "policy_not_found"
    assert "__interrupt__" not in result


@pytest.mark.parametrize(
    ("claim", "policy_status", "names_match"),
    [
        (BASE_CLAIM, "active", True),
        ({**BASE_CLAIM, "policy_number": "POL-456", "claimant_name": "Sam Taylor"}, "inactive", True),
        ({**BASE_CLAIM, "claimant_name": "Casey Rivera"}, "active", False),
    ],
)
def test_review_request_shows_policy_and_name_check(claim, policy_status, names_match):
    _, _, result = run_case(claim)
    request = result["__interrupt__"][0].value
    assert request["policy_status"] == policy_status
    assert request["names_match"] is names_match


@pytest.mark.parametrize(
    ("decision", "expected_status"),
    [("yes", "proceed_to_review"), ("no", "on_hold")],
)
def test_review_resume_saves_decision_and_reason(decision, expected_status):
    graph, config, paused = run_case(BASE_CLAIM)
    assert "__interrupt__" in paused
    result = graph.invoke(
        Command(resume={"decision": decision, "reason": "  Manual check  "}),
        config=config,
    )
    assert result["status"] == expected_status
    assert result["review_decision"] == decision
    assert result["review_reason"] == "Manual check"
    assert graph.get_state(config).values["review_reason"] == "Manual check"


@pytest.mark.parametrize(
    "response",
    [{"decision": "maybe", "reason": "Check"}, {"decision": "yes", "reason": "   "}],
)
def test_invalid_review_response_is_rejected(response):
    with pytest.raises(ValidationError):
        ReviewResponse.model_validate(response)
