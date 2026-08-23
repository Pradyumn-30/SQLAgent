"""
Introspects information_schema to produce raw table/column metadata,
respecting the SchemaScope from schema_scope.py.

This only queries and returns structured data — formatting it into the
markdown block for the system prompt.
"""

from dataclasses import dataclass

from db.postgres_client import PostgresReadOnlyClient
from db.schema_scope import SchemaScope


@dataclass
class ColumnInfo:
    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool


@dataclass
class TableInfo:
    schema: str
    name: str
    columns: list[ColumnInfo]


COLUMNS_QUERY = """
    SELECT
        c.table_schema,
        c.table_name,
        c.column_name,
        c.data_type,
        c.is_nullable,
        EXISTS (
            SELECT 1
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
                AND tc.table_schema = c.table_schema
                AND tc.table_name = c.table_name
                AND kcu.column_name = c.column_name
        ) AS is_primary_key
    FROM information_schema.columns c
    WHERE c.table_schema = ANY(%s)
    ORDER BY c.table_schema, c.table_name, c.ordinal_position;
"""


def _is_included(schema: str, table: str, scope: SchemaScope) -> bool:
    qualified = f"{schema}.{table}"
    if qualified in scope.table_denylist:
        return False
    if scope.table_allowlist:
        return qualified in scope.table_allowlist
    return True


def introspect_schema(
    pg_client: PostgresReadOnlyClient,
    scope: SchemaScope,
) -> list[TableInfo]:
    """
    Returns structured metadata for every table allowed.
    Raises the same exceptions as PostgresReadOnlyClient.execute_query
    on failure (e.g. connectivity issues)
    """
    result = pg_client.execute_query(COLUMNS_QUERY, (scope.schema_allowlist,))

    tables: dict[tuple[str, str], TableInfo] = {}
    for row in result.rows:
        key = (row["table_schema"], row["table_name"])
        if not _is_included(row["table_schema"], row["table_name"], scope):
            continue
        if key not in tables:
            tables[key] = TableInfo(schema=row["table_schema"], name=row["table_name"], columns=[])
        tables[key].columns.append(
            ColumnInfo(
                name=row["column_name"],
                data_type=row["data_type"],
                is_nullable=(row["is_nullable"] == "YES"),
                is_primary_key=row["is_primary_key"],
            )
        )

    return list(tables.values())