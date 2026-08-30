"""
SQL generation node.

Takes the current AgentState (question + system prompt, and on a retry,
the previous failed SQL + error) and calls Groq to produce a single SQL
query. Does NOT validate or execute the query.
"""

from groq import Groq

from agent.state import AgentState
from config.settings import settings

_client = Groq(api_key=settings.groq_api_key)

# The base system prompt (prompts/system_prompt.md) describes the FINAL
# user-facing output format (Answer + Query), which is only relevant once
# a query has succeeded.

_GENERATION_INSTRUCTION = (
    "\n\n---\n"
    "For this specific request, ignore the 'Output Format' section above. "
    "If the question can be answered using only the schema above, respond "
    "with ONLY the raw SQL query — no 'Answer:' or 'Query:' labels, no "
    "explanation, no markdown code fences, no placeholder/NULL columns "
    "for data that doesn't exist. "
    "If the question asks for data that is NOT in the schema (e.g. a "
    "column that doesn't exist), do NOT invent a query with NULL or fake values."
    "Instead, respond with EXACTLY this format: NO_QUERY: <one sentence "
    "explaining what's missing>"
)


def _format_history(history: list) -> str:
    """
    Formats prior turns (from memory_read) into a compact block for the prompt.
    Only successful turns are included. A failed turn's SQL isn't useful context
    for resolving a follow-up question, and could confuse the model into repeating
    the same mistake.
    """
    successful_turns = [t for t in history if t.get("succeeded")]
    if not successful_turns:
        return ""

    lines = ["Prior conversation in this session, oldest to newest (the LAST one is the most recent turn):"]
    for turn in successful_turns:
        lines.append(f"- Q: {turn.get('question')}")
        lines.append(f"  SQL used: {turn.get('sql')}")
    return "\n".join(lines)


def _build_user_message(state: AgentState) -> str:
    """
    Builds the user-turn message sent to the LLM. On a first attempt this
    is the question plus any relevant prior-turn history (so follow-up
    questions like "what about last year?" can be resolved). On a retry,
    it instead includes the previous SQL and the error it produced, so
    the model can self-correct rather than generating blindly again.
    """
    question = state["question"]

    if state.get("retry_count", 0) > 0 and state.get("last_error"):
        return (
            f"Question: {question}\n\n"
            f"Your previous SQL attempt failed:\n{state.get('generated_sql')}\n\n"
            f"Error returned by the database:\n{state['last_error']}\n\n"
            f"Fix the query and return only the corrected SQL."
        )

    history_block = _format_history(state.get("conversation_history") or [])
    if history_block:
        return (
            f"{history_block}\n\n"
            f"Current question: {question}\n\n"
            f"IMPORTANT: If the current question omits details that were "
            f"specified in the most recent prior question — such as a "
            f"specific race, year, or driver filter — assume it is a "
            f"follow-up continuing that SAME context, and carry that "
            f"filter over. For example, if the prior question was about "
            f"the Belgian Grand Prix and the current question just asks "
            f"'who finished 19th?', interpret it as 'who finished 19th "
            f"in the Belgian Grand Prix', not as an unfiltered question "
            f"across all races. Only treat it as a fully new, unrelated "
            f"question if it clearly changes topic (e.g. mentions a "
            f"different race, or says something like 'overall' or "
            f"'across all races').\n\n"
            f"Return only the SQL query that answers the current question."
        )

    return f"Question: {question}\n\nReturn only the SQL query that answers this question."


def generate_sql(state: AgentState) -> AgentState:
    """
    LangGraph node function: reads `state`, calls Groq, returns the fields
    to merge back into state (LangGraph merges dict returns into state).
    """
    user_message = _build_user_message(state)

    response = _client.chat.completions.create(
        model=settings.groq_model,
        messages=[
            {"role": "system", "content": state["system_prompt"] + _GENERATION_INSTRUCTION},
            {"role": "user", "content": user_message},
        ],
        temperature=0,
    )

    raw_sql = response.choices[0].message.content.strip()

    if raw_sql.upper().startswith("NO_QUERY:"):
        reason = raw_sql.split(":", 1)[1].strip() if ":" in raw_sql else (
            "This information isn't available in the database."
        )
        return {"generated_sql": None, "no_query_reason": reason}

    # If the model still wraps SQL in a markdown fence
    # # despite instructions not to, extract just the fenced content.
    # if "```" in raw_sql:
    #     parts = raw_sql.split("```")
    #     # parts[1] is the content between the first pair of fences
    #     fenced = parts[1] if len(parts) > 1 else raw_sql
    #     if fenced.lower().startswith("sql"):
    #         fenced = fenced[3:]
    #     raw_sql = fenced.strip()

    return {"generated_sql": raw_sql, "no_query_reason": None}