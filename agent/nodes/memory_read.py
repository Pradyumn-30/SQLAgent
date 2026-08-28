"""
Memory read node.

Runs BEFORE generate_sql in the graph. Loads prior turns
for this session from Redis and puts them into state["conversation_history"],
so generate_sql can use them to resolve follow-up questions
(e.g. "what about last year?" referring back to a prior question).

If Redis is unreachable or the session has no history yet, this returns an empty history
rather than blocking the turn. 
Memory is a helpful enhancement here, not a hard dependency for the agent to function.
"""

import redis

from agent.state import AgentState
from memory.memory_schema import history_key
from memory.redis_client import RedisMemoryClient

_memory_client = RedisMemoryClient()

# How many prior turns to load into context. Keeps the prompt from
# growing unbounded as a session gets long.
MAX_HISTORY_TURNS = 5


def memory_read(state: AgentState) -> AgentState:
    """
    LangGraph node function. Reads state["session_id"], loads history
    from Redis, and returns fields to merge back into state.
    """
    session_id = state.get("session_id")

    if not session_id:
        # No session scoping provided — proceed with empty history
        return {"conversation_history": []}

    try:
        full_history = _memory_client.get_list(history_key(session_id))
    except redis.RedisError:
        return {"conversation_history": []}

    recent_history = full_history[-MAX_HISTORY_TURNS:] if full_history else []
    return {"conversation_history": recent_history}