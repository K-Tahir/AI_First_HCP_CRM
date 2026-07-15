"""Invokes the LangGraph agent for a single chat turn and extracts results."""
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy.orm import Session

from app.agent.graph import build_agent_graph
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def _strip_markdown(text: str) -> str:
    """Defense-in-depth cleanup of the assistant's reply text.

    The system prompt already instructs the LLM never to use markdown, but
    LLMs don't always follow formatting instructions perfectly. Since the
    UI renders structured data (history/recommendations/follow-ups) as
    proper HTML tables/cards from the tool's return payload, any markdown
    the LLM adds on top is pure duplication that shows up as broken raw
    pipe characters - so it's safe to strip rather than preserve.
    """
    if not text:
        return text

    lines = text.split("\n")
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        # Drop markdown table rows entirely (both header/data rows and the
        # "|---|---|" separator row).
        if stripped.startswith("|") and stripped.endswith("|"):
            continue
        if stripped and set(stripped) <= {"-", "|", ":", " "}:
            continue
        # Strip inline markdown emphasis/heading markers, keep the words.
        line = line.replace("**", "").replace("__", "")
        line = line.lstrip("#").lstrip()
        if line.startswith(("- ", "* ")):
            line = line[2:]
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    # Collapse any run of 3+ blank lines left behind by removed table blocks.
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned or text


def run_agent_turn(db: Session, session_id: str, user_message: str) -> dict[str, Any]:
    """Run one turn of the conversation through the LangGraph agent.

    Returns a dict with the assistant's natural-language reply plus any
    structured payload (interaction/history/recommendations/follow_up) a
    tool produced during this turn.
    """
    graph = build_agent_graph(db, session_id)
    config = {"configurable": {"thread_id": session_id}, "recursion_limit": settings.LANGGRAPH_RECURSION_LIMIT}

    # Explicitly reset the per-turn structured payload fields so a tool that
    # doesn't run this turn can't leak stale data from a previous turn into
    # the response (LangGraph merges unspecified keys from the checkpoint).
    turn_input = {
        "messages": [HumanMessage(content=user_message)],
        "tool_used": None,
        "interaction": None,
        "interactions": None,
        "history": None,
        "recommendations": None,
        "follow_up": None,
    }
    final_state = graph.invoke(turn_input, config=config)

    reply = ""
    for message in reversed(final_state["messages"]):
        if isinstance(message, AIMessage) and message.content:
            reply = message.content
            break

    reply = _strip_markdown(reply)

    return {
        "reply": reply or "I've processed that request.",
        "tool_used": final_state.get("tool_used"),
        "interaction": final_state.get("interaction"),
        "interactions": final_state.get("interactions"),
        "history": final_state.get("history"),
        "recommendations": final_state.get("recommendations"),
        "follow_up": final_state.get("follow_up"),
    }
