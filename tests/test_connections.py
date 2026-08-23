"""
Run this after setting up .env to confirm both the Postgres read-only
connection and Redis connection are working before moving to sub-problem 2.

Usage:
    python -m tests.test_connections
"""

from db.postgres_client import PostgresReadOnlyClient
from memory.redis_client import RedisMemoryClient


def main():
    print("Testing Postgres (read-only) connection...")
    pg = PostgresReadOnlyClient()
    pg.test_connection()
    print("  OK — connected, session is read-only.")

    print("Testing Redis connection...")
    mem = RedisMemoryClient()
    mem.test_connection()
    print("  OK — connected.")

    print("\nAll connections healthy. Ready for sub-problem 2.")


if __name__ == "__main__":
    main()