"""GET /history/{doctor} - fetch chronological interaction history for an HCP."""
from fastapi import APIRouter

from app.dependencies import DbSession
from app.schemas.interaction import InteractionListResponse, InteractionRead
from app.services.interaction_service import InteractionService, serialize_interaction

router = APIRouter(tags=["history"])


@router.get("/history/{doctor}", response_model=InteractionListResponse)
def get_history_for_doctor(doctor: str, db: DbSession, limit: int = 50) -> InteractionListResponse:
    service = InteractionService(db)
    interactions = service.list_history(doctor_name=doctor, limit=limit)
    items = [InteractionRead(**serialize_interaction(i)) for i in interactions]
    return InteractionListResponse(total=len(items), items=items)
