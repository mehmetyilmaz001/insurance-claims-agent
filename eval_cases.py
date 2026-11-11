"""Small fictional examples for checking claim extraction."""

CASES = [
    {
        "name": "inactive_policy",
        "description": (
            "I am Sam Taylor. A stone damaged my windshield on November 5, 2026. "
            "My policy is POL-456. The repair estimate is 900."
        ),
        "expected": {
            "claimant_name": "Sam Taylor",
            "policy_number": "POL-456",
            "incident_date": "2026-11-05",
            "estimated_damage": 900.0,
        },
    },
    {
        "name": "missing_policy_number",
        "description": (
            "I am Jordan Lee. A stone damaged my windshield on November 5, 2026. "
            "The repair estimate is 900."
        ),
        "expected": {
            "claimant_name": "Jordan Lee",
            "policy_number": None,
        },
    },
    {
        "name": "active_policy",
        "description": (
            "I am Alex Morgan. A stone damaged my windshield on November 5, 2026. "
            "My policy is POL-123. The repair estimate is 900."
        ),
        "expected": {
            "claimant_name": "Alex Morgan",
            "policy_number": "POL-123",
        },
    },
    {
        "name": "missing_incident_date",
        "description": (
            "I am Alex Morgan. A stone damaged my windshield. "
            "My policy is POL-123. The repair estimate is 900."
        ),
        "expected": {
            "incident_date": None,
        },
    },
]
