"""Deterministic completeness check, kept separate from model extraction."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph


REQUIRED_FIELDS = (
    "policy_number",
    "claimant_name",
    "incident_description",
    "incident_date",
    "estimated_damage",
)


class ClaimState(TypedDict):
    claim: dict
    missing_fields: list[str]
    status: str
    message: str


def find_missing_fields(claim: dict) -> list[str]:
    return [
        field
        for field in REQUIRED_FIELDS
        if (value := claim.get(field)) is None
        or (isinstance(value, str) and not value.strip())
    ]


def check_claim(state: ClaimState) -> dict:
    return {"missing_fields": find_missing_fields(state["claim"])}


def request_details(state: ClaimState) -> dict:
    missing = ", ".join(state["missing_fields"])
    return {"status": "needs_information", "message": f"Please provide {missing}"}


def ready_for_review(state: ClaimState) -> dict:
    return {
        "status": "ready_for_review",
        "message": "All required details are present. The claim is ready for review",
    }


def route_claim(state: ClaimState) -> str:
    return "incomplete" if state["missing_fields"] else "complete"


def build_claim_graph():
    builder = StateGraph(ClaimState)
    builder.add_node("check_claim", check_claim)
    builder.add_node("request_details", request_details)
    builder.add_node("ready_for_review", ready_for_review)
    builder.add_edge(START, "check_claim")
    builder.add_conditional_edges(
        "check_claim",
        route_claim,
        {"incomplete": "request_details", "complete": "ready_for_review"},
    )
    builder.add_edge("request_details", END)
    builder.add_edge("ready_for_review", END)
    return builder.compile()
