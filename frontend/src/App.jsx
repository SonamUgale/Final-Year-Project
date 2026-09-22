import { useState } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

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
      const response = await fetch("http://127.0.0.1:8000/scan", {
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
    } catch (err) {
      console.error(err);

      setError(
        "Unable to scan the website. Make sure the DarkShield backend is running."
      );
    } finally {
      setLoading(false);
    }
  };

  const getRiskClass = (riskLevel) => {
    if (!riskLevel) return "";

    return riskLevel.toLowerCase();
  };

  const getSeverityClass = (severity) => {
    if (!severity) return "info";

    return severity.toLowerCase();
  };

  const security = result?.security_analysis;
  const website = result?.website;

  const darkPatterns = security?.dark_pattern_analysis?.findings || [];

  return (
    <div className="app">
      {/* ----------------------------------------- */}
      {/* HEADER */}
      {/* ----------------------------------------- */}

      <header className="hero">
        <div className="shield-icon">🛡️</div>

        <h1>DarkShield AI</h1>

        <p>
          AI-Powered Dark Pattern Detection
        </p>

        <span className="hero-description">
          Analyze websites for security risks and deceptive design patterns.
        </span>
      </header>

      <main className="container">

        {/* ----------------------------------------- */}
        {/* SCAN CARD */}
        {/* ----------------------------------------- */}

        <section className="scan-card">

          <h2>Scan a Website</h2>

          <p className="section-description">
            Enter a website URL to analyze its security and potential dark
            patterns.
          </p>

          <div className="input-group">

            <label htmlFor="website-url">
              Website URL
            </label>

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

          <button
            className="scan-button"
            onClick={handleScan}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Scanning Website...
              </>
            ) : (
              <>
                🔍 Scan Website
              </>
            )}
          </button>

          {loading && (
            <div className="loading-message">
              <strong>Analyzing website...</strong>
              <span>
                Playwright is collecting website information. This may take
                a few seconds.
              </span>
            </div>
          )}

          {error && (
            <div className="error-message">
              ⚠️ {error}
            </div>
          )}

        </section>


        {/* ----------------------------------------- */}
        {/* RESULTS */}
        {/* ----------------------------------------- */}

        {result && website && security && (

          <section className="results">

            <div className="results-heading">
              <div>
                <span className="eyebrow">
                  ANALYSIS COMPLETE
                </span>

                <h2>Scan Results</h2>
              </div>

              <span className="live-badge">
                ● LIVE SCAN
              </span>
            </div>


            {/* ----------------------------------------- */}
            {/* WEBSITE INFORMATION */}
            {/* ----------------------------------------- */}

            <div className="website-card">

              <div className="website-info">

                <span className="info-label">
                  WEBSITE
                </span>

                <strong>
                  {website.url}
                </strong>

              </div>

              <div className="website-info">

                <span className="info-label">
                  PAGE TITLE
                </span>

                <strong>
                  {website.title || "Untitled Website"}
                </strong>

              </div>

            </div>


            {/* ----------------------------------------- */}
            {/* SECURITY SUMMARY */}
            {/* ----------------------------------------- */}

            <div className="summary-grid">

              <div className="score-card">

                <div className="score-header">
                  <span>Security Score</span>
                  <span className="shield-small">🛡️</span>
                </div>

                <div
                  className={`score-number ${getRiskClass(
                    security.risk_level
                  )}`}
                >
                  {security.security_score}
                  <small>/100</small>
                </div>

                <div className="score-bar">
                  <div
                    className={`score-fill ${getRiskClass(
                      security.risk_level
                    )}`}
                    style={{
                      width: `${security.security_score}%`,
                    }}
                  ></div>
                </div>

                <div
                  className={`risk-badge ${getRiskClass(
                    security.risk_level
                  )}`}
                >
                  {security.risk_level} Risk
                </div>

              </div>


              <div className="stat-card">

                <span className="stat-icon">
                  ⚠️
                </span>

                <span className="stat-number">
                  {security.total_findings}
                </span>

                <span className="stat-label">
                  Security Findings
                </span>

              </div>


              <div className="stat-card">

                <span className="stat-icon">
                  🧠
                </span>

                <span className="stat-number">
                  {security.dark_pattern_analysis?.total_dark_patterns || 0}
                </span>

                <span className="stat-label">
                  Dark Patterns
                </span>

              </div>

            </div>


            {/* ----------------------------------------- */}
            {/* SECURITY FINDINGS */}
            {/* ----------------------------------------- */}

            <section className="analysis-section">

              <div className="section-title">

                <div>
                  <span className="eyebrow">
                    SECURITY
                  </span>

                  <h3>
                    Security Findings
                  </h3>
                </div>

                <span className="count-badge">
                  {security.findings?.length || 0}
                </span>

              </div>


              {security.findings?.length > 0 ? (

                <div className="finding-list">

                  {security.findings.map((finding, index) => (

                    <div
                      className="finding-card"
                      key={`${finding.issue}-${index}`}
                    >

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

                          <h4>
                            {finding.issue}
                          </h4>

                          <span
                            className={`severity ${getSeverityClass(
                              finding.severity
                            )}`}
                          >
                            {finding.severity}
                          </span>

                        </div>

                        <p>
                          {finding.description}
                        </p>

                      </div>

                    </div>

                  ))}

                </div>

              ) : (

                <div className="empty-state">
                  <span>✅</span>
                  <strong>No security findings detected.</strong>
                </div>

              )}

            </section>


            {/* ----------------------------------------- */}
            {/* DARK PATTERNS */}
            {/* ----------------------------------------- */}

            <section className="analysis-section">

              <div className="section-title">

                <div>
                  <span className="eyebrow">
                    DARK PATTERN DETECTION
                  </span>

                  <h3>
                    Potential Dark Patterns
                  </h3>
                </div>

                <span className="count-badge purple">
                  {darkPatterns.length}
                </span>

              </div>


              {darkPatterns.length > 0 ? (

                <div className="dark-pattern-grid">

                  {darkPatterns.map((pattern, index) => (

                    <div
                      className="pattern-card"
                      key={`${pattern.pattern}-${index}`}
                    >

                      <div className="pattern-header">

                        <div className="pattern-icon">
                          ⚠️
                        </div>

                        <div>

                          <h4>
                            {pattern.pattern}
                          </h4>

                          <span
                            className={`severity ${getSeverityClass(
                              pattern.severity
                            )}`}
                          >
                            {pattern.severity}
                          </span>

                        </div>

                      </div>

                      <p className="pattern-description">
                        {pattern.description}
                      </p>


                      {pattern.evidence &&
                        pattern.evidence.length > 0 && (

                          <div className="evidence">

                            <span className="evidence-label">
                              DETECTED EVIDENCE
                            </span>

                            {pattern.evidence.map(
                              (item, evidenceIndex) => (

                                <div
                                  className="evidence-item"
                                  key={evidenceIndex}
                                >
                                  "{item}"
                                </div>

                              )
                            )}

                          </div>

                        )}

                    </div>

                  ))}

                </div>

              ) : (

                <div className="empty-state success">
                  <span>🛡️</span>
                  <strong>
                    No known dark patterns detected.
                  </strong>

                  <p>
                    The current detection engine did not identify any
                    configured dark-pattern indicators.
                  </p>
                </div>

              )}

            </section>


            {/* ----------------------------------------- */}
            {/* WEBSITE STRUCTURE */}
            {/* ----------------------------------------- */}

            <section className="analysis-section">

              <div className="section-title">

                <div>
                  <span className="eyebrow">
                    WEBSITE STRUCTURE
                  </span>

                  <h3>
                    Extracted Elements
                  </h3>
                </div>

              </div>

              <div className="element-grid">

                <div className="element-stat">
                  <strong>
                    {website.links?.length || 0}
                  </strong>

                  <span>
                    Links
                  </span>
                </div>

                <div className="element-stat">
                  <strong>
                    {website.buttons?.length || 0}
                  </strong>

                  <span>
                    Buttons
                  </span>
                </div>

                <div className="element-stat">
                  <strong>
                    {website.inputs?.length || 0}
                  </strong>

                  <span>
                    Input Fields
                  </span>
                </div>

                <div className="element-stat">
                  <strong>
                    {Object.keys(website.headers || {}).length}
                  </strong>

                  <span>
                    HTTP Headers
                  </span>
                </div>

              </div>

            </section>


            {/* ----------------------------------------- */}
            {/* FOOTER */}
            {/* ----------------------------------------- */}

            <div className="results-footer">

              <span>
                DarkShield AI
              </span>

              <span>
                Security analysis powered by FastAPI + Playwright
              </span>

            </div>

          </section>

        )}

      </main>
    </div>
  );
}

export default App;