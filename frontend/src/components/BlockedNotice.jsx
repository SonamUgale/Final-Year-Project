import React from "react";

export function BlockedNotice({
  provider = "Security Firewall",
  reason,
  url,
  onSwitchToCapture,
  onRetry,
  onExportPdf,
}) {
  return (
    <div className="blocked-notice-card">
      <div className="blocked-notice-header">
        <div className="blocked-shield-badge">🛡️</div>
        <div className="blocked-header-text">
          <span className="blocked-eyebrow">AUTOMATED SCAN BLOCKED</span>
          <h3 className="blocked-title">Anti-Bot Security Challenge Encountered</h3>
          <p className="blocked-subtitle">
            The target website's security controls denied automated crawler access via{" "}
            <strong>{provider}</strong> ({reason || "HTTP 403 Forbidden"}).
          </p>
        </div>
      </div>

      <div className="blocked-policy-box">
        <strong>🔒 DarkShield Scientific Integrity & Anti-Hallucination Policy:</strong>
        <p>
          DarkShield never evaluates deceptive pattern scores on error pages or challenge
          interstitials, and never assigns an unearned clean rating when target content is
          inaccessible. Deceptive risk scoring is strictly <strong>WITHHELD (N/A)</strong>.
        </p>
        <div className="blocked-chips-row">
          <span className="chip-blocked">Status: <strong>BLOCKED</strong></span>
          <span className="chip-blocked">Provider: <strong>{provider}</strong></span>
          <span className="chip-blocked">Risk Score: <strong>N/A (Withheld)</strong></span>
          <span className="chip-blocked">Security Score: <strong>N/A</strong></span>
        </div>
      </div>

      <div className="blocked-actions-row">
        <button
          type="button"
          className="btn-primary-capture"
          onClick={onSwitchToCapture}
        >
          <span>🌐 Open Browser Capture Mode</span>
        </button>
        {onRetry && (
          <button
            type="button"
            className="btn-secondary-action"
            onClick={onRetry}
          >
            <span>🔄 Try Again</span>
          </button>
        )}
        {onExportPdf && (
          <button
            type="button"
            className="btn-secondary-action"
            onClick={onExportPdf}
          >
            <span>📄 Export Blocked Scan Report</span>
          </button>
        )}
      </div>

      <div className="blocked-footer-note">
        <span>💡 <em>Blocked ≠ Safe. Blocked ≠ Dark Pattern Detected.</em> Inspect the live page using our Chrome Extension.</span>
      </div>
    </div>
  );
}
