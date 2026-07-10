import { configureStore } from "@reduxjs/toolkit";
import interactionReducer from "./slices/interactionSlice";
import chatReducer from "./slices/chatSlice";
import historyReducer from "./slices/historySlice";
import uiReducer from "./slices/uiSlice";

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
    history: historyReducer,
    ui: uiReducer,
  },
});

export default store;
