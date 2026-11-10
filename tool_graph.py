import json
from typing import TypedDict

from langgraph.graph import START, END, StateGraph
from openai import OpenAI

from try_tools import POLICY_TOOL, execute_tool_call

client = OpenAI(
    base_url = "http://127.0.0.1:1234/v1",
    api_key="lm-studio",
    max_retries=0
)

class ToolsState(TypedDict):
    messages: list[dict]
    tool_calls: list
    
    
def ask_model(state: ToolsState):
    response = client.chat.completions.create(
        model = "gemma-4-e4b-it",
        messages = state["messages"],
        tools=[POLICY_TOOL]
    )
    
    message = response.choices[0].message
    
    return {
        "messages": state["messages"] + [
            message.model_dump(exclude_none=True)
        ],
        "tool_calls": message.tool_calls or []
    }
    
def run_tools(state: ToolsState):
    tool_messages = []
    
    for tool_call in state["tool_calls"]:
        result = execute_tool_call(tool_call)
        
        if result is None:
            result = { "error": "The tool request could not be executed."}
            
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })
    
    return {
        "messages": state["messages"] + tool_messages,
        "tool_calls": []
    }
    
    
def write_answer(state: ToolsState):
    response = client.chat.completions.create(
        model = "gemma-4-e4b-it",
        messages = state["messages"]
    )
    
    message = response.choices[0].message
    
    return {
        "messages": state["messages"] + [
            message.model_dump(exclude_none = True)
        ]
    }
    
def route_after_model(state: ToolsState):
    if state["tool_calls"]:
        return "tools"
    
    return "done"


def build_tool_graph():
    builder = StateGraph(ToolsState)
    
    builder.add_node("ask_model", ask_model)
    builder.add_node("run_tools", run_tools)
    builder.add_node("write_answer", write_answer)
    
    builder.add_edge(START, "ask_model")
    
    builder.add_conditional_edges(
        "ask_model",
        route_after_model,
        {
            "tools": "run_tools",
            "done": END
        }
    )
    
    builder.add_edge("run_tools", "write_answer")
    builder.add_edge("write_answer", END)
    
    return builder.compile()

def main():
    graph = build_tool_graph()
    
    result = graph.invoke({
        "messages": [
            {
                "role": "system",
                "content": (
                    "Use the lookup tool for policy information."
                    "Base your answer on the returned record. "
                    "If no recored is found, say so. "
                    "Do not infer claim coverage or approval"    
                ),
            },
            {
                "role": "user",
                "content": "Look up the policy record for POL-123"
            }
        ],
        "tool_calls": []
    })
    
    print(result["messages"][-1]["content"])
    
if __name__ == "__main__":
    main()
    
    
