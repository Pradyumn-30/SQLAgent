"""
SQL generation node.

Takes the current AgentState (question + system prompt, and on a retry,
the previous failed SQL + error) and calls Groq to produce a single SQL
query.
"""

# pyrefly: ignore [missing-import]
from groq import Groq

from agent.state import AgentState
from config.settings import settings

_client = Groq(api_key=settings.groq_api_key)

# The base system prompt (prompts/system_prompt.md) describes the FINAL
# user-facing output format (Answer + Query), which is only relevant once
# a query has succeeded. For this node, we only want the raw SQL back, so we
# append an override instruction scoped to this call.
_GENERATION_INSTRUCTION = (
    "\n\n---\n"
    "For this specific request, ignore the 'Output Format' section above. "
    "Respond with ONLY the raw SQL query — no 'Answer:' or 'Query:' labels, "
    "no explanation, no markdown code fences. Just the SQL statement itself."
)


def _build_user_message(state: AgentState) -> str:
    """
    Builds the user-turn message sent to the LLM. On a first attempt this is
    just the question.

    On a retry, it also includes the previous SQL and the error it produced, so
    the model can self-correct instead of generating blindly from scratch again.
    """
    question = state["question"]

    if state.get("retry_count", 0) > 0 and state.get("last_error"):
        return (
            f"Question: {question}\n\n"
            f"Your previous SQL attempt failed:\n{state.get('generated_sql')}\n\n"
            f"Error returned by the database:\n{state['last_error']}\n\n"
            f"Fix the query and return only the corrected SQL."
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

    # # Fallback: if the model still wraps SQL in a markdown fence
    # # despite instructions not to, extract just the fenced content.
    # if "```" in raw_sql:
    #     parts = raw_sql.split("```")
    #     # parts[1] is the content between the first pair of fences
    #     fenced = parts[1] if len(parts) > 1 else raw_sql
    #     if fenced.lower().startswith("sql"):
    #         fenced = fenced[3:]
    #     raw_sql = fenced.strip()

    return {"generated_sql": raw_sql}