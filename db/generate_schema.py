"""
Introspects the target Postgres DB and writes the
schema ground-truth block to a file, ready to paste into
prompts/system_prompt.md.

Re-run this whenever the DB schema changes.

Usage:
    python -m db.generate_schema
    python -m db.generate_schema --output prompts/schema_block.md
"""

import argparse
from pathlib import Path

from db.postgres_client import PostgresReadOnlyClient
from db.schema_formatter import format_schema_as_markdown
from db.schema_introspector import introspect_schema
from db.schema_scope import DEFAULT_SCOPE


def main():
    parser = argparse.ArgumentParser(description="Generate schema ground truth for the system prompt.")
    parser.add_argument(
        "--output",
        default="prompts/schema_block.md",
        help="Path to write the generated markdown schema block (default: prompts/schema_block.md)",
    )
    args = parser.parse_args()

    print(f"Introspecting schema(s): {DEFAULT_SCOPE.schema_allowlist} ...")
    pg_client = PostgresReadOnlyClient()
    tables = introspect_schema(pg_client, DEFAULT_SCOPE)
    print(f"Found {len(tables)} table(s) in scope.")

    markdown = format_schema_as_markdown(tables)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"Schema block written to: {output_path}")

if __name__ == "__main__":
    main()