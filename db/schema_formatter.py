"""
Formats the structured schema metadata (from schema_introspector.py) into
the markdown block that gets pasted into prompts/system_prompt.md as
ground truth.

Kept separate from introspection so the *format* can change (e.g. you
later decide to add sample values, or switch to a more compact syntax)
without touching the DB query logic.
"""

from db.schema_introspector import TableInfo


def format_schema_as_markdown(tables: list[TableInfo]) -> str:
    """
    Produces output like:

    ## public.orders
    - id (integer, PK, not null)
    - customer_id (integer, not null)
    - total (numeric, nullable)
    - order_date (date, not null)

    ## public.customers
    - id (integer, PK, not null)
    - name (text, not null)
    """
    if not tables:
        return "-- No tables found in scope --"

    sorted_tables = sorted(tables, key=lambda t: (t.schema, t.name))

    blocks = []
    for table in sorted_tables:
        lines = [f"## {table.schema}.{table.name}"]
        for col in table.columns:
            flags = []
            if col.is_primary_key:
                flags.append("PK")
            flags.append("not null" if not col.is_nullable else "nullable")
            flag_str = ", ".join(flags)
            lines.append(f"- {col.name} ({col.data_type}, {flag_str})")
        blocks.append("\n".join(lines))

    return "\n\n".join(blocks)