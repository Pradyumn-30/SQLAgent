"""
Shared state schema for the LangGraph agent.

Every node (generate_sql, validate_sql, execute_sql, format_response, ...)
reads from and writes to this same state dict as it flows through the
graph. Defining it once here, up front, means every later node just plugs
into an already-agreed shape.

Fields are all optional at the type level (via `| None`) because the
state starts mostly empty and gets filled in as it moves through nodes
"""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    # --- Input ---
    session_id: str
    question: str

    # --- Static context (loaded once, doesn't change per-turn) ---
    system_prompt: str

    # --- Memory context (filled in by the memory-read node, sub-problem 7) ---
    conversation_history: list[dict]

    # --- SQL generation / retry loop ---
    generated_sql: str | None
    no_query_reason: str | None
    # set instead of generated_sql when the model declines (see generate_sql.py)
    retry_count: int  # starts at 0, incremented on each failed attempt
    max_retries: int  # hard cap — 2, per the Phase 1 spec
    last_error: str | None  # error message fed back into generation on retry

    # --- Execution results ---
    query_columns: list[str] | None
    query_rows: list[dict] | None
    execution_succeeded: bool

    # --- Final output ---
    final_answer: str | None
    final_sql: str | None
    # the SQL that actually succeeded (or last attempt, if all failed)
