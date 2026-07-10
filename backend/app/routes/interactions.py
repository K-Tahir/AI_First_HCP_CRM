"""Interaction resource endpoints.

Note: per the assignment's core requirement, the frontend's Interaction
Details panel is READ-ONLY and is synced exclusively from `/chat` responses.
The POST/PUT endpoints here exist for completeness (REST API design,
testing, and potential future integrations) but are intentionally NOT
wired into the chat-driven UI's form-filling flow.
"""
from fastapi import APIRouter, HTTPException

from app.dependencies import DbSession
from app.schemas.interaction import (
    InteractionCreate,
    InteractionListResponse,
    InteractionRead,
    InteractionUpdate,
)
from app.services.interaction_service import InteractionService, serialize_interaction

router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionRead, status_code=201)
def create_interaction(payload: InteractionCreate, db: DbSession) -> InteractionRead:
    service = InteractionService(db)
    interaction = service.create_interaction(**payload.model_dump())
    return InteractionRead(**serialize_interaction(interaction))


@router.get("", response_model=InteractionListResponse)
def list_interactions(db: DbSession, limit: int = 100) -> InteractionListResponse:
    service = InteractionService(db)
    interactions = service.interactions.list_all(limit=limit)
    items = [InteractionRead(**serialize_interaction(i)) for i in interactions]
    return InteractionListResponse(total=len(items), items=items)


@router.get("/{interaction_id}", response_model=InteractionRead)
def get_interaction(interaction_id: int, db: DbSession) -> InteractionRead:
    service = InteractionService(db)
    interaction = service.get_by_id(interaction_id)
    if interaction is None:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return InteractionRead(**serialize_interaction(interaction))


@router.put("/{interaction_id}", response_model=InteractionRead)
def update_interaction(interaction_id: int, payload: InteractionUpdate, db: DbSession) -> InteractionRead:
    service = InteractionService(db)
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    try:
        interaction = service.update_interaction(interaction_id, updates)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return InteractionRead(**serialize_interaction(interaction))
