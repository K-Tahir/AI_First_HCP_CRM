import { createSlice, nanoid } from "@reduxjs/toolkit";

const initialState = {
  messages: [
    {
      id: nanoid(),
      role: "assistant",
      content:
        "Hi, I'm your AI Assistant. Tell me about an HCP interaction and I'll log it for you — " +
        'for example: "Today I met Dr. Smith at City Hospital and discussed Product X. ' +
        'Sentiment was positive and I shared brochures."',
      toolUsed: null,
    },
  ],
  isSending: false,
};

const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addUserMessage(state, action) {
      state.messages.push({ id: nanoid(), role: "user", content: action.payload });
    },
    addAssistantMessage: {
      reducer(state, action) {
        state.messages.push(action.payload);
      },
      prepare({ content, toolUsed, history, recommendations, followUp }) {
        return {
          payload: {
            id: nanoid(),
            role: "assistant",
            content,
            toolUsed: toolUsed || null,
            history: history || null,
            recommendations: recommendations || null,
            followUp: followUp || null,
          },
        };
      },
    },
    addErrorMessage(state, action) {
      state.messages.push({
        id: nanoid(),
        role: "assistant",
        content: action.payload,
        isError: true,
      });
    },
    setSending(state, action) {
      state.isSending = action.payload;
    },
  },
});

export const { addUserMessage, addAssistantMessage, addErrorMessage, setSending } =
  chatSlice.actions;
export default chatSlice.reducer;
