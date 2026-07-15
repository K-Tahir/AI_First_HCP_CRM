import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  enterBrowseMode,
  exitBrowseMode,
  setFilters,
  resetFilters,
  browseFetchStart,
  browseFetchSuccess,
  browseFetchError,
  setViewMode,
} from "../../redux/slices/browseSlice";
import { fetchInteractionsPage } from "../../api/client";
import RecordsListView from "./RecordsListView";
import "./BrowseBar.css";

const SENTIMENT_OPTIONS = ["", "Positive", "Neutral", "Negative"];
const TYPE_OPTIONS = ["", "Meeting", "Call", "Email", "Conference", "Virtual"];
const EMPTY_DRAFT = {
  hcp_name: "",
  hospital: "",
  product: "",
  sentiment: "",
  interaction_type: "",
  date_from: "",
  date_to: "",
};

/**
 * Independent record browser for the Interaction Details panel. This is a
 * plain, read-only REST-backed viewer over ALL logged interactions - it
 * never goes through the chat/LLM, so paging through history puts zero
 * load on the agent. Filtering/paging here never mutates data; the panel
 * stays exactly as read-only in Browse mode as it is in Live mode.
 */
export default function BrowseBar() {
  const dispatch = useDispatch();
  const active = useSelector((s) => s.browse.active);
  const viewMode = useSelector((s) => s.browse.viewMode);
  const filters = useSelector((s) => s.browse.filters);
  const offset = useSelector((s) => s.browse.offset);
  const total = useSelector((s) => s.browse.total);
  const loading = useSelector((s) => s.browse.loading);
  const error = useSelector((s) => s.browse.error);

  const [draft, setDraft] = useState(filters);

  async function loadPage(targetOffset, targetFilters) {
    dispatch(browseFetchStart());
    try {
      const data = await fetchInteractionsPage(targetFilters, targetOffset, 1);
      const record = data.items && data.items.length > 0 ? data.items[0] : null;
      dispatch(browseFetchSuccess({ offset: targetOffset, total: data.total, record }));
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Browse fetch failed:", err);
      dispatch(browseFetchError("Couldn't load that record. Please try again."));
    }
  }

  function handleEnterBrowse() {
    dispatch(enterBrowseMode());
    loadPage(0, filters);
  }

  function handleExitBrowse() {
    dispatch(exitBrowseMode());
  }

  function handleApplyFilters() {
    dispatch(setFilters(draft));
    loadPage(0, draft);
  }

  function handleResetFilters() {
    setDraft(EMPTY_DRAFT);
    dispatch(resetFilters());
    loadPage(0, EMPTY_DRAFT);
  }

  function handleSetViewMode(mode) {
    if (mode === viewMode) return;
    dispatch(setViewMode(mode));
    if (mode === "single") {
      // The single-record view has its own offset/record state that only
      // this component fetches into - refresh it now in case records were
      // deleted while list mode was active. List mode fetches itself.
      loadPage(0, filters);
    }
  }

  function handlePrev() {
    if (offset <= 0 || loading) return;
    loadPage(offset - 1, filters);
  }

  function handleNext() {
    if (offset + 1 >= total || loading) return;
    loadPage(offset + 1, filters);
  }

  if (!active) {
    return (
      <button type="button" className="browse-toggle-btn" onClick={handleEnterBrowse}>
        📖 Browse All Records
      </button>
    );
  }

  return (
    <div className="browse-bar">
      <div className="browse-bar__header">
        <span className="browse-bar__title">Browsing all records (read-only)</span>
        <button type="button" className="browse-bar__exit-btn" onClick={handleExitBrowse}>
          ← Back to Live
        </button>
      </div>

      <div className="browse-bar__filters">
        <input
          className="browse-bar__input"
          placeholder="HCP name"
          value={draft.hcp_name}
          onChange={(e) => setDraft({ ...draft, hcp_name: e.target.value })}
        />
        <input
          className="browse-bar__input"
          placeholder="Hospital"
          value={draft.hospital}
          onChange={(e) => setDraft({ ...draft, hospital: e.target.value })}
        />
        <input
          className="browse-bar__input"
          placeholder="Product"
          value={draft.product}
          onChange={(e) => setDraft({ ...draft, product: e.target.value })}
        />
        <select
          className="browse-bar__input"
          value={draft.sentiment}
          onChange={(e) => setDraft({ ...draft, sentiment: e.target.value })}
        >
          {SENTIMENT_OPTIONS.map((opt) => (
            <option key={opt || "any-sentiment"} value={opt}>
              {opt || "Any sentiment"}
            </option>
          ))}
        </select>
        <select
          className="browse-bar__input"
          value={draft.interaction_type}
          onChange={(e) => setDraft({ ...draft, interaction_type: e.target.value })}
        >
          {TYPE_OPTIONS.map((opt) => (
            <option key={opt || "any-type"} value={opt}>
              {opt || "Any type"}
            </option>
          ))}
        </select>
        <input
          className="browse-bar__input"
          type="date"
          value={draft.date_from}
          onChange={(e) => setDraft({ ...draft, date_from: e.target.value })}
          title="From date"
        />
        <input
          className="browse-bar__input"
          type="date"
          value={draft.date_to}
          onChange={(e) => setDraft({ ...draft, date_to: e.target.value })}
          title="To date"
        />
        <button type="button" className="browse-bar__apply-btn" onClick={handleApplyFilters}>
          Apply
        </button>
        <button type="button" className="browse-bar__reset-btn" onClick={handleResetFilters}>
          Reset
        </button>
      </div>

      <div className="browse-bar__mode-toggle" role="tablist" aria-label="Browse view mode">
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "single"}
          className={`browse-bar__mode-btn${viewMode === "single" ? " browse-bar__mode-btn--active" : ""}`}
          onClick={() => handleSetViewMode("single")}
        >
          Single record
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === "list"}
          className={`browse-bar__mode-btn${viewMode === "list" ? " browse-bar__mode-btn--active" : ""}`}
          onClick={() => handleSetViewMode("list")}
        >
          List / Delete
        </button>
      </div>

      {viewMode === "single" ? (
        <>
          <div className="browse-bar__nav">
            <button type="button" onClick={handlePrev} disabled={loading || offset <= 0}>
              ← Previous
            </button>
            <span className="browse-bar__position">
              {loading
                ? "Loading…"
                : total === 0
                ? "No matching records"
                : `Record ${offset + 1} of ${total}`}
            </span>
            <button type="button" onClick={handleNext} disabled={loading || offset + 1 >= total}>
              Next →
            </button>
          </div>

          {error && <div className="browse-bar__error">{error}</div>}
        </>
      ) : (
        <RecordsListView filters={filters} />
      )}
    </div>
  );
}
