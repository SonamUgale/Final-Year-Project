import React, { useState } from "react";
import { RiskBadge } from "./RiskBadge";

export function FindingCard({ finding, index = 0, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);

  if (!finding) return null;

  const category = finding.pattern_category || finding.category || finding.pattern || "Deceptive Pattern";
  const severity = finding.severity || "Medium";
  const confidence = finding.confidence !== undefined ? Math.round(finding.confidence * 100) : 90;
  const method = finding.detection_method || "AI Model";

  // Evidence text extraction
  let evidenceList = [];
  if (Array.isArray(finding.evidence)) {
    evidenceList = finding.evidence.filter(Boolean);
  } else if (typeof finding.evidence === "string" && finding.evidence.trim()) {
    evidenceList = [finding.evidence.trim()];
  }
  if (finding.evidence_text && !evidenceList.includes(finding.evidence_text)) {
    evidenceList.unshift(finding.evidence_text);
  }
  if (evidenceList.length === 0 && finding.context) {
    evidenceList.push(finding.context);
  }

  const explanation =
    finding.explanation ||
    finding.description ||
    finding.details ||
    "This interface pattern leverages psychological nudges or visual asymmetry to steer user decisions.";

  const impact =
    finding.user_impact ||
    finding.impact ||
    "Users may be pressured into unwanted purchases, subscriptions, or premature commitments.";

  return (
    <div className={`finding-card-accordion ${open ? "is-open" : "is-collapsed"}`}>
      {/* Header bar */}
      <button
        type="button"
        className="finding-header-btn"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
      >
        <div className="finding-header-left">
          <span className="finding-index-num">#{index + 1}</span>
          <div className="finding-title-group">
            <h4 className="finding-category-name">{category}</h4>
            <span className="finding-method-pill">{method}</span>
          </div>
        </div>

        <div className="finding-header-right">
          <div className="finding-confidence-pill">
            <span className="conf-label">Confidence:</span>
            <strong>{confidence}%</strong>
          </div>
          <RiskBadge level={severity} size="small" />
          <span className="accordion-toggle-arrow">{open ? "▲" : "▼"}</span>
        </div>
      </button>

      {/* Accordion body */}
      {open && (
        <div className="finding-accordion-body">
          {/* Prominent Evidence Block */}
          {evidenceList.length > 0 && (
            <div className="finding-evidence-block">
              <div className="evidence-header-label">
                <span>💬 Verified Interface Evidence:</span>
                {finding.element_type && (
                  <span className="evidence-element-tag">&lt;{finding.element_type}&gt;</span>
                )}
              </div>
              <div className="evidence-quotes-container">
                {evidenceList.map((ev, i) => (
                  <blockquote key={i} className="evidence-quote-item">
                    "{ev}"
                  </blockquote>
                ))}
              </div>
            </div>
          )}

          {/* Explanation & Why it Matters */}
          <div className="finding-details-grid">
            <div className="detail-col">
              <span className="detail-col-title">Why This Matters:</span>
              <p className="detail-col-text">{explanation}</p>
            </div>
            <div className="detail-col">
              <span className="detail-col-title">User Impact & Behavioral Effect:</span>
              <p className="detail-col-text">{impact}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
