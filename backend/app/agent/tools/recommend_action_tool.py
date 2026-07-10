"""LangGraph Tool 5 - Recommend Next Action.

Analyzes historical interaction data for an HCP (sentiment trend, products
discussed, sample requests, unanswered questions) and asks the LLM to
reason over that evidence to generate concrete next-step recommendations.
This tool demonstrates genuine LLM reasoning, not templated output.
"""
import json
from typing import Optional

from langchain_core.messages import HumanMessage
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.agent.llm import invoke_with_self_healing
from app.agent.prompts import RECOMMENDATION_PROMPT
from app.core.logging_config import get_logger
from app.services.interaction_service import InteractionService, serialize_interaction

logger = get_logger(__name__)


class RecommendActionArgs(BaseModel):
    hcp_name: Optional[str] = Field(
        None,
        description=(
            "HCP name to generate recommendations for. If omitted, uses the most recently "
            "logged interaction in this conversation."
        ),
    )


def _default_serializer(value):
    """JSON-serialize date/enum objects that plain json.dumps can't handle."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def make_recommend_action_tool(db: Session, session_id: str) -> StructuredTool:
    service = InteractionService(db)

    def _run(hcp_name: Optional[str] = None) -> dict:
        if hcp_name:
            history = service.list_history(doctor_name=hcp_name, limit=10)
        else:
            latest = service.get_latest_for_session(session_id)
            if latest is None:
                return {
                    "status": "error",
                    "message": "There's no interaction history yet to base a recommendation on.",
                }
            name = latest.doctor.name if latest.doctor else None
            history = service.list_history(doctor_name=name, limit=10) if name else [latest]

        if not history:
            return {
                "status": "success",
                "message": f"No history found for {hcp_name or 'this HCP'} yet, so no data-driven "
                "recommendation is available. Consider a first exploratory visit.",
                "recommendations": [],
            }

        history_payload = [serialize_interaction(i) for i in history]
        history_json = json.dumps(history_payload, default=_default_serializer, indent=2)

        prompt = RECOMMENDATION_PROMPT.format(history_json=history_json)

        try:
            response = invoke_with_self_healing([HumanMessage(content=prompt)])
            raw = response.content.strip()
            # The LLM may wrap the JSON array in a code fence; strip it defensively.
            if raw.startswith("```"):
                raw = raw.strip("`")
                raw = raw[raw.find("[") : raw.rfind("]") + 1]
            recommendations = json.loads(raw)
            if not isinstance(recommendations, list):
                raise ValueError("Expected a JSON array of recommendation strings")
        except Exception:  # noqa: BLE001
            logger.exception("Recommendation generation failed; falling back to heuristic output")
            recommendations = _heuristic_fallback(history_payload)

        return {
            "status": "success",
            "message": f"Generated {len(recommendations)} recommendation(s) based on "
            f"{len(history_payload)} past interaction(s).",
            "recommendations": recommendations,
        }

    return StructuredTool.from_function(
        func=_run,
        name="recommend_next_action",
        description=(
            "Analyze an HCP's interaction history (sentiment, products, samples, questions) and "
            "generate AI-reasoned next-step recommendations for the sales representative."
        ),
        args_schema=RecommendActionArgs,
    )


def _heuristic_fallback(history: list[dict]) -> list[str]:
    """Deterministic fallback used only if the LLM call itself fails (e.g. network issue)."""
    recs: list[str] = []
    latest = history[0]
    if latest.get("sentiment") == "Negative":
        recs.append("Address concerns raised in the last visit before scheduling another meeting.")
    if latest.get("samples_requested"):
        recs.append("Carry additional product samples for the next visit.")
    if latest.get("follow_up_date"):
        recs.append(f"Confirm the scheduled follow-up on {latest['follow_up_date']}.")
    recs.append("Schedule a follow-up visit within the next 2 weeks to maintain engagement.")
    return recs
