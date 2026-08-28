"""
Verifies SQL execution node: runs a real, valid query
against the real database and confirms rows come back, then runs a
deliberately broken query and confirms it fails cleanly (via last_error)
instead of raising an uncaught exception.

Usage:
    python -m tests.test_sql_execution
"""

from agent.nodes.execute_sql import execute_sql

GOOD_SQL = (
    "SELECT c.constructors AS constructor, SUM(fr.points) AS total_points "
    "FROM public.f1_results fr "
    "JOIN public.constructors c ON fr.team_id = c.id "
    "GROUP BY c.id, c.constructors "
    "ORDER BY total_points DESC "
    "LIMIT 10;"
)

BROKEN_SQL = "SELECT * FROM public.this_table_does_not_exist;"


def main():
    print("--- Testing a valid query against the real database ---\n")
    result = execute_sql({"generated_sql": GOOD_SQL})

    assert result["execution_succeeded"] is True, (
        f"Expected success, got failure. Error: {result.get('last_error')}"
    )
    assert result["query_rows"], "Query succeeded but returned zero rows — check your data."
    print(f"  OK — query succeeded, {len(result['query_rows'])} row(s) returned.")
    print(f"  Columns: {result['query_columns']}")
    print("  First row:", result["query_rows"][0])

    print("\n--- Testing a broken query (should fail cleanly) ---\n")
    result = execute_sql({"generated_sql": BROKEN_SQL})

    assert result["execution_succeeded"] is False, "Expected failure for a query against a nonexistent table."
    assert result.get("last_error"), "Expected an error message, got none."
    print(f"  OK — failed cleanly as expected.")
    print(f"  Error message: {result['last_error']}")

    print("\nAll checks passed. Sub-problem 6 (execution) is working correctly.")


if __name__ == "__main__":
    main()