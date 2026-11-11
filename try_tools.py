from openai import OpenAI
from policy_tools import lookup_policy
import json

POLICY_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_policy",
        "description": "Retrieve a policy record using its policy number",
        "parameters": {
            "type": "object",
            "properties": {
                "policy_number": {
                    "type": "string",
                    "description": "The policy number, such as POL-123."
                }
            },
            "required": ["policy_number"],
            "additionalProperties": False
        }
    }
}

def execute_tool_call(tool_call):
    
    function_name = tool_call.function.name
    
    if function_name != "lookup_policy":
        print(f"Unsupported tool: {function_name}")
        return
    
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        print("The tool arguments were not valid JSON.")
        return
    
    if not isinstance(arguments, dict):
        print("The tool arguments must be a JSON object.")
        return
    
    policy_number = arguments.get("policy_number")
    
    if not isinstance(policy_number, str) or not policy_number.strip():
        print("The tool needs a non empty policy number.")
        return
    
    policy = lookup_policy(policy_number)
    
    return {
        "policy_number": policy_number,
        "found": policy is not None,
        "policy": policy
    }
    

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
            tool_result = execute_tool_call(tool_call)
            
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
