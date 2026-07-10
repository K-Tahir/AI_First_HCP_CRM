import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  items: [],
  recommendations: [],
  lastQueriedHcp: null,
};

const historySlice = createSlice({
  name: "history",
  initialState,
  reducers: {
    setHistory(state, action) {
      state.items = action.payload.items || [];
      state.lastQueriedHcp = action.payload.hcpName || null;
    },
    setRecommendations(state, action) {
      state.recommendations = action.payload || [];
    },
  },
});

export const { setHistory, setRecommendations } = historySlice.actions;
export default historySlice.reducer;
