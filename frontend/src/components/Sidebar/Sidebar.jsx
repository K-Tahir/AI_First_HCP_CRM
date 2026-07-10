import React from "react";
import "./Sidebar.css";

const NAV_ITEMS = [
  { key: "log", label: "Log Interaction", icon: "📋", active: true },
  { key: "hcps", label: "HCPs", icon: "🩺" },
  { key: "history", label: "Visit History", icon: "🕓" },
  { key: "followups", label: "Follow-ups", icon: "📅" },
  { key: "insights", label: "AI Insights", icon: "✨" },
];

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <div className="sidebar__logo">AI</div>
        <span className="sidebar__brand-name">AIVOA</span>
      </div>

      <nav className="sidebar__nav">
        {NAV_ITEMS.map((item) => (
          <div
            key={item.key}
            className={`sidebar__nav-item${item.active ? " sidebar__nav-item--active" : ""}`}
            title={item.label}
          >
            <span className="sidebar__nav-icon">{item.icon}</span>
            <span className="sidebar__nav-label">{item.label}</span>
          </div>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className="sidebar__rep-avatar">RS</div>
        <div className="sidebar__rep-meta">
          <div className="sidebar__rep-name">Rep. Sarah Iyer</div>
          <div className="sidebar__rep-region">West Region</div>
        </div>
      </div>
    </aside>
  );
}
