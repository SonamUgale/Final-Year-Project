import React from "react";

export function ModeBadge({ mode = "automatic" }) {
  const norm = String(mode || "automatic").toLowerCase();
  const isCapture = norm === "browser_capture" || norm === "capture";
  const isWholeWebsite = norm === "whole_website" || norm === "website";

  if (isWholeWebsite) {
    return (
      <span className="mode-badge-component mode-whole-website" style={{ backgroundColor: "#f3e8ff", color: "#7e22ce", border: "1px solid #d8b4fe" }}>
        <span className="mode-badge-icon">🕸️</span>
        <span className="mode-badge-text">Whole Website</span>
      </span>
    );
  }

  return (
    <span className={`mode-badge-component ${isCapture ? "mode-browser-capture" : "mode-automated"}`}>
      <span className="mode-badge-icon">{isCapture ? "🌐" : "🤖"}</span>
      <span className="mode-badge-text">{isCapture ? "Browser Capture" : "Single Page"}</span>
    </span>
  );
}
