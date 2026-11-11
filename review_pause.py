from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class ReviewState(TypedDict):
    claim_id: str
    review_decision: str | None


def review_claim(state: ReviewState):
    decision = interrupt({
        "claim_id": state["claim_id"],
        "question": "Should this fictional claim proceed to human review?",
    })

    return {"review_decision": decision}


def build_review_graph(checkpointer):
    builder = StateGraph(ReviewState)
    builder.add_node("review_claim", review_claim)
    builder.add_edge(START, "review_claim")
    builder.add_edge("review_claim", END)
    return builder.compile(checkpointer=checkpointer)


def main():
    config = {
        "configurable": {
            "thread_id": "review-demo-CLM-001",
        }
    }

    with SqliteSaver.from_conn_string("review.sqlite") as checkpointer:
        graph = build_review_graph(checkpointer)

        result = graph.invoke(
            {
                "claim_id": "CLM-001",
                "review_decision": None,
            },
            config=config,
        )

        print("Review request:")
        print(result["__interrupt__"][0].value)


if __name__ == "__main__":
    main()