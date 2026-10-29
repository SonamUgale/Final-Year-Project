import React from "react";

export function EmptyState({ icon = "📂", title, message, actionLabel, onAction }) {
  return (
    <div className="empty-state-box">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-message">{message}</p>
      {actionLabel && onAction && (
        <button type="button" className="btn-empty-action" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}
