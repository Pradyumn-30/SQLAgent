"""
Response formatting node.

Runs LAST in the graph — after execution has either succeeded, or after
the retry loop has been exhausted. Produces the final
user-facing output in the Answer/Query format defined by the system
prompt.

On success: makes one small additional Groq call to turn the raw query
results into a natural-language answer (e.g. "There were 214 orders in
July." rather than just dumping a row of numbers). This is a separate,
narrowly-scoped call from generate_sql. It never sees the schema or
generates SQL, it only summarizes already-fetched, already-validated
data.

On failure (all retries exhausted): no LLM call — just an honest,
plain-language failure message plus the last attempted query and error.
"""

from groq import Groq

from agent.state import AgentState
from config.settings import settings

_client = Groq(api_key=settings.groq_api_key)

_SUMMARY_SYSTEM_PROMPT = (
    "You summarize SQL query results into a single, clear, natural-language "
    "sentence or two that directly answers the user's original question. "
    "Use the actual numbers/values from the results. Do not mention SQL, "
    "tables, or columns just answer as if you already knew the facts. "
    "Do not add caveats or disclaimers unless the results are empty."
)


def _summarize_results(question: str, columns: list, rows: list) -> str:
    if not rows:
        return "The query ran successfully but returned no results."

    # Cap how many rows we send to the summarizer — for a long result set,
    # a full natural-language answer isn't meaningful anyway; the table
    # itself (returned separately in query_rows) is the real answer.
    preview_rows = rows[:20]

    response = _client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Original question: {question}\n\n"
                    f"Columns: {columns}\n"
                    f"Rows ({len(rows)} total, showing up to 20): {preview_rows}"
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
    if state.get("execution_succeeded"):
        answer_text = _summarize_results(
            question=state["question"],
            columns=state.get("query_columns") or [],
            rows=state.get("query_rows") or [],
        )
        final_sql = state.get("final_sql") or state.get("generated_sql")
        formatted = f"Answer: {answer_text}\nQuery: {final_sql}"
        return {"final_answer": formatted}

    # All retries exhausted without success.
    last_sql = state.get("generated_sql")
    last_error = state.get("last_error") or "Unknown error."
    formatted = (
        "I wasn't able to answer that question — the query failed after "
        f"{state.get('retry_count', 0)} attempt(s).\n\n"
        f"Last attempted query: {last_sql}\n"
        f"Error: {last_error}"
    )
    return {"final_answer": formatted}