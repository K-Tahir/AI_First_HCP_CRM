"""POST /followup - programmatic follow-up creation endpoint (REST completeness)."""
from fastapi import APIRouter

from app.dependencies import DbSession
from app.repositories.followup_repository import FollowUpRepository
from app.schemas.followup import FollowUpCreate, FollowUpRead

router = APIRouter(tags=["followup"])


@router.post("/followup", response_model=FollowUpRead, status_code=201)
def create_followup(payload: FollowUpCreate, db: DbSession) -> FollowUpRead:
    repo = FollowUpRepository(db)
    follow_up = repo.create(**payload.model_dump())
    db.commit()
    db.refresh(follow_up)
    return FollowUpRead.model_validate(follow_up)
