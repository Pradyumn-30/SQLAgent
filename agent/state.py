"""
Shared state schema for the LangGraph agent.

Every node (generate_sql, validate_sql, execute_sql, format_response, ...)
reads from and writes to this same state dict as it flows through the
graph.

Fields are all optional at the type level (via Optional) because the
state starts mostly empty and gets filled in as it moves through nodes —
e.g. `generated_sql` doesn't exist yet before the generate_sql node runs.
"""

from typing import List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # --- Input ---
    session_id: str
    question: str

    # --- Static context (loaded once, doesn't change per-turn) ---
    system_prompt: str

    # --- Memory context (filled in by the memory-read node) ---
    conversation_history: List[dict]

    # --- SQL generation / retry loop ---
    generated_sql: Optional[str]
    retry_count: int          # starts at 0, incremented on each failed attempt
    max_retries: int          # hard cap
    last_error: Optional[str]  # error message fed back into generation on retry

    # --- Execution results ---
    query_columns: Optional[List[str]]
    query_rows: Optional[List[dict]]
    execution_succeeded: bool

    # --- Final output ---
    final_answer: Optional[str]
    final_sql: Optional[str]   # the SQL that actually succeeded (or last attempt, if all failed)