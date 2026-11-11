import json

from insurance_claims_agent.policy_adapter import find_policy_result
from insurance_claims_agent.tools import execute_tool_call


def test_tool_result_is_matched_to_requested_number():
    messages = [
        {"role": "tool", "content": json.dumps({"policy_number": "POL-999", "found": False, "policy": None})},
        {"role": "tool", "content": json.dumps(execute_tool_call({"function": {"name": "lookup_policy", "arguments": '{"policy_number":"POL-123"}'}}))},
    ]
    assert find_policy_result(messages, "POL-123")["policy"]["status"] == "active"
    assert find_policy_result(messages, "POL-999")["policy"] is None
    assert find_policy_result(messages, "POL-456") is None


def test_invalid_tool_arguments_do_not_query_policy():
    result = execute_tool_call({"function": {"name": "lookup_policy", "arguments": "not json"}})
    assert "error" in result
