import React from "react";

/**
 * A single field in the Interaction Details panel.
 *
 * Deliberately read-only: this is the AI-controlled CRM form. Fields never
 * accept direct input - they only render whatever the LangGraph agent has
 * extracted, and flash briefly when the AI just updated them.
 */
export default function FormField({ label, value, placeholder, highlighted, span, children }) {
  const isEmpty = value === null || value === undefined || value === "" ||
    (Array.isArray(value) && value.length === 0);

  return (
    <div className={`field${span ? " field--span" : ""}`}>
      <label className="field__label">{label}</label>
      <div className={`field__value${highlighted ? " field-highlight" : ""}${isEmpty ? " field__value--empty" : ""}`}>
        {children ? children : isEmpty ? placeholder || "—" : value}
      </div>
    </div>
  );
}
