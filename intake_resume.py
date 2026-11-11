from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from try_model import build_intake_graph


def main():
    config = {
        "configurable": {
            "thread_id": "intake-demo-CLM-006",
        }
    }

    with SqliteSaver.from_conn_string("intake.sqlite") as checkpointer:
        graph = build_intake_graph(checkpointer)
        snapshot = graph.get_state(config)

        if "pause_for_review" not in snapshot.next:
            print("No paused review found for CLM-006.")
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
        print("Decision:", result["review_decision"])
        print("Status:", result["status"])


if __name__ == "__main__":
    main()
