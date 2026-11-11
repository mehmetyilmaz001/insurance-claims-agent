"""A bounded model/tool loop for policy lookup."""

import json
from operator import add
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from openai import OpenAI

from .config import Settings
from .tools import POLICY_TOOL, execute_tool_call


class ToolsState(TypedDict):
    messages: Annotated[list[dict], add]
    tool_calls: list[dict]
    tool_rounds: int


def build_tool_graph(*, settings: Settings | None = None, client=None, checkpointer=None):
    settings = settings or Settings.from_env()
    client = client or OpenAI(
        base_url=settings.model_url, api_key="lm-studio", max_retries=0
    )

    def ask_model(state: ToolsState) -> dict:
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=state["messages"],
            tools=[POLICY_TOOL],
        )
        message = response.choices[0].message
        return {
            "messages": [message.model_dump(exclude_none=True)],
            "tool_calls": [
                call.model_dump(exclude_none=True)
                for call in (message.tool_calls or [])
            ],
        }

    def run_tools(state: ToolsState) -> dict:
        tool_messages = []
        for call in state["tool_calls"]:
            tool_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(execute_tool_call(call)),
                }
            )
        return {
            "messages": tool_messages,
            "tool_calls": [],
            "tool_rounds": state["tool_rounds"] + 1,
        }

    def write_answer(state: ToolsState) -> dict:
        response = client.chat.completions.create(
            model=settings.model_name, messages=state["messages"]
        )
        return {"messages": [response.choices[0].message.model_dump(exclude_none=True)]}

    def route_after_model(state: ToolsState) -> str:
        return "tools" if state["tool_calls"] else "done"

    def route_after_tools(state: ToolsState) -> str:
        return "finish" if state["tool_rounds"] >= 2 else "continue"

    builder = StateGraph(ToolsState)
    builder.add_node("ask_model", ask_model)
    builder.add_node("run_tools", run_tools)
    builder.add_node("write_answer", write_answer)
    builder.add_edge(START, "ask_model")
    builder.add_conditional_edges(
        "ask_model", route_after_model, {"tools": "run_tools", "done": END}
    )
    builder.add_conditional_edges(
        "run_tools", route_after_tools, {"continue": "ask_model", "finish": "write_answer"}
    )
    builder.add_edge("write_answer", END)
    return builder.compile(checkpointer=checkpointer or InMemorySaver())
