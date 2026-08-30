"""
CLI entry point-

Usage:
    # One-off question
    python main.py --session my-session "How many total points did each constructor score?"

    # Interactive mode (keeps asking, same session, until you type 'exit')
    python main.py --session my-session
"""

import argparse

from agent.graph import agent_graph
from prompts.prompt_loader import get_system_prompt


def run_turn(question: str, session_id: str) -> str:
    system_prompt = get_system_prompt()

    initial_state = {
        "session_id": session_id,
        "question": question,
        "system_prompt": system_prompt,
        "retry_count": 0,
        "max_retries": 2,
        "last_error": None,
    }

    result = agent_graph.invoke(initial_state)
    return result.get("final_answer", "(No answer produced.)")


def main():
    parser = argparse.ArgumentParser(description="Postgres Query Agent — Phase 1")
    parser.add_argument("question", nargs="?", help="The question to ask. Omit for interactive mode.")
    parser.add_argument("--session", default="default-session", help="Session ID for memory scoping.")
    args = parser.parse_args()

    if args.question:
        print(run_turn(args.question, args.session))
        return

    print(f"Interactive mode. Session: '{args.session}'. Type 'exit' to quit.\n")
    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue
        print("\n" + run_turn(question, args.session) + "\n")


if __name__ == "__main__":
    main()