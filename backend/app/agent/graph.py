"""LangGraph Agent - the central orchestrator of the CRM.

Graph shape:

    START -> agent -> (conditional) -> tools -> agent -> END
                    -> (conditional) -> END

The `agent` node calls the Groq LLM with all five tools bound via native
function-calling. The LLM decides - based on the conversation - whether a
tool is needed and, if so, which one and with what extracted arguments.
This is the "Intent Detection" + "Tool Selection" step required by the
assignment; nothing is hardcoded or routed with if/else business logic.

The `tools` node executes the tool the LLM selected against the database
and appends a ToolMessage with the structured result. Control returns to
`agent`, which synthesizes a short natural-language reply for the rep and
the graph ends.

Conversation memory is preserved across turns via LangGraph's checkpointer,
keyed by `session_id` (used as the `thread_id`), so the agent remembers
what was logged earlier in the conversation (needed for the Edit tool).
"""
from typing import Any

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agent.llm import invoke_with_self_healing
from app.agent.prompts import build_system_prompt
from app.agent.state import AgentState
from app.agent.tools.edit_interaction_tool import make_edit_interaction_tool
from app.agent.tools.log_interaction_tool import make_log_interaction_tool
from app.agent.tools.recommend_action_tool import make_recommend_action_tool
from app.agent.tools.schedule_followup_tool import make_schedule_followup_tool
from app.agent.tools.view_history_tool import make_view_history_tool
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# A single in-memory checkpointer for the process. Swappable for a persistent
# checkpointer (e.g. SqliteSaver/PostgresSaver) without touching graph logic.
_checkpointer = MemorySaver()


def _build_tools(db: Session, session_id: str) -> list:
    return [
        make_log_interaction_tool(db, session_id),
        make_edit_interaction_tool(db, session_id),
        make_view_history_tool(db, session_id),
        make_schedule_followup_tool(db, session_id),
        make_recommend_action_tool(db, session_id),
    ]


def build_agent_graph(db: Session, session_id: str):
    """Construct a fresh, request-scoped LangGraph agent bound to `db`/`session_id`.

    The graph structure is static, but the tools close over this request's
    SQLAlchemy session, so each HTTP request gets isolated, correctly
    transaction-scoped tool execution.
    """
    tools = _build_tools(db, session_id)
    tools_by_name = {t.name: t for t in tools}

    def agent_node(state: AgentState) -> dict[str, Any]:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=build_system_prompt()), *messages]

        response = invoke_with_self_healing(messages, tools=tools)
        return {"messages": [response]}

    def tools_node(state: AgentState) -> dict[str, Any]:
        last_message: AIMessage = state["messages"][-1]
        tool_messages = []
        result_updates: dict[str, Any] = {}

        for call in last_message.tool_calls:
            tool = tools_by_name.get(call["name"])
            if tool is None:
                tool_messages.append(
                    ToolMessage(
                        content=f"Unknown tool: {call['name']}",
                        tool_call_id=call["id"],
                    )
                )
                continue

            try:
                result = tool.invoke(call["args"])
            except Exception as exc:  # noqa: BLE001
                logger.exception("Tool execution failed: %s", call["name"])
                result = {"status": "error", "message": f"Tool execution failed: {exc}"}

            result_updates["tool_used"] = call["name"]
            if isinstance(result, dict):
                if "interaction" in result:
                    result_updates["interaction"] = result["interaction"]
                if "history" in result:
                    result_updates["history"] = result["history"]
                if "recommendations" in result:
                    result_updates["recommendations"] = result["recommendations"]
                if "follow_up" in result:
                    result_updates["follow_up"] = result["follow_up"]

            tool_messages.append(
                ToolMessage(content=_stringify(result), tool_call_id=call["id"])
            )

        return {"messages": tool_messages, **result_updates}

    def should_continue(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tools_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile(checkpointer=_checkpointer)


def _stringify(result: Any) -> str:
    import json

    def default(value):
        if hasattr(value, "isoformat"):
            return value.isoformat()
        return str(value)

    try:
        return json.dumps(result, default=default)
    except TypeError:
        return str(result)
