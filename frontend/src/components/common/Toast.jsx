import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { dismissToast } from "../../redux/slices/uiSlice";
import "./Toast.css";

export default function ToastStack() {
  const toasts = useSelector((s) => s.ui.toasts);
  const dispatch = useDispatch();

  useEffect(() => {
    if (toasts.length === 0) return;
    const timers = toasts.map((t) =>
      setTimeout(() => dispatch(dismissToast(t.id)), 3200)
    );
    return () => timers.forEach(clearTimeout);
  }, [toasts, dispatch]);

  if (toasts.length === 0) return null;

  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div key={t.id} className={`toast toast--${t.type}`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}
