"""Live checks against the locally running LM Studio model."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from .evaluation_cases import CASES
from .intake_graph import build_intake_graph, make_initial_state


EXPECTED_OUTCOMES = {
    "active_policy": ("ready_for_review", "active", True),
    "inactive_policy": ("policy_inactive_needs_review", "inactive", True),
    "missing_policy_number": ("needs_information", None, None),
    "missing_incident_date": ("needs_information", None, None),
    "unknown_policy": ("policy_not_found", None, None),
    "name_mismatch": ("ready_for_review", "active", False),
}


def run_live_evaluation(case_names: list[str] | None = None) -> bool:
    selected = [case for case in CASES if case_names is None or case["name"] in case_names]
    if not selected:
        raise ValueError("No evaluation cases selected")

    graph = build_intake_graph(InMemorySaver())
    passed = 0
    total = 0

    def check(label: str, actual, expected) -> None:
        nonlocal passed, total
        total += 1
        success = actual == expected
        passed += success
        print(f"  {'PASS' if success else 'FAIL'} {label}: {actual!r} (expected {expected!r})")

    for case in selected:
        name = case["name"]
        print(f"\nCase: {name}")
        config = {"configurable": {"thread_id": f"eval-{name}"}}
        result = graph.invoke(
            make_initial_state(f"CLM-EVAL-{name}", case["description"]),
            config=config,
        )
        for field, expected in case["expected"].items():
            check(field, result["claim"].get(field), expected)

        status, policy_status, names_match = EXPECTED_OUTCOMES[name]
        check("status", result["status"], status)
        if status == "needs_information":
            missing_field = (
                "policy_number" if name == "missing_policy_number" else "incident_date"
            )
            check("missing_fields", result["missing_fields"], [missing_field])
            check("policy", result["policy"], None)
        elif status == "policy_not_found":
            check("policy", result["policy"], None)
            check("paused", "__interrupt__" in result, False)
        else:
            request = result.get("__interrupt__", ())
            check("paused", bool(request), True)
            if request:
                check("policy_status", request[0].value["policy_status"], policy_status)
                check("names_match", request[0].value["names_match"], names_match)
            if name == "active_policy" and request:
                resumed = graph.invoke(
                    Command(resume={"decision": "yes", "reason": "Demo review"}),
                    config=config,
                )
                check("review_decision", resumed["review_decision"], "yes")
                check("review_reason", resumed["review_reason"], "Demo review")
                check("resumed_status", resumed["status"], "proceed_to_review")

    print(f"\nSummary: {passed}/{total} checks passed")
    return passed == total
