import { createSlice, nanoid } from "@reduxjs/toolkit";

function getOrCreateSessionId() {
  const key = "aivoa_session_id";
  let id = window.localStorage.getItem(key);
  if (!id) {
    id = "sess_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    window.localStorage.setItem(key, id);
  }
  return id;
}

const initialState = {
  sessionId: getOrCreateSessionId(),
  loading: false,
  error: null,
  toasts: [],
  activeRightTab: "chat", // "chat" | "history" | "recommendations"
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    setLoading(state, action) {
      state.loading = action.payload;
    },
    setError(state, action) {
      state.error = action.payload;
    },
    pushToast: {
      reducer(state, action) {
        state.toasts.push(action.payload);
      },
      prepare({ message, type, onClickAction }) {
        return {
          payload: { id: nanoid(), message, type: type || "success", onClickAction: onClickAction || null },
        };
      },
    },
    dismissToast(state, action) {
      state.toasts = state.toasts.filter((t) => t.id !== action.payload);
    },
    setActiveRightTab(state, action) {
      state.activeRightTab = action.payload;
    },
  },
});

export const { setLoading, setError, pushToast, dismissToast, setActiveRightTab } =
  uiSlice.actions;
export default uiSlice.reducer;
