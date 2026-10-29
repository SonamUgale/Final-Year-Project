import React from "react";

export function StatusBadge({ status = "complete" }) {
  const norm = String(status || "").toLowerCase();

  if (norm === "blocked" || norm === "access_blocked") {
    return (
      <span className="status-badge-component status-blocked">
        <span className="status-dot"></span>
        <span>Blocked</span>
      </span>
    );
  }
  if (norm === "failed") {
    return (
      <span className="status-badge-component status-failed">
        <span className="status-dot"></span>
        <span>Failed</span>
      </span>
    );
  }
  if (norm === "partial") {
    return (
      <span className="status-badge-component status-partial">
        <span className="status-dot"></span>
        <span>Partial</span>
      </span>
    );
  }
  return (
    <span className="status-badge-component status-complete">
      <span className="status-dot"></span>
      <span>Completed</span>
    </span>
  );
}
