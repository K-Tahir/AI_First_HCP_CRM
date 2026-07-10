import React, { useCallback, useEffect, useRef, useState } from "react";
import "./ResizableSplit.css";

/**
 * Two-pane layout with a draggable resize handle and a collapse toggle for
 * the left pane. Percentage width is persisted in component state only
 * (no localStorage, per artifact/browser-storage constraints) - it simply
 * resets to the default on a full page reload.
 */
export default function ResizableSplit({
  left,
  right,
  defaultLeftWidth = 42, // percentage
  minLeftWidth = 24,
  maxLeftWidth = 65,
  collapsedWidth = 0,
}) {
  const [leftWidth, setLeftWidth] = useState(defaultLeftWidth);
  const [collapsed, setCollapsed] = useState(false);
  const containerRef = useRef(null);
  const draggingRef = useRef(false);

  const onPointerMove = useCallback(
    (e) => {
      if (!draggingRef.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const pct = ((e.clientX - rect.left) / rect.width) * 100;
      const clamped = Math.min(maxLeftWidth, Math.max(minLeftWidth, pct));
      setLeftWidth(clamped);
      if (collapsed) setCollapsed(false);
    },
    [collapsed, minLeftWidth, maxLeftWidth]
  );

  const stopDragging = useCallback(() => {
    draggingRef.current = false;
    document.body.classList.remove("resizable-split--dragging");
  }, []);

  useEffect(() => {
    window.addEventListener("pointermove", onPointerMove);
    window.addEventListener("pointerup", stopDragging);
    return () => {
      window.removeEventListener("pointermove", onPointerMove);
      window.removeEventListener("pointerup", stopDragging);
    };
  }, [onPointerMove, stopDragging]);

  const startDragging = (e) => {
    e.preventDefault();
    draggingRef.current = true;
    document.body.classList.add("resizable-split--dragging");
  };

  const toggleCollapsed = () => setCollapsed((prev) => !prev);

  const effectiveLeftWidth = collapsed ? collapsedWidth : leftWidth;

  return (
    <div className="resizable-split" ref={containerRef}>
      <div
        className="resizable-split__pane resizable-split__pane--left"
        style={{ width: `${effectiveLeftWidth}%`, minWidth: collapsed ? 0 : undefined }}
        aria-hidden={collapsed}
      >
        {!collapsed && left}
      </div>

      <div className="resizable-split__handle-wrap">
        <button
          type="button"
          className="resizable-split__collapse-btn"
          onClick={toggleCollapsed}
          title={collapsed ? "Expand panel" : "Collapse panel"}
          aria-label={collapsed ? "Expand interaction panel" : "Collapse interaction panel"}
        >
          {collapsed ? "›" : "‹"}
        </button>
        <div
          className="resizable-split__handle"
          onPointerDown={startDragging}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panels"
        />
      </div>

      <div className="resizable-split__pane resizable-split__pane--right">{right}</div>
    </div>
  );
}
