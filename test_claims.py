from main import build_graph

def test_missing_date_requests_information():
    claim = {
        "claim_id": "1",
        "policy_number": "11",
        "claimant_name":"Alex",
        "incident_description": "A tone damaged my windshield.",
        "incident_date": "",
        "estimated_damage": 900.0
    }

    graph = build_graph();

    result = graph.invoke({
        "claim": claim,
        "missing_fields": [],
        "status": "pending",
        "message": ""
    })

    assert result["missing_fields"] == ["incident_date"]
    assert result["status"] == "needs_information"
    assert "incident_date" in result["message"]
