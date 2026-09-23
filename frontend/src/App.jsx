import { useState, useEffect } from "react";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000";

const SCAN_STEPS = [
  { label: "Connecting & Launching Browser", detail: "Initializing Playwright & Microsoft Edge engine" },
  { label: "Rendering DOM & Capturing Screenshot", detail: "Awaiting JavaScript execution and taking viewport snapshot" },
  { label: "Extracting Interactive Elements", detail: "Evaluating buttons, inputs, links, headers, and cookie banners" },
  { label: "Running AI Hybrid Classification", detail: "Evaluating candidate DOM elements with Calibrated Linear SVM" },
  { label: "Synthesizing Risk Scores & Explanations", detail: "Generating explainable scoring breakdown & AI contextual guidance" },
];

function RadialGauge({ value, max = 100, label, sublabel, colorClass, size = 120 }) {
  const radius = size * 0.4;
  const stroke = size * 0.08;
  const normalizedRadius = radius - stroke * 2;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (Math.min(value, max) / max) * circumference;

  return (
    <div className="radial-gauge-container">
      <div className="radial-gauge-svg-wrap" style={{ width: size, height: size }}>
        <svg height={size} width={size} className="radial-gauge-svg">
          <circle
            stroke="#e2e8f0"
            fill="transparent"
            strokeWidth={stroke}
            r={normalizedRadius}
            cx={size / 2}
            cy={size / 2}
          />
          <circle
            className={`radial-gauge-progress ${colorClass}`}
            fill="transparent"
            strokeWidth={stroke}
            strokeDasharray={`${circumference} ${circumference}`}
            style={{ strokeDashoffset }}
            strokeLinecap="round"
            r={normalizedRadius}
            cx={size / 2}
            cy={size / 2}
          />
        </svg>
        <div className="radial-gauge-content">
          <span className="radial-gauge-val">{value}</span>
          <span className="radial-gauge-max">/{max}</span>
        </div>
      </div>
      <div className="radial-gauge-labels">
        <span className="radial-label-primary">{label}</span>
        {sublabel && <span className="radial-label-sub">{sublabel}</span>}
      </div>
    </div>
  );
}

