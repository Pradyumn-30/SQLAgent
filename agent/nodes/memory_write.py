"""
Memory write node.

Runs AFTER a turn completes — either successfully, or after the final
retry has been exhausted (sub-problem 8 decides when "completed" means).
Appends the turn to this session's history in Redis.

If Redis is unreachable, the turn's
answer still gets returned to the user — we just lose persistence for
that one turn rather than failing the whole response.
"""

import redis

from agent.state import AgentState
from memory.memory_schema import build_turn_record, history_key
from memory.redis_client import RedisMemoryClient

_memory_client = RedisMemoryClient()


def memory_write(state: AgentState) -> AgentState:
    """
    LangGraph node function. Builds a turn record from the final state
    and appends it to Redis. Returns an empty dict as this node doesn't
    need to modify AgentState.
    """
    session_id = state.get("session_id")

    if not session_id:
        # Nothing to key the write against — skip silently.
        return {}

    record = build_turn_record(state)

    try:
        _memory_client.append_to_list(history_key(session_id), record)
    except redis.RedisError:
        pass

    return {}