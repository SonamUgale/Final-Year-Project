import { useState } from "react";
import "./App.css";

function App() {
  const [url, setUrl] = useState("");
  const [scanning, setScanning] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  const handleScan = async () => {
    setError("");
    setResult(null);

    const trimmedUrl = url.trim();

    // Check empty URL
    if (!trimmedUrl) {
      setError("Please enter a website URL.");
      return;
    }

    // Validate URL
    let parsedUrl;

    try {
      parsedUrl = new URL(trimmedUrl);
    } catch {
      setError(
        "Please enter a valid URL, for example: https://example.com"
      );
      return;
    }

    // Only allow HTTP and HTTPS
    if (
      parsedUrl.protocol !== "http:" &&
      parsedUrl.protocol !== "https:"
    ) {
      setError("Only HTTP and HTTPS websites can be scanned.");
      return;
    }

    setScanning(true);

    try {
      /*
        Send the URL to the FastAPI backend.

        Backend:
        POST http://127.0.0.1:8000/scan
      */

      const response = await fetch(
        "http://127.0.0.1:8000/scan",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
          },

          body: JSON.stringify({
            url: parsedUrl.href,
          }),
        }
      );

      // Check HTTP response
      if (!response.ok) {
        throw new Error(
          `Server returned ${response.status}`
        );
      }

      // Convert response to JSON
      const data = await response.json();

      console.log("Backend response:", data);

      setResult(data);

    } catch (err) {
      console.error("Scan error:", err);

      setError(
        "Unable to scan this website. Make sure the FastAPI backend is running."
      );

    } finally {
      setScanning(false);
    }
  };

  const scanAnotherWebsite = () => {
    setResult(null);
    setUrl("");
    setError("");
  };

  /*
    The backend returns:

    {
      website: {...},
      security_analysis: {...}
    }

    These helpers make the frontend flexible if the
    analyzer returns slightly different structures.
  */

  const website = result?.website || {};
  const analysis = result?.security_analysis || {};

  // Try common field names for title
  const websiteTitle =
    website.title ||
    website.page_title ||
    website.name ||
    "Website";

  // Try common field names for URL
  const websiteUrl =
    website.url ||
    url;

  /*
    Patterns may come from the analyzer using different
    names. We handle the common possibilities.
  */

  let patterns = [];

  if (Array.isArray(analysis)) {
    patterns = analysis;
  } else if (Array.isArray(analysis.patterns)) {
    patterns = analysis.patterns;
  } else if (Array.isArray(analysis.detected_patterns)) {
    patterns = analysis.detected_patterns;
  }

  return (
    <div className="app">

      {/* HERO */}
      <header className="hero">

        <div className="shield">
          🛡️
        </div>

        <h1>
          DarkShield AI
        </h1>

        <p>
          AI-Powered Dark Pattern Detection
        </p>

      </header>

      <main className="container">

        {/* SCANNER */}
        <section className="scan-box">

          <label htmlFor="url">
            Enter Website URL
          </label>

          <div className="input-row">

            <input
              id="url"
              type="url"
              placeholder="https://example.com"
              value={url}
              disabled={scanning}
              onChange={(e) => {
                setUrl(e.target.value);
                setError("");
              }}
            />

            <button
              onClick={handleScan}
              disabled={scanning}
            >
              {scanning
                ? "Scanning..."
                : "Scan Website"}
            </button>

          </div>

          {/* ERROR */}
          {error && (
            <div className="error-message">
              <span>⚠️</span>

              <p>
                {error}
              </p>
            </div>
          )}

          {/* LOADING */}
          {scanning && (
            <div className="loading">

              <div className="loading-icon">
                🔍
              </div>

              <strong>
                Scanning website...
              </strong>

              <p>
                DarkShield is communicating with the
                website scanner.
              </p>

              <div className="progress-bar">
                <div className="progress-fill"></div>
              </div>

            </div>
          )}

        </section>

        {/* RESULTS */}
        {result && !scanning && (
          <section className="results">

            {/* HEADER */}
            <div className="results-header">

              <div>
                <h2>
                  Scan Results
                </h2>

                <p>
                  Website analysis completed.
                </p>
              </div>

              <div className="scan-status">
                ✓ Complete
              </div>

            </div>

            {/* WEBSITE INFORMATION */}
            <div className="website-info">

              <div className="info-item">

                <span>
                  Website
                </span>

                <strong>
                  {websiteUrl}
                </strong>

              </div>

              <div className="info-item">

                <span>
                  Page Title
                </span>

                <strong>
                  {websiteTitle}
                </strong>

              </div>

              <div className="info-item">

                <span>
                  Patterns Detected
                </span>

                <strong>
                  {patterns.length}
                </strong>

              </div>

            </div>

            {/* SECURITY SUMMARY */}
            <div className="security-summary">

              <div className="summary-heading">

                <h3>
                  Security Summary
                </h3>

                <p>
                  Results returned by the DarkShield
                  analysis engine.
                </p>

              </div>

              <div className="summary-total">

                <strong>
                  {patterns.length}
                </strong>

                <span>
                  Potential Patterns Found
                </span>

              </div>

            </div>

            {/* ANALYSIS */}
            <div className="analysis-heading">

              <h3>
                AI Analysis
              </h3>

              <p>
                DarkShield analyzed the website
                content for potential dark patterns.
              </p>

            </div>

            {/* PATTERNS */}
            {patterns.length > 0 ? (

              <div className="patterns">

                {patterns.map((pattern, index) => {

                  const type =
                    pattern.type ||
                    pattern.name ||
                    pattern.pattern ||
                    `Pattern ${index + 1}`;

                  const description =
                    pattern.description ||
                    pattern.reason ||
                    pattern.explanation ||
                    "Potential dark pattern detected.";

                  const severity =
                    pattern.severity ||
                    "Unknown";

                  const confidence =
                    pattern.confidence;

                  const evidence =
                    pattern.evidence ||
                    pattern.text;

                  return (
                    <div
                      className="pattern-card"
                      key={index}
                    >

                      <div className="pattern-top">

                        <div className="pattern-title">

                          <div className="pattern-icon">
                            ⚠️
                          </div>

                          <div>

                            <h4>
                              {type}
                            </h4>

                            <span
                              className={`severity ${String(
                                severity
                              ).toLowerCase()}`}
                            >
                              {severity} Severity
                            </span>

                          </div>

                        </div>

                        {confidence !== undefined && (
                          <div className="confidence">

                            <strong>
                              {confidence}%
                            </strong>

                            <span>
                              Confidence
                            </span>

                          </div>
                        )}

                      </div>

                      {evidence && (
                        <div className="evidence">

                          <span>
                            Detected Evidence
                          </span>

                          <p>
                            {evidence}
                          </p>

                        </div>
                      )}

                      <p className="pattern-description">
                        {description}
                      </p>

                    </div>
                  );
                })}

              </div>

            ) : (

              <div className="no-patterns">

                <div>
                  ✓
                </div>

                <h3>
                  No Dark Patterns Detected
                </h3>

                <p>
                  The current analysis did not identify
                  any potential dark patterns.
                </p>

              </div>

            )}

            {/* RAW ANALYSIS FALLBACK */}
            {!Array.isArray(analysis) &&
              patterns.length === 0 && (
                <div className="analysis-data">

                  <h4>
                    Analysis Result
                  </h4>

                  <pre>
                    {JSON.stringify(
                      analysis,
                      null,
                      2
                    )}
                  </pre>

                </div>
              )}

            {/* SCAN AGAIN */}
            <button
              className="scan-again"
              onClick={scanAnotherWebsite}
            >
              ↻ Scan Another Website
            </button>

          </section>
        )}

      </main>

      <footer>

        <p>
          DarkShield AI • Website Transparency &
          Dark Pattern Detection
        </p>

      </footer>

    </div>
  );
}

export default App;