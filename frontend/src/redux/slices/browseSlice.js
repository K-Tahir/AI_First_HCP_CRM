import { createSlice } from "@reduxjs/toolkit";

const EMPTY_FILTERS = {
  hcp_name: "",
  hospital: "",
  product: "",
  sentiment: "",
  interaction_type: "",
  date_from: "",
  date_to: "",
};

const initialState = {
  // Whether the left panel is currently showing a browsed record instead of
  // the AI-driven "Live" interaction. Browsing never mutates data - it's a
  // read-only viewer over everything ever logged, independent of chat.
  active: false,
  // "single" = one-record-at-a-time viewer (Previous/Next), the original
  // Browse experience. "list" = a table view with checkboxes, used for
  // selecting one or many records to delete.
  viewMode: "single",
  filters: { ...EMPTY_FILTERS },
  offset: 0,
  total: 0,
  currentRecord: null,
  loading: false,
  error: null,
  // List-mode state (separate from the single-record state above so
  // switching modes never clobbers the other mode's pagination/data).
  listRecords: [],
  listOffset: 0,
  listTotal: 0,
  listLoading: false,
  listError: null,
  selectedIds: [],
};

const browseSlice = createSlice({
  name: "browse",
  initialState,
  reducers: {
    enterBrowseMode(state) {
      state.active = true;
    },
    exitBrowseMode(state) {
      state.active = false;
    },
    setFilters(state, action) {
      state.filters = { ...state.filters, ...action.payload };
      state.offset = 0; // changing filters always restarts from the first matching record
    },
    resetFilters(state) {
      state.filters = { ...EMPTY_FILTERS };
      state.offset = 0;
    },
    setOffset(state, action) {
      state.offset = Math.max(0, action.payload);
    },
    browseFetchStart(state) {
      state.loading = true;
      state.error = null;
    },
    browseFetchSuccess(state, action) {
      const { offset, total, record } = action.payload;
      state.offset = offset;
      state.total = total;
      state.currentRecord = record;
      state.loading = false;
      state.error = null;
    },
    browseFetchError(state, action) {
      state.loading = false;
      state.error = action.payload;
      state.currentRecord = null;
    },
    setViewMode(state, action) {
      state.viewMode = action.payload;
      state.selectedIds = []; // switching modes always clears any in-progress selection
    },
    listFetchStart(state) {
      state.listLoading = true;
      state.listError = null;
    },
    listFetchSuccess(state, action) {
      const { offset, total, items } = action.payload;
      state.listOffset = offset;
      state.listTotal = total;
      state.listRecords = items;
      state.listLoading = false;
      state.listError = null;
    },
    listFetchError(state, action) {
      state.listLoading = false;
      state.listError = action.payload;
    },
    toggleSelected(state, action) {
      const id = action.payload;
      state.selectedIds = state.selectedIds.includes(id)
        ? state.selectedIds.filter((existingId) => existingId !== id)
        : [...state.selectedIds, id];
    },
    selectAllOnPage(state, action) {
      const ids = action.payload;
      state.selectedIds = Array.from(new Set([...state.selectedIds, ...ids]));
    },
    deselectAllOnPage(state, action) {
      const ids = new Set(action.payload);
      state.selectedIds = state.selectedIds.filter((id) => !ids.has(id));
    },
    clearSelection(state) {
      state.selectedIds = [];
    },
  },
});

export const {
  enterBrowseMode,
  exitBrowseMode,
  setFilters,
  resetFilters,
  setOffset,
  browseFetchStart,
  browseFetchSuccess,
  browseFetchError,
  setViewMode,
  listFetchStart,
  listFetchSuccess,
  listFetchError,
  toggleSelected,
  selectAllOnPage,
  deselectAllOnPage,
  clearSelection,
} = browseSlice.actions;

export default browseSlice.reducer;
