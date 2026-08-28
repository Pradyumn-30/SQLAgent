"""
Defines what gets stored in Redis for persistent memory, and the key
naming convention. 
Kept separate from the memory read/write node logic
so the "shape" of memory is documented and reusable in one place.

Redis key conventions:
    session:{session_id}:history      -> a Redis LIST of turn records (JSON strings)
    session:{session_id}:preferences  -> a Redis JSON object (hash-like dict)

Schema knowledge is NOT stored here — it's injected
statically into the system prompt. Memory covers only conversation history and 
user preferences.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Optional

from agent.state import AgentState


def history_key(session_id: str) -> str:
    return f"session:{session_id}:history"


def preferences_key(session_id: str) -> str:
    return f"session:{session_id}:preferences"


@dataclass
class TurnRecord:
    """One completed turn, as stored in the history list."""
    question: str
    sql: Optional[str]
    answer: Optional[str]
    succeeded: bool
    timestamp: str  # ISO 8601 UTC


def build_turn_record(state: AgentState) -> dict:
    """
    Builds the record to persist for a completed turn (success or final
    failure), from the current AgentState. Called by the memory-write
    node after a turn finishes.
    """
    record = TurnRecord(
        question=state.get("question", ""),
        sql=state.get("final_sql") or state.get("generated_sql"),
        answer=state.get("final_answer"),
        succeeded=bool(state.get("execution_succeeded", False)),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    return asdict(record)