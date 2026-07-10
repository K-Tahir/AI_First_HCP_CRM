import axios from "axios";

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
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
