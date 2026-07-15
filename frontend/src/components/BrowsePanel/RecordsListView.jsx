import React, { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  listFetchStart,
  listFetchSuccess,
  listFetchError,
  toggleSelected,
  selectAllOnPage,
  deselectAllOnPage,
  clearSelection,
} from "../../redux/slices/browseSlice";
import { fetchInteractionsList, deleteInteraction, bulkDeleteInteractions } from "../../api/client";
import { pushToast } from "../../redux/slices/uiSlice";
import ConfirmModal from "../common/ConfirmModal";
import "./RecordsListView.css";

const PAGE_SIZE = 20;

function formatDate(isoDate) {
  if (!isoDate) return "—";
  const [y, m, d] = isoDate.split("-");
  if (!y || !m || !d) return isoDate;
  return `${d}/${m}/${y}`;
}

/**
 * Table + checkbox view over all logged interactions, for selecting one or
 * many records to delete. A sibling to the single-record Previous/Next
 * viewer in BrowseBar (same filters, same read-only-until-you-delete
 * contract) - kept as a separate component/state slice so switching modes
 * never clobbers the other mode's pagination.
 */
export default function RecordsListView({ filters }) {
  const dispatch = useDispatch();
  const records = useSelector((s) => s.browse.listRecords);
  const offset = useSelector((s) => s.browse.listOffset);
  const total = useSelector((s) => s.browse.listTotal);
  const loading = useSelector((s) => s.browse.listLoading);
  const error = useSelector((s) => s.browse.listError);
  const selectedIds = useSelector((s) => s.browse.selectedIds);

  // { ids: number[], count: number, followUpCount: number } while a
  // confirmation is pending; null otherwise. Holding the target set here
  // (rather than re-reading selectedIds at confirm time) means a stray
  // selection change while the modal is open can't silently change what
  // gets deleted.
  const [pendingDelete, setPendingDelete] = useState(null);

  async function loadPage(targetOffset) {
    dispatch(listFetchStart());
    try {
      const data = await fetchInteractionsList(filters, targetOffset, PAGE_SIZE);
      dispatch(listFetchSuccess({ offset: targetOffset, total: data.total, items: data.items }));
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Records list fetch failed:", err);
      dispatch(listFetchError("Couldn't load records. Please try again."));
    }
  }

  useEffect(() => {
    loadPage(0);
    dispatch(clearSelection());
    // Re-fetch whenever the shared Browse filters change; selection is
    // cleared too since a filter change can make prior selections invisible.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(filters)]);

  const pageIds = records.map((r) => r.id);
  const allOnPageSelected = pageIds.length > 0 && pageIds.every((id) => selectedIds.includes(id));

  function handleToggleAllOnPage() {
    if (allOnPageSelected) {
      dispatch(deselectAllOnPage(pageIds));
    } else {
      dispatch(selectAllOnPage(pageIds));
    }
  }

  function requestDelete(ids) {
    const targeted = records.filter((r) => ids.includes(r.id));
    const followUpCount = targeted.reduce((sum, r) => sum + (r.follow_ups_count || 0), 0);
    setPendingDelete({ ids, count: ids.length, followUpCount });
  }

  async function confirmDelete() {
    const { ids } = pendingDelete;
    setPendingDelete(null);
    try {
      if (ids.length === 1) {
        await deleteInteraction(ids[0]);
      } else {
        await bulkDeleteInteractions(ids);
      }
      dispatch(pushToast({ message: `Deleted ${ids.length} record${ids.length > 1 ? "s" : ""}.`, type: "success" }));
      dispatch(deselectAllOnPage(ids));
      // Reload the current page; if this emptied it out, step back a page.
      const remainingOnPage = records.length - ids.filter((id) => pageIds.includes(id)).length;
      const nextOffset = remainingOnPage === 0 && offset > 0 ? Math.max(0, offset - PAGE_SIZE) : offset;
      loadPage(nextOffset);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Delete failed:", err);
      dispatch(pushToast({ message: "Delete failed. Please try again.", type: "error" }));
    }
  }

  return (
    <div className="records-list">
      <div className="records-list__toolbar">
        <span className="records-list__count">
          {loading ? "Loading…" : total === 0 ? "No matching records" : `${total} record(s)`}
        </span>
        <button
          type="button"
          className="records-list__delete-btn"
          disabled={selectedIds.length === 0}
          onClick={() => requestDelete(selectedIds)}
        >
          🗑 Delete Selected{selectedIds.length > 0 ? ` (${selectedIds.length})` : ""}
        </button>
      </div>

      <div className="records-list__table-scroll">
        <table className="records-list__table">
          <thead>
            <tr>
              <th className="records-list__checkbox-col">
                <input
                  type="checkbox"
                  checked={allOnPageSelected}
                  onChange={handleToggleAllOnPage}
                  disabled={pageIds.length === 0}
                  aria-label="Select all records on this page"
                />
              </th>
              <th>Date</th>
              <th>HCP</th>
              <th>Hospital</th>
              <th>Sentiment</th>
              <th>Follow-ups</th>
              <th className="records-list__action-col" />
            </tr>
          </thead>
          <tbody>
            {records.map((r) => (
              <tr key={r.id} className={selectedIds.includes(r.id) ? "records-list__row--selected" : ""}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(r.id)}
                    onChange={() => dispatch(toggleSelected(r.id))}
                    aria-label={`Select record for ${r.hcp_name || "unknown HCP"}`}
                  />
                </td>
                <td>{formatDate(r.interaction_date)}</td>
                <td>{r.hcp_name || "Unknown"}</td>
                <td>{r.hospital || "—"}</td>
                <td>{r.sentiment || "—"}</td>
                <td>{r.follow_ups_count || 0}</td>
                <td>
                  <button
                    type="button"
                    className="records-list__row-delete"
                    onClick={() => requestDelete([r.id])}
                    title="Delete this record"
                    aria-label={`Delete record for ${r.hcp_name || "unknown HCP"}`}
                  >
                    🗑
                  </button>
                </td>
              </tr>
            ))}
            {records.length === 0 && !loading && (
              <tr>
                <td colSpan={7} className="records-list__empty">
                  No interactions match those filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {error && <div className="records-list__error">{error}</div>}

      <div className="records-list__pager">
        <button type="button" disabled={loading || offset === 0} onClick={() => loadPage(Math.max(0, offset - PAGE_SIZE))}>
          ← Previous
        </button>
        <span>{total === 0 ? "0 of 0" : `${offset + 1}-${Math.min(offset + PAGE_SIZE, total)} of ${total}`}</span>
        <button type="button" disabled={loading || offset + PAGE_SIZE >= total} onClick={() => loadPage(offset + PAGE_SIZE)}>
          Next →
        </button>
      </div>

      <ConfirmModal
        open={!!pendingDelete}
        title={pendingDelete && pendingDelete.count > 1 ? `Delete ${pendingDelete.count} records?` : "Delete this record?"}
        message={
          pendingDelete && pendingDelete.followUpCount > 0
            ? `This will also delete ${pendingDelete.followUpCount} associated follow-up${
                pendingDelete.followUpCount > 1 ? "s" : ""
              }. This cannot be undone.`
            : "This cannot be undone."
        }
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </div>
  );
}
