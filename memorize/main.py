
from typing import TypedDict
from langgraph.graph import START, END, StateGraph

class ClaimState(TypedDict):
    claim: dict
    missing_fields: list[str]
    status: str
    message: str

def find_missing_fields(claim: dict):
    required_fields = {
        "policy_number",
        "claimant_name",
        "incident_description",
        "incident_date",
        "estimated_damage"
    }
    
    missing_fields = []
    
    for field in required_fields:
        value = claim.get(field)
        
        if value is None or (isinstance(value, str) and value.strip() == ""):
            missing_fields.append(field)
        
    return missing_fields
    
def check_claim(state: ClaimState):
    missing_fields = find_missing_fields(state["claim"])
    
    return {
        "missing_fields": missing_fields
    }

def request_details(state: ClaimState):
    missing = ", ".join(state["missing_fields"])
    
    return {
        "status": "needs_information",
        "message": f"Please provide: {missing}"
    }

def ready_for_review(state):
    return {
        "status": "ready_for_review",
        "message": "All required details are present. The claim is ready for review"
    }
    
def route_claim(state: ClaimState):
    missing_fields = state["missing_fields"]
    
    if missing_fields:
        return "incomplete"
    return "complete"

def build_graph():
    builder = StateGraph(ClaimState)
    
    builder.add_node("check_claim", check_claim)
    builder.add_node("request_details", request_details)
    builder.add_node("ready_for_review", ready_for_review)
    
    builder.add_edge(START, "check_claim")
    
    builder.add_conditional_edges(
        "check_claim",
        route_claim, 
        {
            "incomplete": "request_details",
            "complete": "ready_for_review"
        }
    )
    
    builder.add_edge("request_details", END)
    builder.add_edge("ready_for_review", END)
    
    return builder.compile()
    

def main():
    claim = {
        "claim_id": "CLAIM_1",
        "claimant_name": "Alex Morgan",
        "policy_number": "POL-123",
        "incident_date": "2026-11-08",
        "incident_description": "My car's windshield was damaged by a stone.",
        "estimated_damage": 900.0
    }
    
    graph = build_graph()
    
    initial_state = {
        "claim": claim,
        "missing_fields": [],
        "status": "pending",
        "message": ""
    }
    
    for update in graph.stream(initial_state, stream_mode="updates"):
        print(update)

if __name__ == "__main__":
    main()