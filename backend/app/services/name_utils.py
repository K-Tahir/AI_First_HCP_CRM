"""Shared helpers for normalizing free-text HCP names before matching.

Used by DoctorRepository.find_candidates() so that however the rep or the
LLM happened to phrase a name in a given message ("Dr. Mohammed", "Doctor
Mohammed.", "mohammed") all normalize to the same comparable string. This
keeps name resolution from silently missing a real match (or over-matching)
just because of honorifics/punctuation/case differences.
"""
import re

_HONORIFIC_PREFIX = re.compile(r"^(dr\.?|doctor|prof\.?|professor)\s+", re.IGNORECASE)
_PUNCTUATION = re.compile(r"[.,]")
_WHITESPACE = re.compile(r"\s+")


def normalize_hcp_name(name: str | None) -> str:
    """Strip honorifics/punctuation and collapse whitespace for comparison.

    'Dr. Mohammed', 'Doctor  Mohammed.', and 'mohammed' all normalize to
    'mohammed'. Case is NOT lowered here - callers should lower() explicitly
    at the comparison site so this function stays reusable for display
    purposes too.
    """
    if not name:
        return ""
    cleaned = _HONORIFIC_PREFIX.sub("", name.strip())
    cleaned = _PUNCTUATION.sub("", cleaned)
    return _WHITESPACE.sub(" ", cleaned).strip()
