import React from "react";

export function RadialGauge({
  value = 0,
  max = 100,
  label,
  sublabel,
  size = 140,
  strokeWidth = 10,
  variant = "deception",
}) {
  const safeVal = value === null || value === undefined ? 0 : Math.min(Math.max(0, value), max);
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (safeVal / max) * circumference;

  const getColorClass = () => {
    if (value === null) return "gauge-withheld";
    if (variant === "security") {
      if (safeVal >= 80) return "gauge-clean";
      if (safeVal >= 60) return "gauge-medium";
      return "gauge-high";
    }
    // Deception gauge
    if (safeVal === 0) return "gauge-clean";
    if (safeVal < 30) return "gauge-low";
    if (safeVal < 60) return "gauge-medium";
    if (safeVal < 80) return "gauge-high";
    return "gauge-critical";
  };

  return (
    <div className="radial-gauge-card" style={{ width: size, minWidth: size }}>
      <div className="radial-gauge-svg-wrap" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="radial-gauge-svg">
          {/* Background Track */}
          <circle
            className="gauge-track"
            strokeWidth={strokeWidth}
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
          {/* Active Fill */}
          <circle
            className={`gauge-progress ${getColorClass()}`}
            strokeWidth={strokeWidth}
            strokeDasharray={`${circumference} ${circumference}`}
            style={{ strokeDashoffset }}
            strokeLinecap="round"
            r={radius}
            cx={size / 2}
            cy={size / 2}
          />
        </svg>
        <div className="gauge-center-content">
          <span className="gauge-score-value">
            {value === null ? "N/A" : safeVal}
          </span>
          {value !== null && <span className="gauge-score-max">/{max}</span>}
        </div>
      </div>
      {(label || sublabel) && (
        <div className="gauge-labels-box">
          {label && <span className="gauge-label-primary">{label}</span>}
          {sublabel && <span className="gauge-label-secondary">{sublabel}</span>}
        </div>
      )}
    </div>
  );
}
