"""Check that a claim without a date stops before policy lookup."""

from langgraph.checkpoint.memory import InMemorySaver

from eval_cases import CASES
from try_model import build_intake_graph


case = next(case for case in CASES if case["name"] == "missing_incident_date")
graph = build_intake_graph(InMemorySaver())

result = graph.invoke(
    {
        "description": case["description"],
        "claim": {},
        "policy": None,
        "missing_fields": [],
        "status": "pending",
        "message": "",
        "claim_id": "CLM-EVAL-MISSING-DATE",
        "review_decision": None,
        "names_match": None,
        "review_reason": None,
    },
    config={"configurable": {"thread_id": "eval-missing-date"}},
)

print("Status:", result["status"])
print("Missing fields:", result["missing_fields"])
print("Message:", result["message"])

assert result["status"] == "needs_information"
assert result["missing_fields"] == ["incident_date"]
assert result["policy"] is None
assert "__interrupt__" not in result
