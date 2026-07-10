import { createSlice } from "@reduxjs/toolkit";

const EMPTY_INTERACTION = {
  id: null,
  hcp_name: null,
  hospital: null,
  specialty: null,
  interaction_date: null,
  interaction_type: null,
  products_discussed: [],
  sentiment: null,
  brochures_shared: false,
  samples_requested: false,
  questions_raised: null,
  notes: null,
  discussion_summary: null,
  follow_up_date: null,
};

const initialState = {
  current: EMPTY_INTERACTION,
  recentlyUpdatedFields: [],
};

function diffFields(prev, next) {
  return Object.keys(next).filter((key) => {
    const a = JSON.stringify(prev?.[key] ?? null);
    const b = JSON.stringify(next[key] ?? null);
    return a !== b;
  });
}

const interactionSlice = createSlice({
  name: "interaction",
  initialState,
  reducers: {
    applyAiInteractionUpdate(state, action) {
      const incoming = action.payload;
      if (!incoming) return;
      const merged = { ...EMPTY_INTERACTION, ...state.current, ...incoming };
      state.recentlyUpdatedFields = diffFields(state.current, merged);
      state.current = merged;
    },
    clearHighlights(state) {
      state.recentlyUpdatedFields = [];
    },
    resetInteraction(state) {
      state.current = EMPTY_INTERACTION;
      state.recentlyUpdatedFields = [];
    },
  },
});

export const { applyAiInteractionUpdate, clearHighlights, resetInteraction } =
  interactionSlice.actions;
export default interactionSlice.reducer;
