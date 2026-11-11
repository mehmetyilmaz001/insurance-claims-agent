from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from try_model import build_intake_graph


def main():
    config = {
        "configurable": {
            "thread_id": "intake-demo-CLM-008",
        }
    }

    with SqliteSaver.from_conn_string("intake.sqlite") as checkpointer:
        graph = build_intake_graph(checkpointer)
        snapshot = graph.get_state(config)

        if "pause_for_review" not in snapshot.next:
            print("No paused review found for CLM-008.")
            return

        answer = input("Proceed to human review? yes/no: ").strip().lower()

        if answer not in {"yes", "no"}:
            print("Please enter yes or no.")
            return
        
        reason = input("Reason: ").strip()

        if not reason:
            print("Please provide a reason.")
            return
        
        result = graph.invoke(
            Command(resume={
                "decision": answer,
                "reason": reason,
            }),
            config=config,
        )

        print("Claim:", result["claim_id"])
        print("Decision:", result["review_decision"])
        print("Status:", result["status"])
        print("Reason:", result["review_reason"])


if __name__ == "__main__":
    main()
