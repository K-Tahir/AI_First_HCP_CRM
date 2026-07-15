"""POST /chat - the single entry point through which the rep talks to the AI Assistant.

Every CRM mutation in this application flows through this endpoint and,
from there, through the LangGraph agent. The frontend never calls
`/interactions` PUT/POST directly to mutate data driven by chat.
"""
from fastapi import APIRouter, HTTPException

from app.agent.runner import run_agent_turn
from app.dependencies import DbSession
from app.repositories.chat_repository import ChatRepository
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession) -> ChatResponse:
    chat_repo = ChatRepository(db)
    chat_repo.add_message(payload.session_id, role="user", content=payload.message)
    db.commit()

    try:
        result = run_agent_turn(db, payload.session_id, payload.message)
    except RuntimeError as exc:
        # Typically a missing GROQ_API_KEY.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Agent failed to process the request: {exc}") from exc

    chat_repo.add_message(
        payload.session_id, role="assistant", content=result["reply"], tool_used=result.get("tool_used")
    )
    db.commit()

    return ChatResponse(
        session_id=payload.session_id,
        reply=result["reply"],
        tool_used=result.get("tool_used"),
        interaction=result.get("interaction"),
        interactions=result.get("interactions"),
        history=result.get("history"),
        recommendations=result.get("recommendations"),
        follow_up=result.get("follow_up"),
    )
