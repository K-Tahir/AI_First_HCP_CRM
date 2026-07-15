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

from app.core.config import settings
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

    # ------------------------------------------------------------------
    # HCP / interaction resolution - the single, shared way any tool that
    # needs to act on "the interaction for <name>" figures out which row
    # that is. This replaces each tool doing its own ad hoc name matching
    # and its own silent "just use whatever was touched last" fallback,
    # which is what let a schedule_followup for one HCP land on a
    # completely different HCP's record with no error surfaced anywhere.
    #
    # Every path returns one of three shapes, and callers must not guess
    # past a non-"resolved" result:
    #   {"status": "resolved",  "doctor"/"interaction": <row>}
    #   {"status": "not_found", "message": <str>}
    #   {"status": "ambiguous", "message": <str>, "candidates": [...]}
    # ------------------------------------------------------------------
    def resolve_doctor(self, hcp_name: str) -> dict[str, Any]:
        """Resolve a free-text HCP name to a single Doctor, or a clarification."""
        candidates = self.doctors.find_candidates(hcp_name)
        tier = candidates["exact"] or candidates["prefix"] or candidates["substring"]
        if not tier:
            return {
                "status": "not_found",
                "message": (
                    f"I couldn't find any HCP matching '{hcp_name}'. Did you mean an "
                    f"existing doctor, or should I log a new interaction for them first?"
                ),
            }
        distinct = {doc.id: doc for doc in tier}
        if len(distinct) > 1:
            names = ", ".join(sorted(doc.name for doc in distinct.values()))
            return {
                "status": "ambiguous",
                "message": f"I found multiple HCPs matching '{hcp_name}': {names}. Which one did you mean?",
                "candidates": [
                    {"id": doc.id, "name": doc.name, "hospital": doc.hospital}
                    for doc in distinct.values()
                ],
            }
        return {"status": "resolved", "doctor": next(iter(distinct.values()))}

    def resolve_target_interaction(
        self,
        session_id: str,
        interaction_id: int | None = None,
        hcp_name: str | None = None,
    ) -> dict[str, Any]:
        """Resolve which interaction a mutating tool call (edit / schedule
        follow-up) should act on. An explicit interaction_id always wins; an
        hcp_name is looked up and, on anything other than exactly one
        confident match, returns not_found/ambiguous instead of guessing.
        Only when NEITHER is given does this fall back to "latest interaction
        in this session" - that fallback is for plain corrections with no
        name at all ("actually make that negative"), never for cross-HCP
        guessing."""
        if interaction_id is not None:
            interaction = self.interactions.get_by_id(interaction_id)
            if interaction is None:
                return {"status": "not_found", "message": f"No interaction found with id {interaction_id}."}
            return {"status": "resolved", "interaction": interaction}

        if hcp_name:
            doctor_resolution = self.resolve_doctor(hcp_name)
            if doctor_resolution["status"] != "resolved":
                return doctor_resolution
            doctor = doctor_resolution["doctor"]
            latest = self.interactions.get_latest_for_doctor(doctor.id)
            if latest is None:
                return {
                    "status": "not_found",
                    "message": (
                        f"I found {doctor.name} as an HCP, but there's no logged interaction "
                        f"for them yet. Please log an interaction first."
                    ),
                }
            return {"status": "resolved", "interaction": latest}

        latest = self.get_latest_for_session(session_id)
        if latest is None:
            return {
                "status": "not_found",
                "message": (
                    "There's no interaction logged yet in this conversation. Please log one "
                    "first, or tell me which HCP you mean."
                ),
            }
        return {"status": "resolved", "interaction": latest}

    # ------------------------------------------------------------------
    # Deletion - REST-only (see routes/interactions.py). Deliberately not
    # exposed as a chat tool, so deletion can never be triggered by a
    # misread natural-language message; it always goes through an explicit
    # UI action with its own confirmation step.
    # ------------------------------------------------------------------
    def delete_interaction(self, interaction_id: int) -> None:
        interaction = self.interactions.get_by_id(interaction_id)
        if interaction is None:
            raise ValueError(f"Interaction {interaction_id} not found")
        self.interactions.delete(interaction)
        self._db.commit()

    def delete_interactions(self, interaction_ids: list[int]) -> dict[str, list[int]]:
        found = self.interactions.get_many_by_ids(interaction_ids)
        found_ids = {row.id for row in found}
        missing_ids = [i for i in interaction_ids if i not in found_ids]
        for row in found:
            self.interactions.delete(row)
        self._db.commit()
        return {"deleted_ids": sorted(found_ids), "missing_ids": missing_ids}

    def search_history(
        self,
        hcp_names: list[str] | None = None,
        hospital: str | None = None,
        product: str | None = None,
        sentiment: str | None = None,
        interaction_type: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 20,
        include_summary: bool = False,
    ) -> dict[str, Any]:
        """Single, shared search path used by both the view_interaction_history
        LangGraph tool (include_summary=True, small limit) and the record
        Browse REST endpoint (include_summary=False, arbitrary offset/limit).

        Free-text `sentiment`/`interaction_type` filter values (however the
        LLM or a query string phrased them) are normalized through the exact
        same alias tables used when writing data, so a filter of "positive"
        matches a stored "Positive" reliably. Returns capped items, the TRUE
        total matching count (not just len(items) - the earlier bug), and,
        if requested, aggregate stats computed without ever loading every
        matching row's full data into the LLM's context.
        """
        max_limit = settings.HISTORY_QUERY_MAX_LIMIT if include_summary else settings.INTERACTIONS_LIST_MAX_LIMIT
        default_limit = settings.HISTORY_QUERY_DEFAULT_LIMIT if include_summary else 20
        clamped_limit = max(1, min(limit or default_limit, max_limit))
        clamped_offset = max(0, offset or 0)

        normalized_sentiment = _normalize_sentiment(sentiment) if sentiment else None
        normalized_type = _normalize_interaction_type(interaction_type) if interaction_type else None

        filter_kwargs = dict(
            hcp_names=hcp_names,
            hospital=hospital,
            product=product,
            sentiment=normalized_sentiment,
            interaction_type=normalized_type,
            date_from=date_from,
            date_to=date_to,
        )

        items = self.interactions.list_history(offset=clamped_offset, limit=clamped_limit, **filter_kwargs)
        total = self.interactions.count_history(**filter_kwargs)
        summary = self.interactions.summarize_history(**filter_kwargs) if include_summary else None

        return {"items": items, "total": total, "summary": summary}


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
        "follow_ups_count": len(interaction.follow_ups) if interaction.follow_ups is not None else 0,
    }
