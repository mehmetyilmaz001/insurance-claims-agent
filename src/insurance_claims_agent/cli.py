"""One command for intake, review, and live evaluation."""

import argparse
import json
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from pydantic import ValidationError

from .config import Settings
from .evaluation import run_live_evaluation
from .evaluation_cases import CASES
from .intake_graph import ReviewResponse, build_intake_graph, make_initial_state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fictional insurance claim agent")
    sub = parser.add_subparsers(dest="command", required=True)
    intake = sub.add_parser("intake", help="Start a claim")
    intake.add_argument("--claim-id", required=True)
    source = intake.add_mutually_exclusive_group(required=True)
    source.add_argument("--description", help="Free-text incident description")
    source.add_argument("--case", choices=[case["name"] for case in CASES])
    intake.add_argument("--db", type=Path)

    resume = sub.add_parser("resume", help="Record a human review response")
    resume.add_argument("--claim-id", required=True)
    resume.add_argument("--decision", choices=("yes", "no"))
    resume.add_argument("--reason")
    resume.add_argument("--db", type=Path)

    evaluation = sub.add_parser("eval", help="Run live LM Studio checks")
    evaluation.add_argument(
        "--case", action="append", choices=[case["name"] for case in CASES]
    )
    return parser


def _database(args) -> Path:
    database = args.db or Settings.from_env().database
    database.parent.mkdir(parents=True, exist_ok=True)
    return database


def _config(claim_id: str) -> dict:
    return {"configurable": {"thread_id": f"claim-{claim_id}"}}


def _print_result(result: dict) -> None:
    print("Claim:", result["claim_id"])
    print("Status:", result["status"])
    print("Message:", result["message"])
    if result.get("__interrupt__"):
        print("Human review request:")
        print(json.dumps(result["__interrupt__"][0].value, indent=2))
    if result.get("review_decision"):
        print("Decision:", result["review_decision"])
        print("Reason:", result["review_reason"])


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "eval":
        return 0 if run_live_evaluation(args.case) else 1

    config = _config(args.claim_id)
    with SqliteSaver.from_conn_string(str(_database(args))) as checkpointer:
        graph = build_intake_graph(checkpointer)
        snapshot = graph.get_state(config)

        if args.command == "intake":
            if snapshot.values:
                print(f"Claim {args.claim_id} already exists. Use a new ID or resume it.")
                return 1
            description = args.description
            if args.case:
                description = next(
                    case["description"] for case in CASES if case["name"] == args.case
                )
            result = graph.invoke(
                make_initial_state(args.claim_id, description), config=config
            )
        else:
            if "pause_for_review" not in snapshot.next:
                print(f"No paused review found for {args.claim_id}.")
                return 1
            decision = args.decision or input("Proceed to human review? yes/no: ").strip()
            reason = args.reason if args.reason is not None else input("Reason: ")
            try:
                response = ReviewResponse.model_validate(
                    {"decision": decision, "reason": reason}
                )
            except ValidationError:
                print("Enter yes or no and a nonblank reason.")
                return 1
            result = graph.invoke(
                Command(resume=response.model_dump()), config=config
            )

        _print_result(result)
    return 0
