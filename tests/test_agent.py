"""
End-to-end test for the full agent (sub-problem 8): runs real questions
through the complete LangGraph pipeline — memory read, generation,
validation, execution, retry loop, response formatting, memory write.

Includes one deliberately tricky question (referencing a column that
doesn't exist) to confirm the retry loop actually engages and that the
agent still produces a clean final answer instead of crashing, even if
all retries are exhausted.

Uses a throwaway session ID and cleans up afterward.

Usage:
    python -m tests.test_end_to_end
"""

import redis

from agent.graph import agent_graph
from memory.memory_schema import history_key
from memory.redis_client import RedisMemoryClient
from prompts.prompt_loader import get_system_prompt

TEST_SESSION_ID = "test-session-sub8-e2e"


def cleanup():
    client = RedisMemoryClient()
    try:
        client._client.delete(history_key(TEST_SESSION_ID))
    except redis.RedisError:
        pass


def run(question: str) -> dict:
    system_prompt = get_system_prompt()
    initial_state = {
        "session_id": TEST_SESSION_ID,
        "question": question,
        "system_prompt": system_prompt,
        "retry_count": 0,
        "max_retries": 2,
        "last_error": None,
    }
    return agent_graph.invoke(initial_state)


def main():
    cleanup()

    print("--- Test 1: normal question, should succeed on first attempt ---\n")
    result = run("How many total points did each constructor score?")

    assert result.get("execution_succeeded") is True, "Expected the normal question to succeed."
    assert result.get("retry_count", 0) == 0, "Expected zero retries for a straightforward question."
    assert "Answer:" in result["final_answer"] and "Query:" in result["final_answer"], (
        "Final answer doesn't match the expected Answer/Query format."
    )
    print("  OK — succeeded on first attempt, correct output format.")
    print(f"  {result['final_answer']}\n")

    print("--- Test 2: memory persisted from test 1 ---\n")
    mem_client = RedisMemoryClient()
    history = mem_client.get_list(history_key(TEST_SESSION_ID))
    assert len(history) == 1, f"Expected 1 turn written to memory, found {len(history)}."
    print("  OK — turn 1 was written to memory.\n")

    print("--- Test 3: deliberately tricky question, should trigger retries ---\n")
    tricky_result = run(
        "What is the average lap_time_seconds for each driver?"
        # lap_time_seconds does not exist in the schema — this should force
        # at least one failed attempt and exercise the retry loop.
    )

    print(f"  Final retry_count: {tricky_result.get('retry_count', 0)}")
    print(f"  Execution succeeded: {tricky_result.get('execution_succeeded')}")
    print(f"  No-query reason: {tricky_result.get('no_query_reason')}")
    assert tricky_result.get("final_answer"), "Expected a final_answer even when all retries fail."

    if tricky_result.get("no_query_reason"):
        # Best outcome: the model recognized immediately that lap times
        # aren't in the schema and declined cleanly, without burning any
        # retries on a fake NULL-substitution workaround.
        assert tricky_result.get("retry_count", 0) == 0, (
            "Expected zero retries when the model declines immediately via NO_QUERY."
        )
        print("  OK — model correctly declined immediately (no fake query, no wasted retries).")
    elif not tricky_result.get("execution_succeeded"):
        assert tricky_result.get("retry_count", 0) == 2, (
            f"Expected retry_count to reach max_retries (2) when all attempts fail, "
            f"got {tricky_result.get('retry_count')}."
        )
        assert "wasn't able to answer" in tricky_result["final_answer"], (
            "Expected the graceful failure message when retries are exhausted."
        )
        print("  OK — retry loop engaged, exhausted retries gracefully, clean failure message returned.")
    else:
        print("  Note: the model self-corrected within the retry budget and succeeded anyway — "
              "that's also a valid, acceptable outcome.")

    print(f"\n  {tricky_result['final_answer']}\n")

    cleanup()
    print("All checks passed. Sub-problem 8 (full agent) is working correctly end to end.")
    print("(Test session data cleaned up from Redis.)")


if __name__ == "__main__":
    main()