"""Claim extraction, validation, policy lookup, and human review."""

from typing import Annotated, Literal, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt
from openai import APIConnectionError, OpenAI, OpenAIError
from pydantic import BaseModel, StringConstraints, ValidationError

from .claim_graph import build_claim_graph
from .config import Settings
from .policy_adapter import find_policy_result
from .tool_graph import build_tool_graph


class IntakeState(TypedDict):
    description: str
    claim: dict
    policy: dict | None
    missing_fields: list[str]
    status: str
    message: str
    claim_id: str
    review_decision: str | None
    review_reason: str | None
    names_match: bool | None


class ExtractedClaim(BaseModel):
    claimant_name: str | None = None
    policy_number: str | None = None
    incident_description: str | None = None
    incident_date: str | None = None
    estimated_damage: float | None = None


class ReviewResponse(BaseModel):
    decision: Literal["yes", "no"]
    reason: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


def make_initial_state(claim_id: str, description: str) -> IntakeState:
    return {
        "description": description,
        "claim": {},
        "policy": None,
        "missing_fields": [],
        "status": "pending",
        "message": "",
        "claim_id": claim_id,
        "review_decision": None,
        "review_reason": None,
        "names_match": None,
    }


def extract_claim(
    state: IntakeState, *, settings: Settings | None = None, client=None
) -> dict:
    settings = settings or Settings.from_env()
    client = client or OpenAI(
        base_url=settings.model_url, api_key="lm-studio", max_retries=0
    )
    prompt = (
        "Extract insurance claim details from the description below. "
        "Return only a JSON object with claimant_name, policy_number, "
        "incident_description, incident_date, and estimated_damage. "
        "Use only information present. Use null for missing information. "
        "Format incident_date as YYYY-MM-DD. Return estimated_damage as a number. "
        "Do not include explanations or Markdown code fences.\n\n"
        f"Description:\n{state['description']}"
    )
    try:
        response = client.chat.completions.create(
            model=settings.model_name,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "insurance_claim",
                    "schema": ExtractedClaim.model_json_schema(),
                },
            },
            messages=[{"role": "user", "content": prompt}],
        )
        response_text = response.choices[0].message.content
    except OpenAIError:
        return {
            "claim": {},
            "status": "extraction_failed",
            "message": "Could not get a response from LM Studio. Check the local server and model.",
        }
    try:
        claim = ExtractedClaim.model_validate_json(response_text, strict=True)
    except (ValidationError, TypeError, ValueError):
        return {
            "claim": {},
            "status": "extraction_failed",
            "message": "The model returned invalid claim data.",
        }
    return {"claim": claim.model_dump()}


def fetch_policy(
    state: IntakeState, *, settings: Settings | None = None, client=None
) -> dict:
    settings = settings or Settings.from_env()
    policy_number = state["claim"]["policy_number"]
    try:
        result = build_tool_graph(settings=settings, client=client).invoke(
            {
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Look up the requested policy using lookup_policy. "
                            "Do not infer coverage or approval."
                        ),
                    },
                    {"role": "user", "content": f"Look up policy {policy_number}."},
                ],
                "tool_calls": [],
                "tool_rounds": 0,
            },
            config={"configurable": {"thread_id": f"lookup-{state['claim_id']}"}},
        )
    except APIConnectionError:
        return {
            "policy": None,
            "status": "lookup_failed",
            "message": "Could not reach LM Studio for policy lookup.",
        }
    except OpenAIError:
        return {
            "policy": None,
            "status": "lookup_failed",
            "message": "The local model could not complete policy lookup.",
        }

    lookup = find_policy_result(result["messages"], policy_number)
    if lookup is None:
        return {
            "policy": None,
            "status": "lookup_failed",
            "message": f"No verified tool result for policy {policy_number}.",
        }
    policy = lookup["policy"]
    if policy is None:
        return {
            "policy": None,
            "status": "policy_not_found",
            "message": f"No policy record found for {policy_number}.",
        }
    if policy["status"] != "active":
        return {
            "policy": policy,
            "status": "policy_inactive_needs_review",
            "message": "Policy is inactive. A human must review the record.",
        }
    return {
        "policy": policy,
        "status": "ready_for_review",
        "message": "Policy record found. The claim is ready for human review.",
    }


def check_names(state: IntakeState) -> dict:
    claimant = state["claim"]["claimant_name"]
    holder = state["policy"]["policy_holder"]
    return {"names_match": claimant.strip().casefold() == holder.strip().casefold()}


def pause_for_review(state: IntakeState) -> dict:
    response = interrupt(
        {
            "claim_id": state["claim_id"],
            "policy_number": state["claim"]["policy_number"],
            "claimant_name": state["claim"]["claimant_name"],
            "policy_holder": state["policy"]["policy_holder"],
            "policy_status": state["policy"]["status"],
            "names_match": state["names_match"],
            "question": "Should this fictional claim proceed to human review?",
        },
        response_schema=ReviewResponse,
    )
    return {
        "review_decision": response.decision,
        "review_reason": response.reason,
        "status": "proceed_to_review" if response.decision == "yes" else "on_hold",
    }


def build_intake_graph(
    checkpointer, *, extractor=None, policy_fetcher=None
):
    """Inject model-facing nodes in offline tests; use real nodes by default."""
    builder = StateGraph(IntakeState)
    builder.add_node("extract_claim", extractor or extract_claim)
    builder.add_node("check_workflow", build_claim_graph())
    builder.add_node("fetch_policy", policy_fetcher or fetch_policy)
    builder.add_node("check_names", check_names)
    builder.add_node("pause_for_review", pause_for_review)
    builder.add_edge(START, "extract_claim")
    builder.add_conditional_edges(
        "extract_claim",
        lambda state: "failed" if state["status"] == "extraction_failed" else "success",
        {"failed": END, "success": "check_workflow"},
    )
    builder.add_conditional_edges(
        "check_workflow",
        lambda state: "lookup" if state["status"] == "ready_for_review" else "stop",
        {"lookup": "fetch_policy", "stop": END},
    )
    builder.add_conditional_edges(
        "fetch_policy",
        lambda state: "review" if state["policy"] is not None else "stop",
        {"review": "check_names", "stop": END},
    )
    builder.add_edge("check_names", "pause_for_review")
    builder.add_edge("pause_for_review", END)
    return builder.compile(checkpointer=checkpointer)
