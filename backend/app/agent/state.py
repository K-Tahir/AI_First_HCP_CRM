"""LangGraph agent state definition.

The state flows through every node of the graph: intent detection, tool
selection, tool execution, and response synthesis. `session_id` and `db`
are injected per-invocation (not persisted in the checkpoint) so that each
HTTP request operates on its own database session.
"""
from typing import Annotated, Any, Optional, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """Shared state object threaded through the LangGraph graph."""

    # Conversation memory - accumulates via LangGraph's `add_messages` reducer.
    messages: Annotated[list, add_messages]

    # Per-request context (not part of long-term memory).
    session_id: str

    # Result payload populated by whichever tool executes, consumed by the
    # response node and returned to the FastAPI route.
    tool_used: Optional[str]
    interaction: Optional[dict[str, Any]]
    # All interactions created/edited THIS turn, in order (usually just one,
    # but a single message can name multiple HCPs, producing several - see
    # tools_node in graph.py, which accumulates into this list so the last
    # one never silently overwrites the others).
    interactions: Optional[list[dict[str, Any]]]
    history: Optional[list[dict[str, Any]]]
    recommendations: Optional[list[str]]
    follow_up: Optional[dict[str, Any]]
