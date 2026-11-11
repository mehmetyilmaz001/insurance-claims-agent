"""Check that complete claims reach the human-review pause."""

from langgraph.checkpoint.memory import InMemorySaver

from eval_cases import CASES
from try_model import build_intake_graph


graph = build_intake_graph(InMemorySaver())

for case_name, policy_number, policy_status, expected_status in (
    ("active_policy", "POL-123", "active", "ready_for_review"),
    ("inactive_policy", "POL-456", "inactive", "policy_inactive_needs_review"),
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

    assert result["status"] == expected_status
    assert result["missing_fields"] == []
    assert result["policy"]["policy_number"] == policy_number
    assert result["names_match"] is True
    assert "__interrupt__" in result

    review_request = result["__interrupt__"][0].value
    assert review_request["policy_number"] == policy_number
    assert review_request["policy_status"] == policy_status

    print(f"\nCase: {case_name}")
    print("Status:", result["status"])
    print("Human review request:", review_request)
