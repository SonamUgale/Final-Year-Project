import React from "react";

export function RiskBadge({ level = "None", size = "normal" }) {
  const norm = String(level || "None").toLowerCase().replace(/\s+/g, "-");

  const config = {
    none: { label: "Clean / None", icon: "✓", cls: "risk-clean" },
    clean: { label: "Clean", icon: "✓", cls: "risk-clean" },
    low: { label: "Low Risk", icon: "ℹ", cls: "risk-low" },
    medium: { label: "Medium Risk", icon: "⚠", cls: "risk-medium" },
    high: { label: "High Risk", icon: "⚡", cls: "risk-high" },
    "very-high": { label: "Very High Risk", icon: "🛑", cls: "risk-critical" },
    critical: { label: "Critical Risk", icon: "🛑", cls: "risk-critical" },
    withheld: { label: "Withheld", icon: "🔒", cls: "risk-withheld" },
    "not-assessed": { label: "Not Assessed", icon: "🔒", cls: "risk-withheld" },
    "not-assessed-(incomplete-capture)": { label: "Withheld", icon: "🔒", cls: "risk-withheld" },
  };

  const item = config[norm] || { label: level, icon: "•", cls: "risk-none" };

  return (
    <span className={`risk-badge-component ${item.cls} size-${size}`}>
      <span className="risk-badge-icon">{item.icon}</span>
      <span className="risk-badge-label">{item.label}</span>
    </span>
  );
}
