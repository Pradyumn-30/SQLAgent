"""
Schema generator works end-to-end against your
real database: introspects the schema, formats it, and sanity-checks the results.

Usage:
    python -m tests.test_schema_generation
"""

from db.postgres_client import PostgresReadOnlyClient
from db.schema_formatter import format_schema_as_markdown
from db.schema_introspector import introspect_schema
from db.schema_scope import DEFAULT_SCOPE


def main():
    print(f"Scope: schemas={DEFAULT_SCOPE.schema_allowlist}, "
          f"table_allowlist={DEFAULT_SCOPE.table_allowlist or '(all)'}, "
          f"table_denylist={DEFAULT_SCOPE.table_denylist or '(none)'}")

    print("\nIntrospecting schema...")
    pg_client = PostgresReadOnlyClient()
    tables = introspect_schema(pg_client, DEFAULT_SCOPE)

    assert len(tables) > 0, (
        "No tables found. Check: (1) DEFAULT_SCOPE in db/schema_scope.py "
        "matches your actual schema name, (2) your database actually has "
        "tables in it, (3) the readonly_agent_user role has SELECT grants."
    )
    print(f"  OK — found {len(tables)} table(s):")
    for t in tables:
        print(f"    - {t.schema}.{t.name} ({len(t.columns)} column(s))")
        assert len(t.columns) > 0, f"Table {t.schema}.{t.name} has zero columns — unexpected."

    print("\nFormatting as markdown...")
    markdown = format_schema_as_markdown(tables)
    assert markdown.strip(), "Formatter returned empty output."
    assert "##" in markdown, "Formatted output doesn't look like the expected markdown structure."
    print("  OK — formatted output looks valid.")

    print("\n--- Preview of generated schema block ---")
    print(markdown[:500] + ("..." if len(markdown) > 500 else ""))
    print("--- End preview ---")

    print("\nAll checks passed.")
    print("Run `python -m db.generate_schema` to write the full output to a file.")


if __name__ == "__main__":
    main()