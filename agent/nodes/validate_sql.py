"""
SQL validation node.

Runs BEFORE execution. Enforces read-only at the
application level on top of the DB-role-level.

Checks, in order:
    1. Exactly one SQL statement (blocks stacked/multi-statement injection).
    2. The statement is a SELECT (or a WITH ... SELECT / CTE).
    3. No disallowed keywords appear anywhere in the statement (covers
       write/DDL/admin operations, and defends against a write hidden
       inside a subquery or CTE).

Returns a dict to merge into AgentState: on failure, sets `last_error`
(same field execution failures use) so the retry loop 
can treat validation failures and execution failures identically.
"""

import sqlparse
from sqlparse.sql import Statement

from agent.state import AgentState

# Keywords that should never appear in a query this agent runs, regardless
# of where in the statement they appear (top-level, subquery, or CTE).
DISALLOWED_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "GRANT", "REVOKE", "CREATE", "REPLACE", "MERGE", "CALL",
    "EXECUTE", "COPY", "VACUUM", "SET", "RESET", "LISTEN",
    "NOTIFY", "LOCK", "DO", "COMMENT",
}

def _get_statement_keyword(stmt: Statement) -> str:
    """Returns the first meaningful keyword of a statement, e.g. SELECT, WITH"""
    for token in stmt.tokens:
        if token.is_whitespace:
            continue
        return token.value.upper()
    return ""

def _contains_disallowed_keyword(sql: str) -> str:
    """Returns the first disallowed keyword found anywhere in the SQL, or '' if none."""
    parsed = sqlparse.parse(sql)[0]
    for token in parsed.flatten():
        # sqlparse classifies DELETE/INSERT/UPDATE as Keyword.DML and
        # DROP/CREATE/ALTER as Keyword.DDL — both are subtypes of Keyword.
        if token.ttype in sqlparse.tokens.Keyword:
            if token.value.upper() in DISALLOWED_KEYWORDS:
                return token.value.upper()
    return ""


def validate_sql(state: AgentState) -> AgentState:
    """
    LangGraph node function. Reads state["generated_sql"], validates it,
    and returns fields to merge back into state.
    """
    sql = (state.get("generated_sql") or "").strip()

    if not sql:
        return {"execution_succeeded": False, "last_error": "No SQL was generated to validate."}

    statements = [s for s in sqlparse.parse(sql) if s.value.strip()]

    if len(statements) == 0:
        return {"execution_succeeded": False, "last_error": "Generated SQL was empty after parsing."}

    if len(statements) > 1:
        return {
            "execution_succeeded": False,
            "last_error": (
                "Generated SQL contains multiple statements, which is not allowed. "
                "Return exactly one SELECT statement."
            ),
        }

    stmt = statements[0]
    leading_keyword = _get_statement_keyword(stmt)

    if leading_keyword not in ("SELECT", "WITH"):
        return {
            "execution_succeeded": False,
            "last_error": (
                f"Generated statement starts with '{leading_keyword}', but only SELECT "
                f"(or WITH ... SELECT) statements are allowed. This agent is read-only."
            ),
        }

    bad_keyword = _contains_disallowed_keyword(sql)
    if bad_keyword:
        return {
            "execution_succeeded": False,
            "last_error": (
                f"Generated SQL contains a disallowed keyword: '{bad_keyword}'. "
                f"This agent is strictly read-only — only SELECT is permitted."
            ),
        }

    # Passed all checks — no error, nothing to merge except an implicit "ok".
    # We don't set execution_succeeded=True here as even if the SQL is syntactically correct
    # and validates fine, it may fail during execution (e.g. unknown columns, type mismatches,
    # division by zero, runtime permissions, etc.). That's what the execution node and its
    # retry loop are there to handle.
    return {"last_error": None}