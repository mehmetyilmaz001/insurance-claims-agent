from insurance_claims_agent.claim_graph import build_claim_graph, find_missing_fields

def test_missing_date_requests_information():
    claim = {
        "claim_id": "1",
        "policy_number": "11",
        "claimant_name":"Alex",
        "incident_description": "A tone damaged my windshield.",
        "incident_date": "",
        "estimated_damage": 900.0
    }

    graph = build_claim_graph()

    result = graph.invoke({
        "claim": claim,
        "missing_fields": [],
        "status": "pending",
        "message": ""
    })

    assert result["missing_fields"] == ["incident_date"]
    assert result["status"] == "needs_information"
    assert "incident_date" in result["message"]


def test_spaces_only_name_is_missing():
    assert "claimant_name" in find_missing_fields(
        {
            "policy_number": "POL-123",
            "claimant_name": "   ",
            "incident_description": "Stone hit windshield",
            "incident_date": "2026-11-05",
            "estimated_damage": 900.0,
        }
    )
