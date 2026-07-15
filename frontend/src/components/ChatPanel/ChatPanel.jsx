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
  const browseActive = useSelector((s) => s.browse.active);
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

      // The "Live" interaction state always updates in the background,
      // regardless of whether the rep is currently looking at Browse mode -
      // Browse is just a passive viewer, it never blocks Live from staying
      // current. We only decide separately (below) whether to *visibly*
      // interrupt Browse mode or just notify quietly.
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
        const loggedCount = data.interactions ? data.interactions.length : data.interaction ? 1 : 0;
        if (browseActive && data.interaction) {
          // Per design: while browsing, a new/edited interaction does NOT
          // yank the panel back to Live automatically - just surface a
          // clickable notification so the rep can jump there when ready.
          const label =
            loggedCount > 1
              ? `${loggedCount} interactions logged — click here to view`
              : "New interaction logged — click here to view";
          dispatch(pushToast({ message: label, type: "success", onClickAction: "exit_browse" }));
        } else if (loggedCount > 1) {
          dispatch(pushToast({ message: `${loggedCount} interactions logged via ${data.tool_used.replace(/_/g, " ")}`, type: "success" }));
        } else {
          dispatch(pushToast({ message: `AI updated the CRM via ${data.tool_used.replace(/_/g, " ")}`, type: "success" }));
        }
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error("Chat request failed:", err);

      let detail;
      if (err?.response?.data?.detail) {
        // The backend actually responded with a real error (4xx/5xx) - show
        // that specific message rather than a generic one.
        detail = err.response.data.detail;
      } else if (err?.code === "ECONNABORTED" || /timeout/i.test(err?.message || "")) {
        // Axios's own timeout (configured in api/client.js) - the request
        // never got a response in time. This is NOT the same as the server
        // being unreachable, and is usually caused by a long-running
        // request (e.g. a very broad query or a slow model response), not
        // a down backend - worth telling the rep that distinctly.
        detail =
          "That request took too long and timed out. It may still be processing - try a more " +
          "specific question, or wait a moment and try again.";
      } else if (err?.request) {
        // A request was sent but no response of any kind came back - this
        // is the genuine "server isn't reachable" case.
        detail = "I couldn't reach the CRM backend. Please check that the API server is running and try again.";
      } else {
        detail = "Something went wrong processing that request.";
      }

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
