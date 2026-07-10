import React from "react";
import "./Header.css";

export default function Header() {
  return (
    <header className="app-header">
      <div>
        <h1 className="app-header__title">Log HCP Interaction</h1>
        <p className="app-header__subtitle">
          Talk to the AI Assistant — it fills in the interaction record for you.
        </p>
      </div>
      <div className="app-header__badge">
        <span className="app-header__badge-dot" />
        AI-First · LangGraph Agent Active
      </div>
    </header>
  );
}
