import React, { useState } from "react";

export function BrowserCapturePage({
  captureUrl,
  setCaptureUrl,
  captureTitle,
  setCaptureTitle,
  captureHtml,
  setCaptureHtml,
  captureScreenshot,
  setCaptureScreenshot,
  onCaptureScan,
  onCopyBookmarklet,
  copiedBookmarklet = false,
  loading = false,
  error = "",
}) {
  const [copiedPath, setCopiedPath] = useState(false);
  const extensionPath = "D:\\VSCode\\final_year_project\\Final-Year-Project\\browser_extension";

  const handleCopyPath = async () => {
    try {
      await navigator.clipboard.writeText(extensionPath);
      setCopiedPath(true);
      setTimeout(() => setCopiedPath(false), 2500);
    } catch {
      // ignore
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onCaptureScan();
  };

  return (
    <div className="page-container capture-page">
      {/* 1. HEADER */}
      <div className="page-header-box">
        <h2>Browser Capture</h2>
        <p className="page-header-sub">
          Analyze webpages directly from your browser when automated scanning is restricted by anti-bot firewalls.
        </p>
      </div>

      {/* 2. THREE-STEP VISUAL GUIDE */}
      <section className="capture-workflow-cards-grid">
        <div className="workflow-card">
          <span className="workflow-card-num">01</span>
          <h4>Open Website in Chrome</h4>
          <p>Navigate to the target website normally in your browser (e.g. Meesho, Amazon, or a login portal).</p>
        </div>

        <div className="workflow-card">
          <span className="workflow-card-num">02</span>
          <h4>Activate Extension</h4>
          <p>Click the DarkShield AI shield icon in your Chrome toolbar to open the inspection popup.</p>
        </div>

        <div className="workflow-card">
          <span className="workflow-card-num">03</span>
          <h4>Analyze Rendered Page</h4>
          <p>Click "Analyze Current Page". The extension transmits DOM and visual signals directly to DarkShield.</p>
        </div>
      </section>

      {/* 3. EXTENSION INSTALLATION & SETUP CARD */}
      <section className="card extension-setup-card">
        <div className="extension-setup-header">
          <div className="ext-brand-wrap">
            <span className="ext-icon">🛡️</span>
            <div>
              <h3>DarkShield Chrome Extension (Manifest V3)</h3>
              <span className="ext-sub">Zero Evasion • Full Privacy • Direct DOM Extraction</span>
            </div>
          </div>
          <span className="ext-status-pill">Ready to Load</span>
        </div>

        <div className="extension-steps-box">
          <div className="steps-title">
            <strong>How to Load the Extension in Google Chrome:</strong>
          </div>
          <ol className="ext-instructions-list">
            <li>
              Open <code>chrome://extensions/</code> in your Chrome address bar.
            </li>
            <li>
              Enable the <strong>Developer mode</strong> toggle switch in the top-right corner.
            </li>
            <li>
              Click the <strong>Load unpacked</strong> button in the top-left corner.
            </li>
            <li>
              Select the extension folder on your computer:
              <div className="copy-path-box">
                <code>{extensionPath}</code>
                <button
                  type="button"
                  className="btn-copy-path"
                  onClick={handleCopyPath}
                >
                  {copiedPath ? "✓ Copied!" : "📋 Copy Path"}
                </button>
              </div>
            </li>
          </ol>
        </div>
      </section>

      {/* 4. MANUAL CAPTURE FALLBACK FORM */}
      <section className="card manual-capture-card">
        <div className="manual-card-header">
          <div>
            <h3>Manual DOM & Bookmarklet Submission</h3>
            <span className="manual-card-sub">
              If running in an environment without Chrome extensions, submit rendered page HTML directly.
            </span>
          </div>
          <button
            type="button"
            className="btn-bookmarklet"
            onClick={onCopyBookmarklet}
          >
            {copiedBookmarklet ? "✓ Bookmarklet Copied!" : "📋 Copy 1-Click Bookmarklet"}
          </button>
        </div>

        <form onSubmit={handleSubmit} className="manual-capture-form">
          <div className="form-group-row">
            <div className="form-field-half">
              <label htmlFor="cap-url">Target Webpage URL *</label>
              <input
                id="cap-url"
                type="text"
                placeholder="https://www.meesho.com"
                value={captureUrl}
                onChange={(e) => setCaptureUrl(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="form-field-half">
              <label htmlFor="cap-title">Page Title (Optional)</label>
              <input
                id="cap-title"
                type="text"
                placeholder="Meesho Online Shopping"
                value={captureTitle}
                onChange={(e) => setCaptureTitle(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <div className="form-field-full">
            <label htmlFor="cap-html">Rendered Page OuterHTML / DOM Text *</label>
            <textarea
              id="cap-html"
              rows={6}
              placeholder="Paste rendered page HTML (e.g. from Chrome DevTools -> Elements -> Copy OuterHTML, or run the bookmarklet)..."
              value={captureHtml}
              onChange={(e) => setCaptureHtml(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="form-field-full">
            <label htmlFor="cap-screen">Screenshot Base64 (Optional for Multi-Modal Vision AI)</label>
            <input
              id="cap-screen"
              type="text"
              placeholder="data:image/jpeg;base64,... or raw base64 string"
              value={captureScreenshot}
              onChange={(e) => setCaptureScreenshot(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && (
            <div className="manual-error-alert">
              ⚠️ {error}
            </div>
          )}

          <div className="manual-form-actions">
            <button
              type="submit"
              className="btn-submit-capture"
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-sm"></span>
                  <span>Analyzing Captured Browser DOM...</span>
                </>
              ) : (
                <span>🔍 Run Dark Pattern Analysis on Captured DOM</span>
              )}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
