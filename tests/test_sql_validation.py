"""
Verifies SQL validation node: feeds it deliberately bad
SQL and confirms each is blocked with a sensible error, then confirms a
real, valid query passes cleanly.

Usage:
    python -m tests.test_sql_validation
"""

from agent.nodes.validate_sql import validate_sql

BAD_CASES = [
    ("DELETE statement", "DELETE FROM public.f1_results WHERE year = 2023;"),
    ("UPDATE statement", "UPDATE public.constructors SET constructors = 'x' WHERE id = 1;"),
    ("DROP statement", "DROP TABLE public.f1_results;"),
    ("Stacked statements", "SELECT * FROM public.constructors; DROP TABLE public.f1_results;"),
    ("Write hidden in CTE", "WITH x AS (DELETE FROM public.f1_results RETURNING *) SELECT * FROM x;"),
    ("Empty SQL", ""),
]

GOOD_CASE = (
    "SELECT c.constructors AS constructor, SUM(fr.points) AS total_points "
    "FROM public.f1_results fr "
    "JOIN public.constructors c ON fr.team_id = c.id "
    "GROUP BY c.id, c.constructors "
    "ORDER BY total_points DESC;"
)


def main():
    print("--- Testing cases that should be BLOCKED ---\n")
    for label, sql in BAD_CASES:
        result = validate_sql({"generated_sql": sql})
        error = result.get("last_error")
        assert error, f"FAILED: '{label}' was not blocked — expected an error, got none."
        print(f"  OK — '{label}' correctly blocked.")
        print(f"       Reason: {error}\n")

    print("--- Testing a case that should PASS ---\n")
    result = validate_sql({"generated_sql": GOOD_CASE})
    error = result.get("last_error")
    assert error is None, f"FAILED: valid SELECT was incorrectly blocked. Reason: {error}"
    print("  OK — valid SELECT query passed validation cleanly.")

    print("\nAll checks passed. Sub-problem 5 (validation) is working correctly.")


if __name__ == "__main__":
    main()