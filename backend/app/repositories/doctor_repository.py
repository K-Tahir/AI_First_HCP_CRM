"""Data access layer for the Doctor (HCP) entity."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.services.name_utils import normalize_hcp_name


class DoctorRepository:
    """Encapsulates all SQL access for Doctor records."""

    def __init__(self, db: Session) -> None:
        self._db = db

    def find_by_name(self, name: str) -> Doctor | None:
        stmt = select(Doctor).where(func.lower(Doctor.name) == name.strip().lower())
        return self._db.execute(stmt).scalar_one_or_none()

    def find_candidates(self, name: str) -> dict[str, list[Doctor]]:
        """Tiered name matching: exact (normalized) match, then prefix, then substring.

        Callers should use only the FIRST non-empty tier - never mix tiers - so a
        single confident exact match is never diluted by loose partial hits, and a
        genuinely ambiguous set of partial hits is never silently narrowed to one.

        Honorifics ("Dr.", "Doctor") and punctuation can't be cleanly normalized
        in SQL, so this does a cheap SQL ILIKE to narrow the candidate set, then
        does the precise tiering in Python against the normalized names.
        """
        normalized_query = normalize_hcp_name(name).lower()
        if not normalized_query:
            return {"exact": [], "prefix": [], "substring": []}

        # The last token is usually the most selective part of a name (surname),
        # so it narrows the SQL scan without risking an over-narrow first-token match.
        core_token = normalized_query.split(" ")[-1]
        stmt = select(Doctor).where(Doctor.name.ilike(f"%{core_token}%"))
        rows = list(self._db.execute(stmt).scalars().all())

        exact: list[Doctor] = []
        prefix: list[Doctor] = []
        substring: list[Doctor] = []
        for doc in rows:
            norm_doc = normalize_hcp_name(doc.name).lower()
            if norm_doc == normalized_query:
                exact.append(doc)
            elif norm_doc.startswith(normalized_query) or normalized_query.startswith(norm_doc):
                prefix.append(doc)
            elif normalized_query in norm_doc or norm_doc in normalized_query:
                substring.append(doc)
        return {"exact": exact, "prefix": prefix, "substring": substring}

    def get_or_create(
        self, name: str, hospital: str | None = None, specialty: str | None = None
    ) -> Doctor:
        doctor = self.find_by_name(name)
        if doctor:
            # Backfill missing metadata without overwriting known data.
            if hospital and not doctor.hospital:
                doctor.hospital = hospital
            if specialty and not doctor.specialty:
                doctor.specialty = specialty
            self._db.flush()
            return doctor

        doctor = Doctor(name=name.strip(), hospital=hospital, specialty=specialty)
        self._db.add(doctor)
        self._db.flush()
        return doctor

    def get_by_id(self, doctor_id: int) -> Doctor | None:
        return self._db.get(Doctor, doctor_id)
