"""LangGraph Tool 3 - View Interaction History.

Retrieves previously logged interactions, filterable by HCP name(s),
hospital, product, sentiment, interaction type, and/or a date range. Large
result sets are capped and paired with a small, pre-computed summary
(sentiment breakdown, distinct HCPs/hospitals/products, date range) rather
than ever dumping every matching row into the LLM's context - the summary
is cheap to compute and lets the reply stay accurate without the model
needing to read (or restate) dozens of rows itself.
"""
from datetime import date
from typing import Optional

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.interaction_service import InteractionService, serialize_interaction


class ViewHistoryArgs(BaseModel):
    hcp_names: Optional[list[str]] = Field(
        None,
        description=(
            "Filter to interactions with any of these HCP names (partial match). Include EVERY "
            "name the rep mentioned - if they ask about two doctors in one message, pass both "
            "names here, not just one."
        ),
    )
    hospital: Optional[str] = Field(None, description="Filter to interactions at this hospital/clinic")
    product: Optional[str] = Field(None, description="Filter to interactions where this product was discussed")
    sentiment: Optional[str] = Field(None, description="Positive, Neutral, or Negative")
    interaction_type: Optional[str] = Field(
        None, description="Meeting, Call, Email, Conference, or Virtual"
    )
    date_from: Optional[date] = Field(None, description="Only include interactions on/after this date")
    date_to: Optional[date] = Field(None, description="Only include interactions on/before this date")
    limit: Optional[int] = Field(
        None,
        description=(
            "Max rows to actually display in the table (default 20, hard-capped at 50 regardless "
            "of what's requested). The true total matching count and a summary are always "
            "computed and returned separately, so a broad query never needs a larger limit to be "
            "answered accurately."
        ),
    )


def make_view_history_tool(db: Session, session_id: str) -> StructuredTool:
    service = InteractionService(db)

    def _run(
        hcp_names: Optional[list[str]] = None,
        hospital: Optional[str] = None,
        product: Optional[str] = None,
        sentiment: Optional[str] = None,
        interaction_type: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: Optional[int] = None,
    ) -> dict:
        result = service.search_history(
            hcp_names=hcp_names,
            hospital=hospital,
            product=product,
            sentiment=sentiment,
            interaction_type=interaction_type,
            date_from=date_from,
            date_to=date_to,
            limit=limit or settings.HISTORY_QUERY_DEFAULT_LIMIT,
            include_summary=True,
        )
        items = [serialize_interaction(i) for i in result["items"]]
        total = result["total"]
        summary = result["summary"]

        if total == 0:
            return {
                "status": "success",
                "message": "No interaction history found matching those filters.",
                "history": [],
                "total_matching": 0,
            }

        shown = len(items)
        if total > shown:
            message = (
                f"Showing the {shown} most recent of {total} total matching interactions "
                f"(displaying more than {settings.HISTORY_QUERY_MAX_LIMIT} rows at once isn't "
                f"supported - use the summary below or narrow the filters instead). "
                f"Sentiment breakdown: {summary['sentiment_breakdown']}. "
                f"HCPs involved: {', '.join(summary['distinct_hcps']) or 'none recorded'}. "
                f"Hospitals: {', '.join(summary['distinct_hospitals']) or 'none recorded'}. "
                f"Products: {', '.join(summary['distinct_products']) or 'none recorded'}. "
                f"Date range covered: {summary['earliest_date']} to {summary['latest_date']}."
            )
        else:
            message = f"Found {total} interaction(s) matching those filters."

        return {
            "status": "success",
            "message": message,
            "history": items,
            "total_matching": total,
            "summary": summary,
        }

    return StructuredTool.from_function(
        func=_run,
        name="view_interaction_history",
        description=(
            "Retrieve previously logged HCP interactions, filterable by one or more HCP names, "
            "hospital, product, sentiment, interaction type, and/or a date range, sorted with the "
            "most recent first. Large matches are capped and summarized rather than listed in full."
        ),
        args_schema=ViewHistoryArgs,
    )
