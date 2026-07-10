"""Business/application logic for Interactions.

This module sits between the LangGraph tools / FastAPI routes and the
repository layer. It owns the rules for how a natural-language extraction
gets translated into normalized database fields (e.g. splitting a
comma-separated product list, resolving a Doctor record), keeping that
logic out of both the tools and the routes.
"""
from datetime import date
from typing import Any

from sqlalchemy.orm import Session

from app.models.interaction import Interaction, InteractionType, Sentiment
from app.repositories.doctor_repository import DoctorRepository
from app.repositories.interaction_repository import InteractionRepository

_INTERACTION_TYPE_ALIASES: dict[str, InteractionType] = {
    "meeting": InteractionType.MEETING,
    "visit": InteractionType.MEETING,
    "site visit": InteractionType.MEETING,
    "in-person": InteractionType.MEETING,
    "in person": InteractionType.MEETING,
    "call": InteractionType.CALL,
    "phone call": InteractionType.CALL,
    "phone": InteractionType.CALL,
    "telephonic": InteractionType.CALL,
    "email": InteractionType.EMAIL,
    "conference": InteractionType.CONFERENCE,
    "event": InteractionType.CONFERENCE,
    "congress": InteractionType.CONFERENCE,
    "virtual": InteractionType.VIRTUAL,
    "video call": InteractionType.VIRTUAL,
    "zoom": InteractionType.VIRTUAL,
    "teams": InteractionType.VIRTUAL,
    "online": InteractionType.VIRTUAL,
}

_SENTIMENT_ALIASES: dict[str, Sentiment] = {
    "positive": Sentiment.POSITIVE,
    "good": Sentiment.POSITIVE,
    "happy": Sentiment.POSITIVE,
    "neutral": Sentiment.NEUTRAL,
    "okay": Sentiment.NEUTRAL,
    "negative": Sentiment.NEGATIVE,
    "bad": Sentiment.NEGATIVE,
    "unhappy": Sentiment.NEGATIVE,
}


def _normalize_interaction_type(value: str | None) -> InteractionType | None:
    """Map any free-text interaction type the LLM produces onto a valid enum
    member, defaulting to MEETING for anything unrecognized (never lets a
    raw, unvalidated string reach the database column)."""
    if value is None:
        return None
    if isinstance(value, InteractionType):
        return value
    key = str(value).strip().lower()
    return _INTERACTION_TYPE_ALIASES.get(key, InteractionType.MEETING)


def _normalize_sentiment(value: str | None) -> Sentiment | None:
    """Map any free-text sentiment onto a valid enum member. Unlike
    interaction_type, an unrecognized sentiment is left as None rather than
    guessed, since a wrong sentiment is more misleading than a missing one."""
    if value is None:
        return None
    if isinstance(value, Sentiment):
        return value
    key = str(value).strip().lower()
    return _SENTIMENT_ALIASES.get(key)


class InteractionService:
    def __init__(self, db: Session) -> None:
        self._db = db
        self.doctors = DoctorRepository(db)
        self.interactions = InteractionRepository(db)

    def create_interaction(
        self,
        session_id: str,
        hcp_name: str | None = None,
        hospital: str | None = None,
        specialty: str | None = None,
        interaction_date: date | None = None,
        interaction_type: str | None = None,
        products_discussed: list[str] | None = None,
        sentiment: str | None = None,
        brochures_shared: bool | None = None,
        samples_requested: bool | None = None,
        questions_raised: str | None = None,
        notes: str | None = None,
        discussion_summary: str | None = None,
        follow_up_date: date | None = None,
    ) -> Interaction:
        doctor = None
        if hcp_name:
            doctor = self.doctors.get_or_create(hcp_name, hospital, specialty)

        interaction = self.interactions.create(
            session_id=session_id,
            doctor_id=doctor.id if doctor else None,
            hospital=hospital or (doctor.hospital if doctor else None),
            specialty=specialty or (doctor.specialty if doctor else None),
            interaction_date=interaction_date,
            interaction_type=_normalize_interaction_type(interaction_type),
            products_discussed=_join_products(products_discussed),
            sentiment=_normalize_sentiment(sentiment),
            brochures_shared=bool(brochures_shared) if brochures_shared is not None else False,
            samples_requested=bool(samples_requested) if samples_requested is not None else False,
            questions_raised=questions_raised,
            notes=notes,
            discussion_summary=discussion_summary,
            follow_up_date=follow_up_date,
        )
        self._db.commit()
        self._db.refresh(interaction)
        return interaction

    def update_interaction(self, interaction_id: int, updates: dict[str, Any]) -> Interaction:
        interaction = self.interactions.get_by_id(interaction_id)
        if interaction is None:
            raise ValueError(f"Interaction {interaction_id} not found")

        clean_updates: dict[str, Any] = {}

        hcp_name = updates.pop("hcp_name", None)
        if hcp_name:
            doctor = self.doctors.get_or_create(
                hcp_name, updates.get("hospital"), updates.get("specialty")
            )
            clean_updates["doctor_id"] = doctor.id

        if "products_discussed" in updates and updates["products_discussed"] is not None:
            clean_updates["products_discussed"] = _join_products(updates.pop("products_discussed"))
        else:
            updates.pop("products_discussed", None)

        if "interaction_type" in updates:
            clean_updates["interaction_type"] = _normalize_interaction_type(updates.pop("interaction_type"))
        if "sentiment" in updates:
            clean_updates["sentiment"] = _normalize_sentiment(updates.pop("sentiment"))

        for key, value in updates.items():
            if value is not None:
                clean_updates[key] = value

        self.interactions.update_fields(interaction, clean_updates)
        self._db.commit()
        self._db.refresh(interaction)
        return interaction

    def get_latest_for_session(self, session_id: str) -> Interaction | None:
        return self.interactions.get_latest_for_session(session_id)

    def get_by_id(self, interaction_id: int) -> Interaction | None:
        return self.interactions.get_by_id(interaction_id)

    def list_history(
        self,
        doctor_name: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        limit: int = 50,
    ) -> list[Interaction]:
        return self.interactions.list_history(doctor_name, date_from, date_to, limit)


def _join_products(products: list[str] | None) -> str | None:
    if not products:
        return None
    return ", ".join(p.strip() for p in products if p and p.strip())


def _split_products(products: str | None) -> list[str]:
    if not products:
        return []
    return [p.strip() for p in products.split(",") if p.strip()]


def serialize_interaction(interaction: Interaction | None) -> dict[str, Any] | None:
    """Convert an Interaction ORM object into the flat dict the frontend form expects."""
    if interaction is None:
        return None

    return {
        "id": interaction.id,
        "session_id": interaction.session_id,
        "doctor_id": interaction.doctor_id,
        "hcp_name": interaction.doctor.name if interaction.doctor else None,
        "hospital": interaction.hospital,
        "specialty": interaction.specialty,
        "interaction_date": interaction.interaction_date,
        "interaction_type": interaction.interaction_type.value if interaction.interaction_type else None,
        "products_discussed": _split_products(interaction.products_discussed),
        "sentiment": interaction.sentiment.value if interaction.sentiment else None,
        "brochures_shared": interaction.brochures_shared,
        "samples_requested": interaction.samples_requested,
        "questions_raised": interaction.questions_raised,
        "notes": interaction.notes,
        "discussion_summary": interaction.discussion_summary,
        "follow_up_date": interaction.follow_up_date,
    }
