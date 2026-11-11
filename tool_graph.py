import json
from operator import add
from typing import Annotated, TypedDict

from langgraph.graph import START, END, StateGraph
from langgraph.checkpoint.memory import InMemorySaver
from openai.types.chat import ChatCompletionMessageToolCall
from openai import OpenAI

from try_tools import POLICY_TOOL, execute_tool_call

client = OpenAI(
    base_url = "http://127.0.0.1:1234/v1",
    api_key="lm-studio",
    max_retries=0
)

class ToolsState(TypedDict):
    messages: Annotated[list[dict], add]
    tool_calls: list[dict]
    tool_rounds: int
    
    
def ask_model(state: ToolsState):
    response = client.chat.completions.create(
        model = "gemma-4-e4b-it",
        messages = state["messages"],
        tools=[POLICY_TOOL]
    )
    
    message = response.choices[0].message
    
    return {
        "messages": [
            message.model_dump(exclude_none=True)
        ],
        "tool_calls": [
            call.model_dump(exclude_none=True)
            for call in (message.tool_calls or [])
        ],
    }
    
def run_tools(state: ToolsState):
    tool_messages = []
    
    for tool_call_data in state["tool_calls"]:
        tool_call = ChatCompletionMessageToolCall.model_validate(tool_call_data)
        result = execute_tool_call(tool_call)
        
        if result is None:
            result = { "error": "The tool request could not be executed."}
            
        tool_messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result)
        })
    
    return {
        "messages": tool_messages,
        "tool_calls": [],
        "tool_rounds": state["tool_rounds"] + 1
    }
    
    
def write_answer(state: ToolsState):
    response = client.chat.completions.create(
        model = "gemma-4-e4b-it",
        messages = state["messages"]
    )
    
    message = response.choices[0].message
    
    return {
        "messages": [
            message.model_dump(exclude_none = True)
        ]
    }
    
def route_after_model(state: ToolsState):
    if state["tool_calls"]:
        return "tools"
    
    return "done"

def route_after_tools(state: ToolsState):
    if state["tool_rounds"] >= 2:
        return "finish"
    
    return "continue"

def build_tool_graph(checkpointer=None):
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
    
    builder.add_conditional_edges(
        "run_tools",
        route_after_tools,
        {
            "continue": "ask_model",
            "finish": "write_answer"
        }
    )
    builder.add_edge("write_answer", END)
    
    return builder.compile(
        checkpointer=checkpointer or InMemorySaver()
    )

def main():
    graph = build_tool_graph()
    
    config = {
        "configurable": {
            "thread_id": "claim-demo-1",
        }
    }
    
    first_result = graph.invoke({
        "messages": [
            {
                "role": "system",
                "content": (
                    "Use the lookup tool for policy information."
                    "Base your answer on the returned record. "
                    "Do not infer claim coverage or approval"    
                ),
            },
            {
                "role": "user",
                "content": (
                        "My preferred contact method is email. "
                        "Look up POL-123."
                ),
            }
        ],
        "tool_calls": [],
        "tool_rounds": 0
    },
    config=config
    )
    
    print("First answer:")
    print(first_result["messages"][-1]["content"])
    
    second_result = graph.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "What contact method did I say I prefer?",
                }
            ],
            "tool_calls": [],
            "tool_rounds": 0,
        },
        config=config,
    )

    print("Follow-up answer:")
    print(second_result["messages"][-1]["content"])
    
if __name__ == "__main__":
    main()
    
    
