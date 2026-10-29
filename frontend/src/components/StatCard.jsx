import React from "react";

export function StatCard({ icon, value, label, subtext, color = "primary" }) {
  return (
    <div className={`stat-card-component stat-color-${color}`}>
      <div className="stat-card-top">
        <span className="stat-card-icon">{icon}</span>
        {subtext && <span className="stat-card-subtext">{subtext}</span>}
      </div>
      <div className="stat-card-body">
        <span className="stat-card-value">{value}</span>
        <span className="stat-card-label">{label}</span>
      </div>
    </div>
  );
}
