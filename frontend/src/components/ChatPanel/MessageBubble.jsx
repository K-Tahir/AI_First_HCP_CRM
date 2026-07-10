import React from "react";

function formatDate(isoDate) {
  if (!isoDate) return null;
  const [y, m, d] = isoDate.split("-");
  if (!y || !m || !d) return isoDate;
  return `${d}/${m}/${y}`;
}

function HistoryCard({ items }) {
  if (!items || items.length === 0) {
    return <div className="msg-card msg-card--empty">No interaction history found.</div>;
  }
  return (
    <div className="msg-card msg-card--table-wrap">
      <div className="msg-card__title">Interaction History ({items.length})</div>
      <div className="history-table-scroll">
        <table className="history-table">
          <thead>
            <tr>
              <th>Date</th>
              <th>HCP</th>
              <th>Type</th>
              <th>Products</th>
              <th>Sentiment</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td data-label="Date">{formatDate(item.interaction_date) || "—"}</td>
                <td data-label="HCP">{item.hcp_name || "Unknown"}</td>
                <td data-label="Type">{item.interaction_type || "—"}</td>
                <td data-label="Products">
                  {item.products_discussed?.length ? item.products_discussed.join(", ") : "—"}
                </td>
                <td data-label="Sentiment">
                  {item.sentiment ? (
                    <span className={`sentiment-pill sentiment-pill--${item.sentiment.toLowerCase()}`}>
                      {item.sentiment}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecommendationCard({ items }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="msg-card">
      <div className="msg-card__title">✨ Recommended Next Actions</div>
      <ul className="msg-card__list msg-card__list--recs">
        {items.map((rec, idx) => (
          <li key={idx} className="rec-row">
            {rec}
          </li>
        ))}
      </ul>
    </div>
  );
}

function FollowUpCard({ followUp }) {
  if (!followUp) return null;
  return (
    <div className="msg-card msg-card--followup">
      <div className="msg-card__title">📅 Follow-up Scheduled</div>
      <div className="followup-row">
        <strong>{formatDate(followUp.follow_up_date)}</strong>
        {followUp.notes ? <span> — {followUp.notes}</span> : null}
      </div>
    </div>
  );
}

export default function MessageBubble({ message }) {
  const isUser = message.role === "user";
  return (
    <div className={`msg-row${isUser ? " msg-row--user" : ""}`}>
      {!isUser && <div className="msg-avatar">AI</div>}
      <div className={`msg-bubble${isUser ? " msg-bubble--user" : ""}${message.isError ? " msg-bubble--error" : ""}`}>
        <div className="msg-bubble__text">{message.content}</div>
        {message.toolUsed && !isUser && (
          <div className="msg-bubble__tool-tag">via {formatToolName(message.toolUsed)}</div>
        )}
        {message.history && <HistoryCard items={message.history} />}
        {message.recommendations && <RecommendationCard items={message.recommendations} />}
        {message.followUp && <FollowUpCard followUp={message.followUp} />}
      </div>
    </div>
  );
}

function formatToolName(name) {
  return name
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}
