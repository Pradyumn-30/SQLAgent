"""
Response formatting node.

Runs LAST in the graph after execution has either succeeded, or after
the retry loop has been exhausted. Produces the final user-facing output
in the Answer/Query format defined by the system prompt.

On success: makes one small additional Groq call to turn the raw query
results into a natural-language answer (e.g. "There were 214 orders in
July." rather than just dumping a row of numbers). This is a separate,
narrowly-scoped call from generate_sql, it never sees the schema or
generates SQL, it only summarizes already-fetched, already-validated
data.

On failure (all retries exhausted): no LLM call, just an honest, plain-language
failure message plus the last attempted query and error,
per the spec.
"""

from groq import Groq

from agent.state import AgentState
from config.settings import settings

_client = Groq(api_key=settings.groq_api_key)

_SUMMARY_SYSTEM_PROMPT = (
    "You summarize SQL query results into a clear, natural-language answer "
    "to the user's original question. Rules:\n"
    "1. The rows provided below ARE the complete, correct results. Never "
    "claim there is no data, no matches, or an empty result if rows are listed.\n"
    "2. Use the actual values from the rows — do not invent, omit, or "
    "generalize any of them.\n"
    "3. If there are multiple rows, mention each one (name/value pairs), "
    "not just a summary count, unless there are more than ~15 rows.\n"
    "4. Do not mention SQL, tables, or columns - just answer naturally.\n"
    "5. Only say results are empty if the rows list given to you is literally empty."
)


def _format_rows_for_prompt(columns: list, rows: list) -> str:
    """
    Formats rows as explicit 'column: value' lines per row, rather than a
    raw Python list/dict repr — easier for a smaller model to parse
    reliably and harder to accidentally skim past or misread as empty.
    """
    lines = []
    for i, row in enumerate(rows, start=1):
        pairs = ", ".join(f"{col}={row.get(col)}" for col in columns)
        lines.append(f"Row {i}: {pairs}")
    return "\n".join(lines)


def _summarize_results(question: str, columns: list, rows: list) -> str:
    if not rows:
        return "The query ran successfully but returned no results."

    # Cap how many rows we send to the summarizer — for a long result set,
    # a full natural-language answer isn't meaningful anyway; the table
    # itself (returned separately in query_rows) is the real answer.
    preview_rows = rows[:20]
    rows_block = _format_rows_for_prompt(columns, preview_rows)

    response = _client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original question: {question}\n\n"
                    f"Number of matching rows: {len(rows)} (showing up to 20 below)\n"
                    f"{rows_block}"
                ),
            },
        ],
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def format_response(state: AgentState) -> AgentState:
    """
    LangGraph node function. Reads the final execution outcome from
    state and returns {"final_answer": ...} to merge back in.
    """
    if state.get("no_query_reason"):
        # The model correctly declined — the question asks for data that
        # isn't in the schema. No SQL was ever generated, so no Query line.
        formatted = f"Answer: {state['no_query_reason']}\nQuery: (none — this data is not available in the database)"
        return {"final_answer": formatted}

    if state.get("execution_succeeded"):
        answer_text = _summarize_results(
            question=state["question"],
            columns=state.get("query_columns") or [],
            rows=state.get("query_rows") or [],
        )
        final_sql = state.get("final_sql") or state.get("generated_sql")
        formatted = f"Answer: {answer_text}\nQuery: {final_sql}"
        return {"final_answer": formatted}

    # All retries exhausted without success — be honest, per the spec.
    last_sql = state.get("generated_sql")
    last_error = state.get("last_error") or "Unknown error."
    formatted = (
        "I wasn't able to answer that question — the query failed after "
        f"{state.get('retry_count', 0)} attempt(s).\n\n"
        f"Last attempted query: {last_sql}\n"
        f"Error: {last_error}"
    )
    return {"final_answer": formatted}