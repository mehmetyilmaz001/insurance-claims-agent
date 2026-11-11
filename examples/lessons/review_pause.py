from typing import TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

CLAIM_ID = "CLM-003"


class ReviewState(TypedDict):
    claim_id: str
    review_decision: str | None
    review_outcome: str


def review_claim(state: ReviewState):
    decision = interrupt({
        "claim_id": state["claim_id"],
        "question": "Should this fictional claim proceed to human review?",
    })

    return {"review_decision": decision}

def route_review(state: ReviewState):
    if state["review_decision"] == "yes":
        return "proceed"

    return "hold"


def proceed_to_review(state: ReviewState):
    return {"review_outcome": "proceed_to_review"}


def hold_claim(state: ReviewState):
    return {"review_outcome": "on_hold"}

def build_review_graph(checkpointer):
    builder = StateGraph(ReviewState)

    builder.add_node("review_claim", review_claim)
    builder.add_node("proceed_to_review", proceed_to_review)
    builder.add_node("hold_claim", hold_claim)

    builder.add_edge(START, "review_claim")

    builder.add_conditional_edges(
        "review_claim",
        route_review,
        {
            "proceed": "proceed_to_review",
            "hold": "hold_claim",
        },
    )

    builder.add_edge("proceed_to_review", END)
    builder.add_edge("hold_claim", END)

    return builder.compile(checkpointer=checkpointer)


def main():
    config = {
        "configurable": {
            "thread_id": f"review-demo-{CLAIM_ID}",
        }
    }

    with SqliteSaver.from_conn_string("review.sqlite") as checkpointer:
        graph = build_review_graph(checkpointer)

        result = graph.invoke(
            {
                "claim_id": CLAIM_ID,
                "review_decision": None,
                "review_outcome": "pending",
            },
            config=config,
        )

        print("Review request:")
        print(result["__interrupt__"][0].value)


if __name__ == "__main__":
    main()
