import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  // 45s (up from 30s): multi-HCP logging and recommend_action can trigger
  // several sequential LLM calls in a single turn. Conversation-history
  // trimming and history-query capping (see backend) now keep each
  // individual call's latency bounded regardless of session length, but a
  // multi-call turn still needs a bit more headroom than a single call.
  timeout: 45000,
});

/**
 * Send a natural-language message to the AI Assistant. This is the ONLY
 * write path in the application - it drives every LangGraph tool and,
 * transitively, every CRM mutation.
 */
export async function sendChatMessage(sessionId, message) {
  const { data } = await apiClient.post("/chat", { session_id: sessionId, message });
  return data;
}

export async function fetchHistory(doctorName, limit = 50) {
  const { data } = await apiClient.get(`/history/${encodeURIComponent(doctorName)}`, {
    params: { limit },
  });
  return data;
}

/**
 * Fetch a page of interactions for the Browse panel - a plain, filterable,
 * paginated REST call that never touches the chat/LLM at all. Used for
 * passive Previous/Next record browsing so it stays fast and doesn't put
 * any load on the AI agent.
 *
 * `filters` may include: hcp_name, hospital, product, sentiment,
 * interaction_type, date_from, date_to (all optional, all strings/dates).
 */
export async function fetchInteractionsPage(filters = {}, offset = 0, limit = 1) {
  const cleanFilters = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== null && v !== "")
  );
  const { data } = await apiClient.get("/interactions", {
    params: { ...cleanFilters, offset, limit },
  });
  return data; // { total, items }
}

/**
 * Fetch a page of interactions as a LIST (not a single record) - powers the
 * Browse panel's table/multi-select view. Same underlying filtered/paginated
 * REST endpoint as fetchInteractionsPage, just with a page-sized limit
 * instead of 1, so filter semantics can never drift between the two views.
 */
export async function fetchInteractionsList(filters = {}, offset = 0, limit = 20) {
  return fetchInteractionsPage(filters, offset, limit);
}

/** Delete a single interaction (and its follow-ups, cascaded server-side). */
export async function deleteInteraction(interactionId) {
  await apiClient.delete(`/interactions/${interactionId}`);
}

/**
 * Delete multiple interactions in one call. Returns
 * { deleted_ids, missing_ids } - missing_ids covers anything that was
 * already gone (e.g. deleted from another tab) rather than failing the
 * whole batch.
 */
export async function bulkDeleteInteractions(interactionIds) {
  const { data } = await apiClient.post("/interactions/bulk-delete", {
    interaction_ids: interactionIds,
  });
  return data;
}
