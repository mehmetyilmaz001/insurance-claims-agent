from openai import OpenAI
from insurance_claims_agent.tools import POLICY_TOOL, execute_tool_call
import json


def main():
    client = OpenAI(
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        max_retries=0
    )
    
    messages = [
            {
                "role": "system",
                "content": (
                    "Use the lookup tool for policy information. "
                    "Base your answer on the returned record. "
                    "If no record is found, say so. "
                    "Do not infer claim coverage or approval."
                )    
            },
            {
                "role": "user",
                "content": "Lookup the policy record for POL-123."
            }
    ]
    
    response = client.chat.completions.create(
        model="gemma-4-e4b-it",
        messages=messages,
        tools=[POLICY_TOOL]
    )
    
    message = response.choices[0].message
    
    if message.tool_calls:
        messages.append(message.model_dump(exclude_none=True))
        
        for tool_call in message.tool_calls:
            tool_result = execute_tool_call(tool_call.model_dump(exclude_none=True))
            
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result),
            })
            
        final_response = client.chat.completions.create(
            model="gemma-4-e4b-it",
            messages=messages
        )
        
        print("Gemma's answer: ")
        print(final_response.choices[0].message.content)
                               
    else:
        print("No tool call returned")
        print(message.content)
        
if __name__ == "__main__":
    main()
