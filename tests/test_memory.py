"""
Verifies memory read/write nodes: simulates two turns in
the same session. After writing turn 1, a fresh memory_read for the same
session should see it. Uses a throwaway test session ID so it doesn't
pollute real session data.

Usage:
    python -m tests.test_memory
"""

import redis

from agent.nodes.memory_read import memory_read
from agent.nodes.memory_write import memory_write
from memory.memory_schema import history_key
from memory.redis_client import RedisMemoryClient

TEST_SESSION_ID = "test-session-sub7-verification"


def cleanup():
    """Remove test data so repeated runs start clean."""
    client = RedisMemoryClient()
    try:
        client._client.delete(history_key(TEST_SESSION_ID))
    except redis.RedisError:
        pass


def main():
    cleanup()

    print("--- Turn 1: no prior history expected ---\n")
    state_turn1 = {"session_id": TEST_SESSION_ID}
    result = memory_read(state_turn1)
    assert result["conversation_history"] == [], "Expected empty history before any writes."
    print("  OK — history is empty, as expected for a new session.")

    print("\n--- Writing turn 1 ---\n")
    completed_turn1 = {
        "session_id": TEST_SESSION_ID,
        "question": "How many total points did each constructor score?",
        "final_sql": "SELECT c.constructors, SUM(fr.points) FROM public.f1_results fr "
                     "JOIN public.constructors c ON fr.team_id = c.id GROUP BY c.constructors;",
        "final_answer": "Here are the total points per constructor.",
        "execution_succeeded": True,
    }
    memory_write(completed_turn1)
    print("  OK — turn 1 written.")

    print("\n--- Turn 2: should now see turn 1 in history ---\n")
    state_turn2 = {"session_id": TEST_SESSION_ID}
    result = memory_read(state_turn2)
    history = result["conversation_history"]

    assert len(history) == 1, f"Expected 1 prior turn, found {len(history)}."
    assert history[0]["question"] == completed_turn1["question"], "Stored question doesn't match what was written."
    assert history[0]["succeeded"] is True, "Stored success flag doesn't match."
    print("  OK — turn 2 can see turn 1's question and outcome in history.")
    print(f"  Retrieved record: {history[0]}")

    cleanup()
    print("\nAll checks passed. Sub-problem 7 (memory) is working correctly.")
    print("(Test session data cleaned up from Redis.)")


if __name__ == "__main__":
    main()