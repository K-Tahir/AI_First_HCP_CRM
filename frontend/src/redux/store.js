import { configureStore } from "@reduxjs/toolkit";
import interactionReducer from "./slices/interactionSlice";
import chatReducer from "./slices/chatSlice";
import historyReducer from "./slices/historySlice";
import uiReducer from "./slices/uiSlice";
import browseReducer from "./slices/browseSlice";

export const store = configureStore({
  reducer: {
    interaction: interactionReducer,
    chat: chatReducer,
    history: historyReducer,
    ui: uiReducer,
    browse: browseReducer,
  },
});

export default store;
