from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from review_pause import CLAIM_ID, build_review_graph


def main():
    config = {
        "configurable": {
            "thread_id": f"review-demo-{CLAIM_ID}",
        }
    }

    with SqliteSaver.from_conn_string("review.sqlite") as checkpointer:
        graph = build_review_graph(checkpointer)

        snapshot = graph.get_state(config)

        if not snapshot.next:
            print("No paused review found for this claim.")
            return

        answer = input("Proceed to human review? yes/no: ").strip().lower()

        if answer not in {"yes", "no"}:
            print("Please enter yes or no.")
            return

        result = graph.invoke(
            Command(resume=answer),
            config=config,
        )

        print("Claim:", result["claim_id"])
        print("Review decision:", result["review_decision"])
        print("Outcome:", result["review_outcome"])


if __name__ == "__main__":
    main()
