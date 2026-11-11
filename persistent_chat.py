from langgraph.checkpoint.sqlite import SqliteSaver

from tool_graph import build_tool_graph


def main():
    question = input("You: ")

    config = {
        "configurable": {
            "thread_id": "claim-demo-sqlite",
        }
    }

    with SqliteSaver.from_conn_string("claims.sqlite") as checkpointer:
        graph = build_tool_graph(checkpointer)
        snapshot = graph.get_state(config)

        new_messages = [{"role": "user", "content": question}]

        if not snapshot.values:
            new_messages.insert(0, {
                "role": "system",
                "content": (
                    "Use the lookup tool for policy records. "
                    "Base policy answers on returned records. "
                    "Do not infer claim coverage or approval."
                ),
            })

        result = graph.invoke(
            {
                "messages": new_messages,
                "tool_calls": [],
                "tool_rounds": 0,
            },
            config=config,
        )

        print("Gemma:", result["messages"][-1]["content"])


if __name__ == "__main__":
    main()