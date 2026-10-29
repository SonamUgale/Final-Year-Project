import React, { useState } from "react";
import { StatCard } from "../components/StatCard";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import { ModeBadge } from "../components/ModeBadge";
import { EmptyState } from "../components/EmptyState";

export function DashboardPage({
  history = [],
  onStartScan,
  onNavigate,
  onSelectScan,
  loading = false,
  modelInfo = null,
}) {
  const [quickUrl, setQuickUrl] = useState("");
  const [urlError, setUrlError] = useState("");

  const handleQuickSubmit = (e) => {
    e.preventDefault();
    setUrlError("");
    const trimmed = quickUrl.trim();
    if (!trimmed) {
      setUrlError("Please enter a website URL.");
      return;
    }
    try {
      const parsed = new URL(trimmed);
      if (!["http:", "https:"].includes(parsed.protocol)) {
        throw new Error();
      }
    } catch {
      setUrlError("Please enter a valid URL, e.g. https://example.com");
      return;
    }
    onStartScan(trimmed);
  };

  // Derive real statistics from scan history
  const totalScans = history.length;
  const totalPatterns = history.reduce((sum, h) => sum + (h.total_dark_patterns || 0), 0);
  const highRiskCount = history.filter((h) => {
    const lvl = String(h.dark_risk_level || "").toLowerCase();
    return lvl === "high" || lvl === "very high" || lvl === "critical" || (h.dark_risk_score && h.dark_risk_score >= 60);
  }).length;
  const reportsCount = history.filter((h) => h.scan_status === "complete" || h.scan_status === "blocked").length;

  const recentScans = history.slice(0, 5);

  return (
    <div className="page-container dashboard-page">
      {/* 1. HERO SECTION */}
      <section className="dashboard-hero">
        <div className="hero-content">
          <div className="hero-badge">
            <span className="live-pulse-dot"></span>
            <span>Next-Gen Interface Integrity Scanner</span>
          </div>
          <h1 className="hero-heading">Detect Dark Patterns with AI</h1>
          <p className="hero-subtitle">
            Analyze websites for deceptive interface patterns using machine learning,
            rule-based heuristics, and visual intelligence.
          </p>
          <div className="hero-ctas-row">
            <button
              type="button"
              className="btn-hero-primary"
              onClick={() => onNavigate("scan")}
            >
              <span>🔍 Scan a Website</span>
            </button>
            <button
              type="button"
              className="btn-hero-secondary"
              onClick={() => onNavigate("capture")}
            >
              <span>🌐 Browser Capture</span>
            </button>
          </div>
          <p className="hero-footnote">
            Paste a public URL or analyze a page currently open in your browser.
          </p>
        </div>
      </section>

      {/* 2. QUICK URL SCAN CARD */}
      <section className="card quick-scan-card">
        <div className="quick-scan-header">
          <h3>Scan a Website</h3>
          <span className="quick-scan-hint">Instant automated Playwright crawl & multi-engine audit</span>
        </div>

        <form onSubmit={handleQuickSubmit} className="quick-scan-form">
          <div className="quick-input-group">
            <span className="quick-input-icon">🔗</span>
            <input
              type="text"
              className={`quick-url-input ${urlError ? "has-error" : ""}`}
              placeholder="https://example.com"
              value={quickUrl}
              onChange={(e) => {
                setQuickUrl(e.target.value);
                if (urlError) setUrlError("");
              }}
              disabled={loading}
            />
            <button
              type="submit"
              className="btn-quick-submit"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-sm"></span>
                  <span>Scanning...</span>
                </>
              ) : (
                <span>🔍 Analyze Website</span>
              )}
            </button>
          </div>
          {urlError && <div className="quick-scan-error">⚠️ {urlError}</div>}
        </form>

        <div className="quick-scan-footer">
          <div className="supported-tags-list">
            <span className="supported-label">Engines:</span>
            <span className="tag-chip">HTML/DOM Analysis</span>
            <span className="tag-chip">Calibrated Linear SVM V2 ({modelInfo?.accuracy_display || "96.89%"} Acc)</span>
            <span className="tag-chip">12 Rule Heuristics</span>
            <span className="tag-chip">Screenshot Vision AI</span>
          </div>
          <span className="blocked-reminder-text">
            Protected by Cloudflare/Akamai? Use <a href="#capture" onClick={(e) => { e.preventDefault(); onNavigate("capture"); }}>Browser Capture Mode</a>.
          </span>
        </div>
      </section>

      {/* AI ENGINE & MODEL METADATA BANNER */}
      <div className="card model-engine-badge-card" style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", marginBottom: "20px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <span style={{ fontSize: "22px" }}>🧠</span>
          <div>
            <strong style={{ fontSize: "13px", color: "#0f172a" }}>
              Active AI Classifier: {modelInfo?.model_name || "Calibrated Linear SVM V2"}
            </strong>
            <span style={{ display: "block", fontSize: "12px", color: "#64748b" }}>
              Two-stage classification with calibrated probability inference and multi-factor deceptive risk weighting.
            </span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
          <div style={{ textAlign: "right" }}>
            <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase", color: "#64748b", fontWeight: "600" }}>Test Accuracy</span>
            <strong style={{ fontSize: "14px", color: "#059669" }}>{modelInfo?.accuracy_display || "96.89%"}</strong>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase", color: "#64748b", fontWeight: "600" }}>Precision</span>
            <strong style={{ fontSize: "14px", color: "#0284c7" }}>{modelInfo?.precision_display || "96.72%"}</strong>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase", color: "#64748b", fontWeight: "600" }}>Recall</span>
            <strong style={{ fontSize: "14px", color: "#6366f1" }}>{modelInfo?.recall_display || "97.10%"}</strong>
          </div>
          <div style={{ textAlign: "right" }}>
            <span style={{ display: "block", fontSize: "11px", textTransform: "uppercase", color: "#64748b", fontWeight: "600" }}>F1-Score</span>
            <strong style={{ fontSize: "14px", color: "#7c3aed" }}>{modelInfo?.f1_display || modelInfo?.f1_score || "0.9691"}</strong>
          </div>
        </div>
      </div>

      {/* 3. METRIC STATISTICS CARDS */}
      <section className="dashboard-stats-grid">
        <StatCard
          icon="📊"
          value={totalScans}
          label="Total Scans Executed"
          subtext={totalScans === 0 ? "No scans yet" : `${totalScans} total audits`}
          color="blue"
        />
        <StatCard
          icon="🎯"
          value={totalPatterns}
          label="Deceptive Patterns Found"
          subtext={totalPatterns === 0 ? "0 findings" : "Corroborated by AI"}
          color="rose"
        />
        <StatCard
          icon="⚡"
          value={highRiskCount}
          label="High-Risk Websites"
          subtext={highRiskCount === 0 ? "0 high risk" : "Risk score ≥ 60"}
          color="amber"
        />
        <StatCard
          icon="📄"
          value={reportsCount}
          label="Reports Generated"
          subtext={reportsCount === 0 ? "0 reports" : "PDF ready"}
          color="emerald"
        />
      </section>

      {/* 4. RECENT SCANS TABLE */}
      <section className="card recent-scans-card">
        <div className="card-header-row">
          <div>
            <h3>Recent Website Audits</h3>
            <span className="card-header-sub">Latest scans evaluated across Playwright and Browser Capture</span>
          </div>
          {history.length > 5 && (
            <button
              type="button"
              className="btn-view-all-history"
              onClick={() => onNavigate("history")}
            >
              View All ({history.length}) →
            </button>
          )}
        </div>

        {recentScans.length === 0 ? (
          <EmptyState
            icon="🌐"
            title="No Scans Performed Yet"
            message="Enter a website URL above to execute your first automated deception audit."
            actionLabel="Start Your First Scan"
            onAction={() => onNavigate("scan")}
          />
        ) : (
          <div className="table-responsive-wrapper">
            <table className="recent-scans-table">
              <thead>
                <tr>
                  <th>Website / Domain</th>
                  <th>Scan Mode</th>
                  <th>Deceptive Risk</th>
                  <th>Patterns</th>
                  <th>Status</th>
                  <th>Date & Time</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recentScans.map((item) => (
                  <tr key={item.scan_id} className="scan-table-row">
                    <td className="cell-website">
                      <strong className="website-row-url" title={item.url}>
                        {item.url}
                      </strong>
                      <span className="website-row-title">{item.title || "Untitled Webpage"}</span>
                    </td>
                    <td>
                      <ModeBadge mode={item.scan_mode} />
                    </td>
                    <td>
                      {item.scan_status === "blocked" || item.scan_status === "partial" || item.dark_risk_score === null ? (
                        <RiskBadge level="Withheld" size="small" />
                      ) : (
                        <RiskBadge level={item.dark_risk_level || "None"} size="small" />
                      )}
                    </td>
                    <td className="cell-patterns">
                      <strong>{item.total_dark_patterns ?? 0}</strong>
                    </td>
                    <td>
                      <StatusBadge status={item.scan_status} />
                    </td>
                    <td className="cell-date">
                      {item.timestamp
                        ? new Date(item.timestamp).toLocaleDateString(undefined, {
                            month: "short",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "Recent"}
                    </td>
                    <td className="cell-action">
                      <button
                        type="button"
                        className="btn-table-view"
                        onClick={() => onSelectScan(item.scan_id)}
                      >
                        View Report →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
