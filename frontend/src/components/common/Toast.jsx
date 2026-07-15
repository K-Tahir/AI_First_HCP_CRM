import React, { useEffect } from "react";
import { useDispatch, useSelector } from "react-redux";
import { dismissToast } from "../../redux/slices/uiSlice";
import { exitBrowseMode } from "../../redux/slices/browseSlice";
import "./Toast.css";

// Maps a toast's serializable `onClickAction` string to the actual Redux
// action it should dispatch on click. Kept as a lookup table (rather than
// storing a function directly in state) since Redux state must stay
// serializable - functions can't be persisted/inspected/replayed.
const TOAST_ACTIONS = {
  exit_browse: exitBrowseMode,
};

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

  function handleClick(toast) {
    const actionCreator = toast.onClickAction && TOAST_ACTIONS[toast.onClickAction];
    if (actionCreator) {
      dispatch(actionCreator());
    }
    dispatch(dismissToast(toast.id));
  }

  return (
    <div className="toast-stack">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`toast toast--${t.type}${t.onClickAction ? " toast--clickable" : ""}`}
          onClick={t.onClickAction ? () => handleClick(t) : undefined}
          role={t.onClickAction ? "button" : undefined}
          tabIndex={t.onClickAction ? 0 : undefined}
        >
          {t.message}
        </div>
      ))}
    </div>
  );
}
