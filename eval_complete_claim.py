"""Check that a complete claim reaches the human-review pause."""

from langgraph.checkpoint.memory import InMemorySaver

from eval_cases import CASES
from try_model import build_intake_graph


case = next(case for case in CASES if case["name"] == "active_policy")
graph = build_intake_graph(InMemorySaver())

result = graph.invoke(
    {
        "description": case["description"],
        "claim": {},
        "policy": None,
        "missing_fields": [],
        "status": "pending",
        "message": "",
        "claim_id": "CLM-EVAL-ACTIVE",
        "review_decision": None,
        "names_match": None,
        "review_reason": None,
    },
    config={"configurable": {"thread_id": "eval-active-policy"}},
)

assert result["status"] == "ready_for_review"
assert result["missing_fields"] == []
assert result["policy"]["policy_number"] == "POL-123"
assert result["names_match"] is True
assert "__interrupt__" in result

review_request = result["__interrupt__"][0].value
assert review_request["policy_number"] == "POL-123"
assert review_request["policy_status"] == "active"

print("Status:", result["status"])
print("Human review request:", review_request)
