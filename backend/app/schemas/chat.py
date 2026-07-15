"""Pydantic schemas for the /chat endpoint - the sole entry point for AI actions."""
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.schemas.interaction import InteractionRead


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Stable per-browser-session conversation id")
    message: str = Field(..., min_length=1, description="Natural language user message")


class ChatResponse(BaseModel):
    session_id: str
    reply: str = Field(..., description="Natural language assistant reply")
    tool_used: Optional[str] = Field(None, description="Name of the LangGraph tool invoked")
    interaction: Optional[InteractionRead] = Field(
        None, description="Current structured interaction state to sync into the left form"
    )
    interactions: Optional[list[InteractionRead]] = Field(
        None,
        description=(
            "All interactions created/edited THIS turn, in order. Usually just one; a message "
            "naming multiple HCPs produces several, all preserved here (not just the last)."
        ),
    )
    history: Optional[list[dict[str, Any]]] = Field(
        None, description="Populated when the history tool was invoked"
    )
    recommendations: Optional[list[str]] = Field(
        None, description="Populated when the recommendation tool was invoked"
    )
    follow_up: Optional[dict[str, Any]] = Field(
        None, description="Populated when the follow-up tool was invoked"
    )
