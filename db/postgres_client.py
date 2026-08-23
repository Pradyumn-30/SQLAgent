"""
Read-only Postgres client.

Defense in depth for the read-only guarantee:
  1. The DB role used here should ONLY have SELECT grants (enforce this
     at the database level — see README "Creating the read-only role").
  2. Every connection additionally sets the session to READ ONLY at the
     Postgres transaction level, so even a misconfigured role would still
     be blocked from writing.
"""

from contextlib import contextmanager
from dataclasses import dataclass

import psycopg2
import psycopg2.extras

from config.settings import settings


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[dict]
    row_count: int


class PostgresReadOnlyClient:
    def __init__(self):
        self._conn_params = dict(
            host=settings.pg_host,
            port=settings.pg_port,
            dbname=settings.pg_database,
            user=settings.pg_user,
            password=settings.pg_password,
        )

    @contextmanager
    def _connection(self):
        conn = psycopg2.connect(**self._conn_params)
        try:
            # Defense in depth: enforce read-only at the transaction level,
            # regardless of what the DB role's grants already restrict.
            conn.set_session(readonly=True, autocommit=False)
            yield conn
        finally:
            conn.close()

    def test_connection(self) -> bool:
        """Quick health check — used at startup to fail fast on bad config."""
        with self._connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True

    def execute_query(self, sql: str, params: tuple | None = None) -> QueryResult:
        """
        Executes a single SQL statement and returns structured results.
        Raises psycopg2.Error subclasses on failure — callers (the retry
        node, in a later sub-problem) are expected to catch and handle these.
        """
        with self._connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                columns = [desc.name for desc in cur.description] if cur.description else []
                return QueryResult(
                    columns=columns,
                    rows=[dict(r) for r in rows],
                    row_count=len(rows),
                )