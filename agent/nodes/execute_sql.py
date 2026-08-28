"""
SQL execution node.

Runs AFTER validation passes. Executes the query via
Postgres Client and converts any database error
into `last_error` — the same field validation failures use — so the
retry loop can treat "invalid SQL" and "execution failed"
identically: feed the error back into generate_sql and try again.

Does NOT retry internally. Retry counting and the max-2-retries cap live
in the agent state, not here — this node's only job is
to attempt the query once and report what happened.
"""

import psycopg2

from agent.state import AgentState
from db.postgres_client import PostgresReadOnlyClient

_pg_client = PostgresReadOnlyClient()


def execute_sql(state: AgentState) -> AgentState:
    """
    LangGraph node function. Reads state["generated_sql"], executes it,
    and returns fields to merge back into state.
    """
    sql = state.get("generated_sql")

    if not sql:
        return {
            "execution_succeeded": False,
            "last_error": "No SQL available to execute.",
        }

    try:
        result = _pg_client.execute_query(sql)
    except psycopg2.Error as e:
        error_message = str(e).strip()
        return {
            "execution_succeeded": False,
            "last_error": error_message,
        }

    return {
        "execution_succeeded": True,
        "query_columns": result.columns,
        "query_rows": result.rows,
        "final_sql": sql,
        "last_error": None,
    }