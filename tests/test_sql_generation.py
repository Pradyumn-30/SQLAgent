"""
Verifies SQL generation node works: calls Groq with a
real question against real schema, and sanity-checks the output
looks like plausible SQL without executing it.

Usage:
    python -m tests.test_sql_generation
"""

from agent.nodes.generate_sql import generate_sql
from prompts.prompt_loader import get_system_prompt


def main():
    system_prompt = get_system_prompt()

    question = "How many total points did each constructor score, across all years?"
    print(f"Question: {question}\n")

    state = {
        "question": question,
        "system_prompt": system_prompt,
        "retry_count": 0,
        "last_error": None,
    }

    result = generate_sql(state)
    sql = result["generated_sql"]

    print("Generated SQL:")
    print(sql)

    assert sql, "generate_sql returned an empty string."
    assert sql.strip().lower().startswith("select"), (
        "Expected a SELECT statement, but the output doesn't start with one. "
        "Check the model's response above — it may have added extra commentary."
    )
    assert "constructors" in sql.lower() or "f1_results" in sql.lower(), (
        "Generated SQL doesn't reference either known table — check the "
        "system prompt actually contains the schema."
    )

    print("\nAll checks passed. SQL generation is producing plausible SQL.")
    print("Note: this query has NOT been executed or validated yet.")


if __name__ == "__main__":
    main()