"""
LangGraph wiring for the Postgres Query Agent.

Flow:
    memory_read -> generate_sql -> validate_sql
                                        |
                        (invalid) -> [retry loop] -> generate_sql
                                        |
                                    (valid) -> execute_sql
                                                    |
                                (failed) -> [retry loop] -> generate_sql
                                                    |
                                              (succeeded) -> format_response -> memory_write -> END

The retry loop is capped at state["max_retries"] (2 max tries, 3 total attempts).
Both validation failures and execution
failures share the same retry path and the same `last_error` field,
since from the retry loop's perspective they're the same thing: "the
last attempt didn't produce usable SQL, try again with this feedback."
"""

from langgraph.graph import END, StateGraph

from agent.nodes.execute_sql import execute_sql
from agent.nodes.format_response import format_response
from agent.nodes.generate_sql import generate_sql
from agent.nodes.memory_read import memory_read
from agent.nodes.memory_write import memory_write
from agent.nodes.validate_sql import validate_sql
from agent.state import AgentState


def _increment_retry(state: AgentState) -> AgentState:
    """Small node: bumps retry_count before looping back to generate_sql."""
    return {"retry_count": state.get("retry_count", 0) + 1}


def _route_after_generation(state: AgentState) -> str:
    """If the model correctly declined (no_query_reason set), skip
    straight to format_response — there's no SQL to validate or execute."""
    if state.get("no_query_reason"):
        return "no_query"
    return "validate"


def _route_after_validation(state: AgentState) -> str:
    if state.get("last_error") is None:
        return "execute"
    return _route_on_failure(state)


def _route_after_execution(state: AgentState) -> str:
    if state.get("execution_succeeded"):
        return "success"
    return _route_on_failure(state)


def _route_on_failure(state: AgentState) -> str:
    """Shared retry-vs-give-up decision, used after both validation and execution failures."""
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 2)
    if retry_count < max_retries:
        return "retry"
    return "give_up"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("memory_read", memory_read)
    graph.add_node("generate_sql", generate_sql)
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_sql", execute_sql)
    graph.add_node("increment_retry", _increment_retry)
    graph.add_node("format_response", format_response)
    graph.add_node("memory_write", memory_write)

    graph.set_entry_point("memory_read")
    graph.add_edge("memory_read", "generate_sql")

    graph.add_conditional_edges(
        "generate_sql",
        _route_after_generation,
        {"validate": "validate_sql", "no_query": "format_response"},
    )

    graph.add_conditional_edges(
        "validate_sql",
        _route_after_validation,
        {"execute": "execute_sql", "retry": "increment_retry", "give_up": "format_response"},
    )
    graph.add_conditional_edges(
        "execute_sql",
        _route_after_execution,
        {"success": "format_response", "retry": "increment_retry", "give_up": "format_response"},
    )

    graph.add_edge("increment_retry", "generate_sql")
    graph.add_edge("format_response", "memory_write")
    graph.add_edge("memory_write", END)

    return graph.compile()


# Compiled once at import time — reused across calls.
agent_graph = build_graph()