import React, { useState } from "react";

const SUGGESTIONS = [
  "Today I met Dr. Smith at City Hospital and discussed Product X. Sentiment was positive and I shared brochures.",
  "Show me the history for Dr. Smith",
  "Schedule a follow-up for next Friday",
  "What should I do next with Dr. Smith?",
];

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  }

  return (
    <div className="chat-input-area">
      {value.length === 0 && (
        <div className="chat-suggestions">
          {SUGGESTIONS.slice(0, 3).map((s) => (
            <button
              type="button"
              key={s}
              className="chat-suggestion-chip"
              onClick={() => onSend(s)}
              disabled={disabled}
            >
              {s.length > 42 ? s.slice(0, 42) + "…" : s}
            </button>
          ))}
        </div>
      )}
      <form className="chat-input-form" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          placeholder="Describe the interaction, or ask for history, follow-ups, or recommendations…"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              handleSubmit(e);
            }
          }}
          rows={2}
          disabled={disabled}
        />
        <button type="submit" className="chat-send-btn" disabled={disabled || !value.trim()}>
          {disabled ? "…" : "Send"}
        </button>
      </form>
    </div>
  );
}
