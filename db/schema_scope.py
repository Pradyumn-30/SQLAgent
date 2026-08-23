"""
Schema scoping config for the schema generator.

This defines which Postgres schema(s) and, optionally, which specific
tables the agent is allowed to see. Keeping this separate from the
introspection logic means you can restrict visibility (e.g. hide a
sensitive table) without touching the query logic itself.

Leave TABLE_ALLOWLIST empty to include all tables found in SCHEMA_ALLOWLIST.
"""

from dataclasses import dataclass, field


@dataclass
class SchemaScope:
    # Postgres schemas the agent is allowed to see
    schema_allowlist: list[str] = field(default_factory=lambda: ["public"])

    # Optional: restrict to specific tables only, as "schema.table" strings.
    # Example: ["public.orders", "public.customers"]
    # Leave empty to include every table in schema_allowlist.
    table_allowlist: list[str] = field(default_factory=list)

    # Tables to always exclude, even if they'd otherwise be included.
    # Useful for sensitive tables you never want the agent to know exist.
    table_denylist: list[str] = field(default_factory=list)


# Edit this to match what the agent should be allowed to see.
DEFAULT_SCOPE = SchemaScope(
    schema_allowlist=["public"],
    table_allowlist=[],
    table_denylist=[],
)