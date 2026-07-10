import React, { useEffect, useRef } from "react";
import { useDispatch, useSelector } from "react-redux";
import MessageBubble from "./MessageBubble";
import ChatInput from "./ChatInput";
import { sendChatMessage } from "../../api/client";
import { addUserMessage, addAssistantMessage, addErrorMessage, setSending } from "../../redux/slices/chatSlice";
import { applyAiInteractionUpdate, clearHighlights } from "../../redux/slices/interactionSlice";
import { setHistory, setRecommendations } from "../../redux/slices/historySlice";
import { pushToast } from "../../redux/slices/uiSlice";
import "./ChatPanel.css";

export default function ChatPanel() {
  const dispatch = useDispatch();
  const messages = useSelector((s) => s.chat.messages);
  const isSending = useSelector((s) => s.chat.isSending);
  const sessionId = useSelector((s) => s.ui.sessionId);
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isSending]);

  async function handleSend(text) {
    dispatch(addUserMessage(text));
    dispatch(setSending(true));

    try {
      const data = await sendChatMessage(sessionId, text);

      if (data.interaction) {
        dispatch(applyAiInteractionUpdate(data.interaction));
        setTimeout(() => dispatch(clearHighlights()), 1900);
      }
      if (data.history) {
        dispatch(setHistory({ items: data.history }));
      }
      if (data.recommendations) {
        dispatch(setRecommendations(data.recommendations));
      }

      dispatch(
        addAssistantMessage({
          content: data.reply,
          toolUsed: data.tool_used,
          history: data.history,
          recommendations: data.recommendations,
          followUp: data.follow_up,
        })
      );

      if (data.tool_used) {
        dispatch(pushToast({ message: `AI updated the CRM via ${data.tool_used.replace(/_/g, " ")}`, type: "success" }));
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Chat request failed:", err);
      const detail =
        err?.response?.data?.detail ||
        "I couldn't reach the CRM backend. Please check that the API server is running and try again.";
      dispatch(addErrorMessage(typeof detail === "string" ? detail : "Something went wrong processing that request."));
      dispatch(pushToast({ message: "Request failed", type: "error" }));
    } finally {
      dispatch(setSending(false));
    }
  }

  return (
    <section className="chat-panel">
      <div className="chat-panel__header">
        <div className="chat-panel__title-row">
          <span className="chat-panel__ai-dot" />
          <h2>AI Assistant</h2>
        </div>
        <p className="chat-panel__subtitle">Log interactions via natural conversation</p>
      </div>

      <div className="chat-panel__messages" ref={scrollRef}>
        {messages.map((m) => (
          <MessageBubble key={m.id} message={m} />
        ))}
        {isSending && (
          <div className="msg-row">
            <div className="msg-avatar">AI</div>
            <div className="msg-bubble msg-bubble--typing">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
      </div>

      <ChatInput onSend={handleSend} disabled={isSending} />
    </section>
  );
}