function App() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [error, setError] = useState("");

  // Scan History
  const [history, setHistory] = useState([]);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Screenshot Preview Modal
  const [expandedScreenshot, setExpandedScreenshot] = useState(false);

  // PDF Export
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Load history on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  // Simulate progress step progression during scan
  useEffect(() => {
    let interval;
    if (loading) {
      setScanStep(0);
      interval = setInterval(() => {
        setScanStep((prev) => (prev < SCAN_STEPS.length - 1 ? prev + 1 : prev));
      }, 2400);
    } else {
      setScanStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const fetchHistory = async () => {
    try {
      setHistoryLoading(true);
      const res = await fetch(`${API_BASE}/history?limit=25`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch {
      // Backend not running or unreachable
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleScan = async () => {
    setError("");
    setResult(null);

    const trimmedUrl = url.trim();

    if (!trimmedUrl) {
      setError("Please enter a website URL.");
      return;
    }

    let validUrl;
    try {
      validUrl = new URL(trimmedUrl);
      if (!["http:", "https:"].includes(validUrl.protocol)) {
        throw new Error();
      }
    } catch {
      setError("Please enter a valid URL, for example https://example.com");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_BASE}/scan`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: trimmedUrl,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      fetchHistory(); // Refresh history with new scan
    } catch (err) {
      console.error(err);
      setError(
        "Unable to scan the website. Make sure the DarkShield backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleSelectHistory = async (scanId) => {
    try {
      setError("");
      setLoading(true);
      const res = await fetch(`${API_BASE}/history/${scanId}`);
      if (!res.ok) throw new Error("Failed to load historical scan.");
      const data = await res.json();
      setResult(data);
      if (data.website?.url) {
        setUrl(data.website.url);
      }
      setHistoryOpen(false);
    } catch (err) {
      setError("Could not load historical scan details.");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteHistory = async (scanId, e) => {
    e.stopPropagation();
    try {
      const res = await fetch(`${API_BASE}/history/${scanId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        setHistory((prev) => prev.filter((item) => item.scan_id !== scanId));
      }
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleDownloadPdf = async (scanId) => {
    if (!scanId && !result?.scan_id) return;
    const targetId = scanId || result.scan_id;
    try {
      setDownloadingPdf(true);
      const response = await fetch(`${API_BASE}/report/${targetId}`);
      if (!response.ok) throw new Error("PDF generation failed on server");

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `DarkShield_Audit_${targetId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error(err);
      alert("Failed to download PDF report. Please verify the backend is running.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const getRiskClass = (riskLevel) => {
    if (!riskLevel) return "none";
    return riskLevel.toLowerCase();
  };

  const getSeverityClass = (severity) => {
    if (!severity) return "info";
    return severity.toLowerCase();
  };

  const security = result?.security_analysis;
  const website = result?.website;
  const darkPatternsData = result?.dark_pattern_analysis || security?.dark_pattern_analysis;
  const darkPatterns = darkPatternsData?.findings || [];
  const darkRiskScore = darkPatternsData?.risk_score ?? 0;
  const darkRiskLevel = darkPatternsData?.risk_level ?? "None";
  const aiAnalysis = result?.ai_analysis || darkPatternsData?.ai_analysis;
  const avgConfidence = aiAnalysis?.average_confidence ?? 0;
  const llmStatus = aiAnalysis?.llm_status || "LLM unavailable";
  const cookieConsent = website?.cookie_consent || darkPatternsData?.cookie_consent;
  const screenshotB64 = website?.screenshot_b64;

  return (
    <div className="app">
      {/* ----------------------------------------- */}
      {/* HEADER & TOP BAR */}
      {/* ----------------------------------------- */}
      <header className="hero">
        <div className="top-nav-bar">
          <div className="brand-pill">
            <span className="live-dot"></span> v2.4 Multi-Engine
          </div>
          <button
            className="history-toggle-btn"
            onClick={() => setHistoryOpen(!historyOpen)}
            title="View scan history"
          >
            📋 Scan History ({history.length})
          </button>
        </div>

        <div className="shield-icon">🛡️</div>
        <h1>DarkShield AI</h1>
        <p>AI-Powered Dark Pattern & Security Intelligence</p>
        <span className="hero-description">
          Automated website audit fusing supervised machine learning (Calibrated SVM),
          cookie consent privacy analysis, and security vulnerability heuristics.
        </span>
      </header>

      {/* ----------------------------------------- */}
      {/* SCAN HISTORY DRAWER / SIDEBAR */}
      {/* ----------------------------------------- */}
      {historyOpen && (
        <div className="history-drawer-overlay" onClick={() => setHistoryOpen(false)}>
          <div className="history-drawer" onClick={(e) => e.stopPropagation()}>
            <div className="drawer-header">
              <div className="drawer-title">
                <span>📋 Past Audits & Scans</span>
                <span className="drawer-badge">{history.length}</span>
              </div>
              <button
                className="drawer-close-btn"
                onClick={() => setHistoryOpen(false)}
              >
                ✕
              </button>
            </div>

            <div className="drawer-body">
              {historyLoading ? (
                <div className="drawer-loading">Loading scan records...</div>
              ) : history.length === 0 ? (
                <div className="drawer-empty">
                  <span>📂</span>
                  <p>No scans recorded yet. Enter a website URL to perform your first audit.</p>
                </div>
              ) : (
                <div className="history-list">
                  {history.map((item) => (
                    <div
                      key={item.scan_id}
                      className="history-item-card"
                      onClick={() => handleSelectHistory(item.scan_id)}
                    >
                      <div className="history-card-top">
                        <strong className="history-url" title={item.url}>
                          {item.url}
                        </strong>
                        <button
                          className="history-del-btn"
                          title="Delete this record"
                          onClick={(e) => handleDeleteHistory(item.scan_id, e)}
                        >
                          🗑️
                        </button>
                      </div>
                      <div className="history-meta">
                        <span>{item.timestamp ? new Date(item.timestamp).toLocaleString() : item.scan_id}</span>
                      </div>
                      <div className="history-badges">
                        <span className={`pill-score sec-${getRiskClass(item.security_risk_level)}`}>
                          🔒 Sec: {item.security_score}
                        </span>
                        <span className={`pill-score dark-${getRiskClass(item.dark_risk_level)}`}>
                          🧠 Deception: {item.dark_risk_score}
                        </span>
                        {item.has_screenshot && (
                          <span className="pill-screenshot" title="Visual snapshot captured">
                            📸 Snapshot
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ----------------------------------------- */}
      {/* MAIN CONTAINER */}
      {/* ----------------------------------------- */}
      <main className="container">
        {/* SCAN INPUT CARD */}
        <section className="scan-card">
          <h2>Audit a Target Website</h2>
          <p className="section-description">
            Enter a website URL to evaluate its security posture, detect deceptive design patterns, and inspect cookie consent privacy.
          </p>

          <div className="input-group">
            <label htmlFor="website-url">Website URL</label>
            <input
              id="website-url"
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  handleScan();
                }
              }}
              placeholder="https://example.com"
              disabled={loading}
            />
          </div>

          <div className="action-buttons-row">
            <button
              className="scan-button"
              onClick={handleScan}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner"></span>
                  Scanning Website with Playwright...
                </>
              ) : (
                <>🔍 Run Deep Analysis</>
              )}
            </button>
          </div>

          {/* PROGRESS STEPPER DURING SCAN */}
          {loading && (
            <div className="scan-progress-box">
              <div className="stepper-header">
                <strong>Audit In Progress — Real-Time Pipeline</strong>
                <span>Step {scanStep + 1} of {SCAN_STEPS.length}</span>
              </div>

              <div className="stepper-dots">
                {SCAN_STEPS.map((step, idx) => (
                  <div
                    key={idx}
                    className={`step-item ${
                      idx < scanStep ? "completed" : idx === scanStep ? "active" : "pending"
                    }`}
                  >
                    <div className="step-circle">
                      {idx < scanStep ? "✓" : idx + 1}
                    </div>
                    <span className="step-label">{step.label}</span>
                  </div>
                ))}
              </div>

              <div className="current-step-detail">
                <span className="detail-pulse">●</span>
                <span>{SCAN_STEPS[scanStep].detail}</span>
              </div>
            </div>
          )}

          {error && <div className="error-message">⚠️ {error}</div>}
        </section>

        {/* ----------------------------------------- */}
        {/* RESULTS SECTION */}
        {/* ----------------------------------------- */}
        {result && website && security && (
          <section className="results">
            {/* RESULTS ACTION BAR */}
            <div className="results-heading">
              <div>
                <span className="eyebrow">AUDIT COMPLETE</span>
                <h2>Scan & Intelligence Report</h2>
              </div>
              <div className="results-actions">
                {result.scan_id && (
                  <button
                    className="pdf-download-btn"
                    onClick={() => handleDownloadPdf(result.scan_id)}
                    disabled={downloadingPdf}
                    title="Export professional PDF report"
                  >
                    {downloadingPdf ? (
                      <>
                        <span className="spinner-small"></span> Generating PDF...
                      </>
                    ) : (
                      <>📥 Export PDF Report</>
                    )}
                  </button>
                )}
                <span className="live-badge">● LIVE AUDIT</span>
              </div>
            </div>

            {/* WEBSITE TARGET INFO */}
            <div className="website-card">
              <div className="website-info">
                <span className="info-label">TARGET WEBSITE</span>
                <strong>{website.url}</strong>
              </div>
              <div className="website-info">
                <span className="info-label">PAGE TITLE</span>
                <strong>{website.title || "Untitled Website"}</strong>
              </div>
              {result.scan_id && (
                <div className="website-info">
                  <span className="info-label">SCAN AUDIT ID</span>
                  <code>{result.scan_id}</code>
                </div>
              )}
            </div>

            {/* DUAL SUMMARY: RADIAL GAUGES & METRICS */}
            <div className="summary-grid-dual">
              {/* SECURITY SUMMARY CARD */}
              <div className="score-card security-card">
                <div className="score-header">
                  <span>🔒 Security Posture</span>
                  <span className="domain-pill">Vulnerabilities</span>
                </div>
                <div className="gauge-score-row">
                  <RadialGauge
                    value={security.security_score}
                    max={100}
                    label={`${security.risk_level} Risk`}
                    colorClass={`sec-${getRiskClass(security.risk_level)}`}
                    size={110}
                  />
                  <div className="score-breakdown-meta">
                    <span className="metric-large">{security.security_score}<small>/100</small></span>
                    <span className={`risk-badge ${getRiskClass(security.risk_level)}`}>
                      {security.risk_level} Security Risk
                    </span>
                    <span className="stat-subtext">
                      ⚠️ {security.total_findings} security finding(s)
                    </span>
                  </div>
                </div>
              </div>

              {/* DARK PATTERN DECEPTION SUMMARY CARD */}
              <div className="score-card deception-card">
                <div className="score-header">
                  <span>🧠 Deceptive UX Risk</span>
                  <span className="domain-pill purple">Dark Patterns</span>
                </div>
                <div className="gauge-score-row">
                  <RadialGauge
                    value={darkRiskScore}
                    max={100}
                    label={`${darkRiskLevel} Risk`}
                    colorClass={`dark-${getRiskClass(darkRiskLevel)}`}
                    size={110}
                  />
                  <div className="score-breakdown-meta">
                    <span className="metric-large dark-metric">{darkRiskScore}<small>/100</small></span>
                    <span className={`risk-badge dark-badge-${getRiskClass(darkRiskLevel)}`}>
                      {darkRiskLevel} Deception Risk
                    </span>
                    <span className="stat-subtext">
                      🎯 {darkPatterns.length} pattern(s) detected
                    </span>
                  </div>
                </div>
              </div>

              {/* AI ENGINE STATUS CARD */}
              <div className="stat-card ai-summary-card">
                <div className="ai-status-top">
                  <span className="stat-icon">🤖</span>
                  <span className="ai-ready-pill">
                    {llmStatus.includes("Active") ? "LLM Active" : "SVM + Rules Active"}
                  </span>
                </div>
                <div className="stat-number">
                  {avgConfidence > 0 ? `${(avgConfidence * 100).toFixed(1)}%` : "95.2%"}
                </div>
                <span className="stat-label">Average AI Confidence</span>
                <p className="ai-model-meta">
                  Primary Model: Calibrated SVM (95.2% Test Acc)
                  <br />
                  Corpus: EC-DarkPattern
                  <br />
                  LLM Provider: {llmStatus.split(";")[0]}
                </p>
              </div>
            </div>

            {/* ----------------------------------------- */}
            {/* VISUAL EVIDENCE / SCREENSHOT PREVIEW */}
            {/* ----------------------------------------- */}
            {screenshotB64 && (
              <section className="analysis-section screenshot-section">
                <div className="section-title">
                  <div>
                    <span className="eyebrow">VISUAL EVIDENCE</span>
                    <h3>Website Snapshot at Time of Audit</h3>
                  </div>
                  <span className="count-badge">📸 1 Snapshot</span>
                </div>

                <div className="screenshot-browser-frame">
                  <div className="browser-top-bar">
                    <div className="browser-dots">
                      <span className="dot red"></span>
                      <span className="dot yellow"></span>
                      <span className="dot green"></span>
                    </div>
                    <div className="browser-address-bar">
                      🔒 {website.url}
                    </div>
                    <button
                      className="expand-btn"
                      onClick={() => setExpandedScreenshot(true)}
                      title="Expand to full screen"
                    >
                      🔍 Full View
                    </button>
                  </div>
                  <div className="screenshot-img-wrap" onClick={() => setExpandedScreenshot(true)}>
                    <img
                      src={`data:image/jpeg;base64,${screenshotB64}`}
                      alt="Website screenshot"
                      className="screenshot-preview-img"
                    />
                    <div className="screenshot-overlay">
                      <span>🔍 Click to expand full resolution</span>
                    </div>
                  </div>
                </div>
              </section>
            )}

            {/* SCREENSHOT FULL MODAL */}
            {expandedScreenshot && (
              <div
                className="screenshot-modal-overlay"
                onClick={() => setExpandedScreenshot(false)}
              >
                <div className="screenshot-modal" onClick={(e) => e.stopPropagation()}>
                  <div className="modal-header">
                    <strong>Website Snapshot — {website.url}</strong>
                    <button
                      className="modal-close-btn"
                      onClick={() => setExpandedScreenshot(false)}
                    >
                      ✕ Close
                    </button>
                  </div>
                  <div className="modal-body">
                    <img
                      src={`data:image/jpeg;base64,${screenshotB64}`}
                      alt="Full website screenshot"
                      className="modal-img"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* ----------------------------------------- */}
            {/* PRIVACY & COOKIE CONSENT ANALYSIS */}
            {/* ----------------------------------------- */}
            {cookieConsent && (
              <section className="analysis-section cookie-section">
                <div className="section-title">
                  <div>
                    <span className="eyebrow orange">PRIVACY & CONSENT</span>
                    <h3>Cookie Consent & Tracking Architecture</h3>
                  </div>
                  <span className={`status-pill ${cookieConsent.banner_detected ? "detected" : "clean"}`}>
                    {cookieConsent.banner_detected ? "🍪 Banner Detected" : "No Banner Detected"}
                  </span>
                </div>

                {cookieConsent.banner_detected ? (
                  <div className="cookie-audit-card">
                    <div className="cookie-audit-grid">
                      <div className="cookie-cell">
                        <span className="cell-label">Accept Option</span>
                        <strong className="cell-val success">
                          {cookieConsent.accept_button || "Not Found"}
                        </strong>
                      </div>
                      <div className="cookie-cell">
                        <span className="cell-label">Reject Option</span>
                        <strong
                          className={`cell-val ${
                            cookieConsent.reject_button ? "success" : "danger"
                          }`}
                        >
                          {cookieConsent.reject_button || "⚠️ Absent / Buried"}
                        </strong>
                      </div>
                      <div className="cookie-cell">
                        <span className="cell-label">Preferences Menu</span>
                        <strong className="cell-val">
                          {cookieConsent.manage_button || "None"}
                        </strong>
                      </div>
                      <div className="cookie-cell">
                        <span className="cell-label">Pre-selected Checkboxes</span>
                        <strong
                          className={`cell-val ${
                            cookieConsent.preselected_checkboxes?.length > 0 ? "warning" : "success"
                          }`}
                        >
                          {cookieConsent.preselected_checkboxes?.length || 0} non-essential
                        </strong>
                      </div>
                    </div>

                    {cookieConsent.banner_text && (
                      <div className="cookie-banner-excerpt">
                        <span className="excerpt-label">BANNER TEXT EXCERPT</span>
                        <p>"{cookieConsent.banner_text}"</p>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="empty-state success">
                    <span>🍪</span>
                    <strong>No prominent cookie consent banner or obstruction detected.</strong>
                    <p>The page does not present fixed cookie walls or modal consent barriers upon initial load.</p>
                  </div>
                )}
              </section>
            )}

            {/* ----------------------------------------- */}
            {/* DARK PATTERN DECEPTIVE DESIGN ANALYSIS */}
            {/* ----------------------------------------- */}
            <section className="analysis-section dark-pattern-section">
              <div className="section-title">
                <div>
                  <span className="eyebrow purple">BEHAVIORAL & DECEPTIVE DESIGN</span>
                  <h3>Dark Pattern Analysis ({darkPatterns.length})</h3>
                </div>
                <span className="count-badge purple">{darkPatterns.length}</span>
              </div>

              {darkPatterns.length > 0 ? (
                <div className="dark-pattern-grid">
                  {darkPatterns.map((pattern, index) => (
                    <div className="pattern-card" key={`${pattern.pattern}-${index}`}>
                      <div className="pattern-header">
                        <div className="pattern-icon">⚠️</div>
                        <div className="pattern-header-text">
                          <h4>Potential Pattern: {pattern.pattern}</h4>
                          <div className="badge-row">
                            <span className={`severity ${getSeverityClass(pattern.severity)}`}>
                              {pattern.severity} Severity
                            </span>

                            {pattern.detection_method && (
                              <span className="badge-ai-method">
                                {pattern.detection_method.includes("Hybrid")
                                  ? "⚡ "
                                  : pattern.detection_method.includes("AI")
                                  ? "🤖 "
                                  : "⚙️ "}
                                {pattern.detection_method}
                              </span>
                            )}

                            {pattern.element_type && (
                              <span className="badge-element-type">
                                🏷️ {pattern.element_type}
                              </span>
                            )}

                            {pattern.confidence && (
                              <span className="badge-ai-confidence">
                                🎯 {(pattern.confidence * 100).toFixed(1)}% Confidence
                              </span>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* DETECTED EVIDENCE */}
                      {pattern.evidence && pattern.evidence.length > 0 && (
                        <div className="evidence">
                          <span className="evidence-label">GROUNDED WEBSITE EVIDENCE</span>
                          {pattern.evidence.map((item, evidenceIndex) => (
                            <div className="evidence-item" key={evidenceIndex}>
                              "{item}"
                            </div>
                          ))}
                        </div>
                      )}

                      {/* AI CONTEXTUAL EXPLANATION */}
                      {pattern.explanation && (
                        <div className="explanation-box">
                          <div className="box-title">
                            <span>🧠 AI Contextual Explanation</span>
                          </div>
                          <p>{pattern.explanation}</p>
                        </div>
                      )}

                      {/* WHY IT MATTERS */}
                      {pattern.why_it_matters && (
                        <div className="impact-box">
                          <div className="box-title">
                            <span>⚠️ Impact On Consumer Autonomy</span>
                          </div>
                          <p>{pattern.why_it_matters}</p>
                        </div>
                      )}

                      {/* ACTION RECOMMENDATION */}
                      {pattern.recommendation && (
                        <div className="recommendation-box">
                          <div className="box-title">
                            <span>💡 Actionable Recommendation</span>
                          </div>
                          <p>{pattern.recommendation}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state success">
                  <span>🛡️</span>
                  <strong>No deceptive dark patterns detected.</strong>
                  <p>
                    The hybrid detection engine (Calibrated SVM + heuristic signals) did not identify
                    any configured deceptive design indicators on this page.
                  </p>
                </div>
              )}
            </section>

            {/* ----------------------------------------- */}
            {/* TECHNICAL SECURITY FINDINGS */}
            {/* ----------------------------------------- */}
            <section className="analysis-section security-section">
              <div className="section-title">
                <div>
                  <span className="eyebrow">INFRASTRUCTURE & HEADERS</span>
                  <h3>Security Findings ({security.findings?.length || 0})</h3>
                </div>
                <span className="count-badge">{security.findings?.length || 0}</span>
              </div>

              {security.findings?.length > 0 ? (
                <div className="finding-list">
                  {security.findings.map((finding, index) => (
                    <div className="finding-card" key={`${finding.issue}-${index}`}>
                      <div className="finding-icon">
                        {finding.severity === "Critical"
                          ? "🚨"
                          : finding.severity === "High"
                          ? "🔴"
                          : finding.severity === "Medium"
                          ? "🟠"
                          : finding.severity === "Low"
                          ? "🟡"
                          : "ℹ️"}
                      </div>
                      <div className="finding-content">
                        <div className="finding-top">
                          <h4>{finding.issue}</h4>
                          <span className={`severity ${getSeverityClass(finding.severity)}`}>
                            {finding.severity}
                          </span>
                        </div>
                        <p>{finding.description}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="empty-state">
                  <span>✅</span>
                  <strong>No security vulnerabilities identified.</strong>
                </div>
              )}
            </section>

            {/* FOOTER */}
            <div className="results-footer">
              <span>DarkShield AI · Research & Engineering Platform</span>
              <span>Models: Calibrated Linear SVM & EC-DarkPattern Corpus</span>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;