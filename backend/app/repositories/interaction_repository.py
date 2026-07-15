"""Data access layer for the Interaction entity."""
from datetime import date

from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models.doctor import Doctor
from app.models.interaction import Interaction, InteractionType, Sentiment


class InteractionRepository:
    """Encapsulates all SQL access for Interaction records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    @staticmethod
    def _date_desc_nulls_last():
        """Order by `interaction_date` descending, with NULL dates sorted last.

        SQLAlchemy's `.desc().nullslast()` compiles to a literal `NULLS LAST`
        clause, which Postgres/SQLite/Oracle understand natively but MySQL
        does not (MySQL has no NULLS FIRST/LAST syntax at all) - MySQL
        rejects it outright with a 1064 syntax error. This CASE-based
        expression (0 for a real date, 1 for NULL, ascending) achieves the
        same ordering on every backend, MySQL included. Every ORDER BY in
        this file that touches `interaction_date` MUST use this helper
        instead of `.nullslast()` directly - see git history for how easy
        this is to accidentally reintroduce during a rewrite.
        """
        return (
            case((Interaction.interaction_date.is_(None), 1), else_=0),
            Interaction.interaction_date.desc(),
        )

    def create(self, **fields) -> Interaction:
        interaction = Interaction(**fields)
        self._db.add(interaction)
        self._db.flush()
        return interaction

    def get_by_id(self, interaction_id: int) -> Interaction | None:
        return self._db.get(Interaction, interaction_id)

    def get_many_by_ids(self, interaction_ids: list[int]) -> list[Interaction]:
        if not interaction_ids:
            return []
        stmt = select(Interaction).where(Interaction.id.in_(interaction_ids))
        stmt = stmt.options(selectinload(Interaction.follow_ups))
        return list(self._db.execute(stmt).scalars().all())

    def delete(self, interaction: Interaction) -> None:
        """Delete a single interaction. The ORM-level cascade on
        Interaction.follow_ups (cascade="all, delete-orphan") deletes its
        follow-ups too, as long as the object was loaded through the session
        (not a bare detached row) - which is always true for callers going
        through get_by_id()/get_many_by_ids()."""
        self._db.delete(interaction)
        self._db.flush()

    def get_latest_for_session(self, session_id: str) -> Interaction | None:
        stmt = (
            select(Interaction)
            .where(Interaction.session_id == session_id)
            .order_by(Interaction.id.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def get_latest_for_doctor(self, doctor_id: int) -> Interaction | None:
        """Latest interaction for a SPECIFIC doctor row, by id - not by name.

        Used once a name has already been resolved to one Doctor.id, so two
        doctors that happen to share an identical name (e.g. same surname,
        different hospital) can never be blurred together the way a
        name-based ILIKE lookup could.
        """
        stmt = (
            select(Interaction)
            .where(Interaction.doctor_id == doctor_id)
            .options(selectinload(Interaction.doctor))
            .order_by(*self._date_desc_nulls_last(), Interaction.id.desc())
            .limit(1)
        )
        return self._db.execute(stmt).scalar_one_or_none()

    def update_fields(self, interaction: Interaction, updates: dict) -> Interaction:
        """Apply a partial update, touching only the keys present in `updates`."""
        for key, value in updates.items():
            if hasattr(interaction, key):
                setattr(interaction, key, value)
        self._db.flush()
        return interaction

    # ------------------------------------------------------------------
    # Filtered search - shared by the view_interaction_history LangGraph
    # tool AND the record-browser REST endpoint, so filter semantics can
    # never drift between the two call sites (one query builder, reused
    # for the list query, the count query, and the summary query below).
    # ------------------------------------------------------------------
    def _build_filtered_stmt(
        self,
        hcp_names: list[str] | None = None,
        hospital: str | None = None,
        product: str | None = None,
        sentiment: Sentiment | None = None,
        interaction_type: InteractionType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Select:
        stmt = select(Interaction)

        cleaned_names = [n.strip() for n in (hcp_names or []) if n and n.strip()]
        if cleaned_names:
            stmt = stmt.join(Doctor, Interaction.doctor_id == Doctor.id).where(
                or_(*[Doctor.name.ilike(f"%{name}%") for name in cleaned_names])
            )
        if hospital:
            stmt = stmt.where(Interaction.hospital.ilike(f"%{hospital.strip()}%"))
        if product:
            stmt = stmt.where(Interaction.products_discussed.ilike(f"%{product.strip()}%"))
        if sentiment is not None:
            stmt = stmt.where(Interaction.sentiment == sentiment)
        if interaction_type is not None:
            stmt = stmt.where(Interaction.interaction_type == interaction_type)
        if date_from:
            stmt = stmt.where(Interaction.interaction_date >= date_from)
        if date_to:
            stmt = stmt.where(Interaction.interaction_date <= date_to)

        return stmt

    def list_history(
        self,
        hcp_names: list[str] | None = None,
        hospital: str | None = None,
        product: str | None = None,
        sentiment: Sentiment | None = None,
        interaction_type: InteractionType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Interaction]:
        stmt = self._build_filtered_stmt(
            hcp_names, hospital, product, sentiment, interaction_type, date_from, date_to
        )
        # selectinload follow_ups too (not just doctor): the Browse list and
        # delete-confirmation UI need each row's follow-up count, and doing
        # that eagerly here avoids an N+1 lazy-load per row on that screen.
        stmt = stmt.options(selectinload(Interaction.doctor), selectinload(Interaction.follow_ups))
        stmt = stmt.order_by(*self._date_desc_nulls_last(), Interaction.id.desc())
        stmt = stmt.offset(max(0, offset)).limit(max(1, limit))
        return list(self._db.execute(stmt).scalars().all())

    def count_history(
        self,
        hcp_names: list[str] | None = None,
        hospital: str | None = None,
        product: str | None = None,
        sentiment: Sentiment | None = None,
        interaction_type: InteractionType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> int:
        base_stmt = self._build_filtered_stmt(
            hcp_names, hospital, product, sentiment, interaction_type, date_from, date_to
        )
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        return self._db.execute(count_stmt).scalar_one()

    def summarize_history(
        self,
        hcp_names: list[str] | None = None,
        hospital: str | None = None,
        product: str | None = None,
        sentiment: Sentiment | None = None,
        interaction_type: InteractionType | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        sample_limit: int = 1000,
    ) -> dict:
        """Aggregate stats (sentiment breakdown, distinct HCPs/hospitals/products,
        date range) computed in Python over up to `sample_limit` matching rows.

        This never feeds raw per-row data to the LLM - only these small,
        pre-computed aggregates - which is what keeps a broad query (e.g. a
        month-long date range) cheap regardless of how many rows it matches.
        """
        stmt = self._build_filtered_stmt(
            hcp_names, hospital, product, sentiment, interaction_type, date_from, date_to
        )
        stmt = stmt.options(selectinload(Interaction.doctor))
        stmt = stmt.order_by(*self._date_desc_nulls_last()).limit(sample_limit)
        rows = list(self._db.execute(stmt).scalars().all())

        sentiment_counts: dict[str, int] = {}
        doctor_names: set[str] = set()
        hospitals: set[str] = set()
        products: set[str] = set()
        dates: list[date] = []

        for row in rows:
            if row.sentiment:
                sentiment_counts[row.sentiment.value] = sentiment_counts.get(row.sentiment.value, 0) + 1
            if row.doctor and row.doctor.name:
                doctor_names.add(row.doctor.name)
            if row.hospital:
                hospitals.add(row.hospital)
            if row.products_discussed:
                products.update(p.strip() for p in row.products_discussed.split(",") if p.strip())
            if row.interaction_date:
                dates.append(row.interaction_date)

        return {
            "sentiment_breakdown": sentiment_counts,
            "distinct_hcps": sorted(doctor_names),
            "distinct_hospitals": sorted(hospitals),
            "distinct_products": sorted(products),
            "earliest_date": min(dates).isoformat() if dates else None,
            "latest_date": max(dates).isoformat() if dates else None,
            "sampled_count": len(rows),
        }
