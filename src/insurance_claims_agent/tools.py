"""The model may request a lookup; this module executes and validates it."""

import json

from .policies import lookup_policy


POLICY_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_policy",
        "description": "Retrieve a fictional policy record by policy number",
        "parameters": {
            "type": "object",
            "properties": {"policy_number": {"type": "string"}},
            "required": ["policy_number"],
            "additionalProperties": False,
        },
    },
}


def execute_tool_call(tool_call: dict) -> dict:
    function = tool_call.get("function") or {}
    if function.get("name") != "lookup_policy":
        return {"error": "Unsupported tool"}
    try:
        arguments = json.loads(function.get("arguments", ""))
    except (TypeError, json.JSONDecodeError):
        return {"error": "Invalid tool arguments"}
    if not isinstance(arguments, dict):
        return {"error": "Tool arguments must be an object"}
    policy_number = arguments.get("policy_number")
    if not isinstance(policy_number, str) or not policy_number.strip():
        return {"error": "A policy number is required"}
    policy = lookup_policy(policy_number)
    return {
        "policy_number": policy_number,
        "found": policy is not None,
        "policy": policy,
    }
