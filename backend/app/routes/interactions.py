"""Interaction resource endpoints.

Note: per the assignment's core requirement, the frontend's Interaction
Details panel is READ-ONLY and is synced exclusively from `/chat` responses
for its "Live" (AI-driven) view. The GET endpoints here also power the
independent, read-only Browse panel (filterable, paginated record viewer) -
that's a read path, not a mutation path, so it doesn't touch the AI-only
rule. The POST/PUT endpoints exist for REST completeness but are
intentionally NOT wired into the chat-driven UI's form-filling flow.
"""
from datetime import date

from fastapi import APIRouter, HTTPException

from app.dependencies import DbSession
from app.schemas.interaction import (
    InteractionBulkDeleteRequest,
    InteractionBulkDeleteResponse,
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
def list_interactions(
    db: DbSession,
    hcp_name: str | None = None,
    hospital: str | None = None,
    product: str | None = None,
    sentiment: str | None = None,
    interaction_type: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    offset: int = 0,
    limit: int = 20,
) -> InteractionListResponse:
    """Filterable, paginated interaction listing.

    This backs the frontend's Browse panel (Previous/Next stepping through
    all logged interactions, independent of the chat/LLM). `total` is the
    true count of ALL rows matching the filters - not just `len(items)` on
    this page - so the frontend can render an accurate "record X of Y".
    """
    service = InteractionService(db)
    result = service.search_history(
        hcp_names=[hcp_name] if hcp_name else None,
        hospital=hospital,
        product=product,
        sentiment=sentiment,
        interaction_type=interaction_type,
        date_from=date_from,
        date_to=date_to,
        offset=offset,
        limit=limit,
        include_summary=False,
    )
    items = [InteractionRead(**serialize_interaction(i)) for i in result["items"]]
    return InteractionListResponse(total=result["total"], items=items)


@router.post("/bulk-delete", response_model=InteractionBulkDeleteResponse)
def bulk_delete_interactions(payload: InteractionBulkDeleteRequest, db: DbSession) -> InteractionBulkDeleteResponse:
    """Delete multiple interactions (and their follow-ups) in one call.

    Powers the Browse panel's multi-select delete. Silently skips any ID
    that doesn't exist rather than failing the whole batch - the response's
    missing_ids lets the frontend flag those individually if it wants to.
    Registered ahead of the /{interaction_id} routes below so this literal
    path is never shadowed.
    """
    service = InteractionService(db)
    result = service.delete_interactions(payload.interaction_ids)
    return InteractionBulkDeleteResponse(**result)


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


@router.delete("/{interaction_id}", status_code=204)
def delete_interaction(interaction_id: int, db: DbSession) -> None:
    """Delete a single interaction and cascade-delete its follow-ups."""
    service = InteractionService(db)
    try:
        service.delete_interaction(interaction_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
