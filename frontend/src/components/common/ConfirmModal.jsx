import React, { useEffect } from "react";
import "./ConfirmModal.css";

/**
 * Generic confirm/cancel modal. Used by the Browse panel's delete flow so a
 * single-record delete and a multi-select bulk delete share one consistent,
 * unmissable confirmation step - deletion can never happen from a single
 * accidental click.
 */
export default function ConfirmModal({
  open,
  title,
  message,
  confirmLabel = "Delete",
  cancelLabel = "Cancel",
  danger = true,
  onConfirm,
  onCancel,
}) {
  useEffect(() => {
    if (!open) return undefined;
    function handleKeyDown(e) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="confirm-modal-overlay" onClick={onCancel} role="presentation">
      <div
        className="confirm-modal"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-modal-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 id="confirm-modal-title" className="confirm-modal__title">
          {title}
        </h3>
        <p className="confirm-modal__message">{message}</p>
        <div className="confirm-modal__actions">
          <button type="button" className="confirm-modal__btn confirm-modal__btn--cancel" onClick={onCancel}>
            {cancelLabel}
          </button>
          <button
            type="button"
            className={`confirm-modal__btn ${
              danger ? "confirm-modal__btn--danger" : "confirm-modal__btn--primary"
            }`}
            onClick={onConfirm}
            autoFocus
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
