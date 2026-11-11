"""Read a requested policy lookup from the tool agent's conversation."""

import json


def find_policy_result(
    messages: list[dict], requested_number: str
) -> dict | None:
    for message in reversed(messages):
        if message.get("role") != "tool":
            continue

        try:
            result = json.loads(message["content"])
        except (KeyError, TypeError, json.JSONDecodeError):
            continue

        if not isinstance(result, dict):
            continue
        if result.get("policy_number") != requested_number:
            continue

        policy = result.get("policy")
        if result.get("found") is True:
            if isinstance(policy, dict) and policy.get("policy_number") == requested_number:
                return result
        elif result.get("found") is False and policy is None:
            return result

    return None
