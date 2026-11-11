"""Check that incomplete claims stop before policy lookup."""

from langgraph.checkpoint.memory import InMemorySaver

from eval_cases import CASES
from try_model import build_intake_graph


graph = build_intake_graph(InMemorySaver())

for case_name, expected_missing in (
    ("missing_incident_date", ["incident_date"]),
    ("missing_policy_number", ["policy_number"]),
):
    case = next(case for case in CASES if case["name"] == case_name)
    result = graph.invoke(
        {
            "description": case["description"],
            "claim": {},
            "policy": None,
            "missing_fields": [],
            "status": "pending",
            "message": "",
            "claim_id": f"CLM-EVAL-{case_name}",
            "review_decision": None,
            "names_match": None,
            "review_reason": None,
        },
        config={"configurable": {"thread_id": f"eval-{case_name}"}},
    )

    print(f"\nCase: {case_name}")
    print("Status:", result["status"])
    print("Missing fields:", result["missing_fields"])
    print("Message:", result["message"])

    assert result["status"] == "needs_information"
    assert result["missing_fields"] == expected_missing
    assert result["policy"] is None
    assert "__interrupt__" not in result
