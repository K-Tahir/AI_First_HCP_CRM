"""POST /recommendation - programmatic recommendation endpoint (REST completeness).

Reuses the exact same LangGraph tool logic invoked by the chat agent, so
behavior is identical whether triggered via chat or via direct API call.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.agent.tools.recommend_action_tool import make_recommend_action_tool
from app.dependencies import DbSession

router = APIRouter(tags=["recommendation"])


class RecommendationRequest(BaseModel):
    session_id: str
    hcp_name: str | None = None


class RecommendationResponse(BaseModel):
    message: str
    recommendations: list[str]


@router.post("/recommendation", response_model=RecommendationResponse)
def get_recommendation(payload: RecommendationRequest, db: DbSession) -> RecommendationResponse:
    tool = make_recommend_action_tool(db, payload.session_id)
    result = tool.invoke({"hcp_name": payload.hcp_name})
    return RecommendationResponse(
        message=result.get("message", ""), recommendations=result.get("recommendations", [])
    )
