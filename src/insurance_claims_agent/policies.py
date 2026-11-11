"""Fictional policy records used by the lookup tool."""

POLICIES = {
    "POL-123": {
        "policy_number": "POL-123",
        "policy_holder": "Alex Morgan",
        "product": "Motor Insurance",
        "status": "active"
    },
    "POL-456": {
        "policy_number": "POL-456",
        "policy_holder": "Sam Taylor",
        "product": "Motor Insurance",
        "status": "inactive",
    },
}

def lookup_policy(policy_number: str) -> dict | None:
    """Return a fictional policy record, or None if it is unknown."""
    return POLICIES.get(policy_number)
