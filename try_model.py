from typing import TypedDict

from openai import OpenAI, APIConnectionError
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError



from main import build_graph
from policy_tools import lookup_policy

class IntakeState(TypedDict):
    description: str
    claim: dict
    policy: dict
    missing_fields: list[str]
    status: str
    message: str
    
class ExtractedClaim(BaseModel):
    claimant_name: str | None = None
    policy_number: str | None = None
    incident_description: str | None = None
    incident_date: str | None = None
    estimated_damage: float | None = None

def extract_claim(state: IntakeState):
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1", 
        api_key="lm-studio",
        max_retries=0
    )
    
    description = state["description"]
    
    try:
        
        response_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "insurance_claim",
                "schema": ExtractedClaim.model_json_schema()
            }
        }
        
        response = client.chat.completions.create(
            model="gemma-4-e4b-it",
            response_format=response_format,
            messages=[
                { 
                "role": "user", 
                "content": f"""
                Extract insurance claim details from the description below.
                
                Return only a JSON object with these fields:
                - claimant_name
                - policy_number
                - incident_description
                - incident_date
                - estimated_damage
                
                Rules:
                
                - Use only information present in the description.
                - Use null for missing information.
                - Format incident_date as YYYY-MM-DD.
                - Return estimated_damage as number, without currency symbol
                - Do not include explanations or Markdown code fences.
                
                Description:
                {description}
                
                """
                }
            ]
        )
    except APIConnectionError:
        return {
            "claim": {},
            "missing_fields": [],
            "status": "extraction_failed",
            "message": """ Could not get a response from Model API. Check that the server is running and try again """
            
        }
        
    response_text = response.choices[0].message.content
    # response_text = {
    #     "estimated_damage": "nine hundred"
    # }
    
    try:
        extracted_claim = ExtractedClaim.model_validate_json(response_text, strict=True)
    except ValidationError: 
        return {
            "claim": {},
            "missing_fields": [],
            "status": "extraction_failed",
            "message": "The model returned invalid claim data. Extraction failed."
        }
    
    return {"claim": extracted_claim.model_dump()}

def route_after_extraction(state: IntakeState):
    if state["status"] == "extraction_failed":
        return "failed"
    
    return "success"

def fetch_policy(state: IntakeState):
    policy_number = state["claim"]["policy_number"]
    policy = lookup_policy(policy_number)
    
    if policy is None:
        return {
            "policy": None,
            "status": "policy_not_found",
            "message": F"No policy record found for {policy_number}."
        }
    
    return {
        "policy": policy,
        "status": "ready_for_review",
        "message": f"Policy record found. The claim is ready for human review"
    }
    
def route_after_check(state: IntakeState):
    if state["status"] == "ready_for_review":
        return "lookup"
    
    return "stop"

def build_intake_graph():
    builder = StateGraph(IntakeState)
    
    builder.add_node("extract_claim", extract_claim)
    builder.add_node("check_workflow", build_graph())
    builder.add_node("fetch_policy", fetch_policy)
    
    builder.add_edge(START, "extract_claim")
    
    builder.add_conditional_edges(
        "extract_claim",
        route_after_extraction,
        {
            "success": "check_workflow", 
            "failed": END
        },
    )
    
    builder.add_conditional_edges(
        "check_workflow",
        route_after_check,
        {
            "lookup": "fetch_policy",
            "stop": END
        }
    )
    
    builder.add_edge("fetch_policy", END)
    
    return builder.compile()


def main():
    graph = build_intake_graph()
    
    initial_state = {
        "description" : (
            "I am Alex Morgan. A stone damaged my windshield "
            "on November 5, 2026. My policy is POL-123."
            "The repair estimate is 900."
        ),
        "claim": {},
        "policy": None,
        "missing_fields": [],
        "status": "pending",
        "message": ""
    }
    
    for update in graph.stream(initial_state, stream_mode="updates"):
        print(update)
    
    

if __name__ == "__main__":
    main()