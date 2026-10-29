import React, { useState, useEffect, useRef } from "react";
import { RadialGauge } from "../components/RadialGauge";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import { ModeBadge } from "../components/ModeBadge";
import { FindingCard } from "../components/FindingCard";
import { BlockedNotice } from "../components/BlockedNotice";
import { LoadingStepper } from "../components/LoadingStepper";

function SnapshotEvidenceModal({ lightbox, onClose }) {
  const [loading, setLoading] = useState(Boolean(lightbox?.url));
  const [hasError, setHasError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  useEffect(() => {
    setLoading(Boolean(lightbox?.url));
    setHasError(false);
    setRetryCount(0);
  }, [lightbox?.url, lightbox?.pageId]);

  if (!lightbox) return null;

  const currentImgUrl = lightbox.url
    ? (lightbox.url.startsWith("data:")
        ? lightbox.url
        : `${lightbox.url}${lightbox.url.includes("?") ? "&" : "?"}_r=${retryCount}`)
    : null;

  const handleRetry = () => {
    setHasError(false);
    setLoading(true);
    setRetryCount((prev) => prev + 1);
  };

  const handleDownload = () => {
    if (!currentImgUrl) return;
    const a = document.createElement("a");
    a.href = currentImgUrl;
    a.download = `DarkShield_Snapshot_${lightbox.pageId || "page"}.jpg`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const handleOpenNewTab = () => {
    if (!currentImgUrl) return;
    window.open(currentImgUrl, "_blank", "noopener,noreferrer");
  };

  const isBlocked = lightbox.isBlocked || lightbox.status === "blocked";
  const hasImage = Boolean(currentImgUrl) && !hasError;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content snapshot-modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header snapshot-modal-header">
          <div className="snapshot-modal-title-col">
            <div className="snapshot-modal-title-row">
              <h4>Snapshot Evidence: {lightbox.title || lightbox.pageId || "Page Viewport"}</h4>
              <span className={`snapshot-status-pill status-${lightbox.status || "completed"}`}>
                {(lightbox.status || "completed").toUpperCase()}
              </span>
              {lightbox.riskScore !== null && lightbox.riskScore !== undefined ? (
                <span className="snapshot-risk-pill">
                  Risk: {lightbox.riskScore}/100 ({lightbox.riskLevel || "Assessed"})
                </span>
              ) : isBlocked ? (
                <span className="snapshot-risk-pill risk-withheld">Score Withheld</span>
              ) : null}
            </div>
            {lightbox.pageUrl && (
              <a
                href={lightbox.pageUrl}
                target="_blank"
                rel="noreferrer"
                className="snapshot-modal-url"
                title={lightbox.pageUrl}
              >
                🔗 {lightbox.pageUrl}
              </a>
            )}
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        {/* Modal Action Toolbar */}
        <div className="snapshot-modal-toolbar">
          <div className="snapshot-modal-toolbar-left">
            <span className="snapshot-toolbar-label">
              Page Identifier: <code>{lightbox.pageId}</code>
            </span>
          </div>
          <div className="snapshot-modal-toolbar-actions">
            {hasImage && !loading && (
              <>
                <button
                  type="button"
                  className="btn-toolbar-action"
                  onClick={handleOpenNewTab}
                  title="Open snapshot in full browser window"
                >
                  🔍 Open in New Tab
                </button>
                <button
                  type="button"
                  className="btn-toolbar-action"
                  onClick={handleDownload}
                  title="Download captured screenshot image"
                >
                  📥 Download Image
                </button>
              </>
            )}
            {lightbox.url && (
              <button
                type="button"
                className="btn-toolbar-action"
                onClick={handleRetry}
                title="Force reload snapshot from backend"
              >
                🔄 Refresh
              </button>
            )}
          </div>
        </div>

        {/* Modal Body */}
        <div className="modal-body snapshot-modal-body">
          {/* 1. Stored Image Rendering with Loading & Error States */}
          {lightbox.url && !hasError ? (
            <div className="snapshot-image-stage">
              {loading && (
                <div className="snapshot-loader-box">
                  <div className="snapshot-spinner"></div>
                  <p className="snapshot-loader-text">Retrieving stored viewport snapshot from backend...</p>
                </div>
              )}
              <img
                src={currentImgUrl}
                alt={lightbox.title || "Page viewport snapshot"}
                className="snapshot-full-image"
                style={{ display: loading ? "none" : "block" }}
                onLoad={() => setLoading(false)}
                onError={() => {
                  setLoading(false);
                  setHasError(true);
                }}
              />
            </div>
          ) : hasError ? (
            /* 2. Image Load Error Banner with Retry */
            <div className="snapshot-error-banner">
              <div className="snapshot-error-icon">⚠️</div>
              <div className="snapshot-error-content">
                <h5>Snapshot Image Failed to Load</h5>
                <p>
                  The stored snapshot could not be retrieved from <code>{lightbox.url}</code>. The image file may be
                  missing, corrupted, or network communication timed out.
                </p>
                <button type="button" className="btn-retry-load" onClick={handleRetry}>
                  🔄 Retry Loading Snapshot
                </button>
              </div>
            </div>
          ) : (
            /* 3. Snapshot Not Captured Notice (Never substitute live page / logo) */
            <div className="snapshot-unavailable-card">
              <div className="snapshot-unavailable-icon">{isBlocked ? "🔒" : "📄"}</div>
              <div className="snapshot-unavailable-body">
                <h5>
                  {isBlocked
                    ? "Viewport Snapshot Unavailable: Access Barrier Detected"
                    : lightbox.status === "timeout"
                    ? "Viewport Snapshot Unavailable: Navigation Timeout"
                    : lightbox.status === "failed"
                    ? "Viewport Snapshot Unavailable: Capture Failed"
                    : "Viewport Snapshot Not Captured"}
                </h5>
                <p>
                  {isBlocked
                    ? `This page was defended by an access control barrier (${lightbox.blockProvider || "Cloudflare / Bot Defense"}). Browser viewport rendering was halted, but all DOM telemetry and structural text were securely recorded below.`
                    : lightbox.status === "timeout"
                    ? "Page execution or hydration exceeded the crawler deadline. A visual snapshot was skipped to prevent the scan from stalling."
                    : lightbox.message || "A visual screenshot was not collected for this page during the crawl."}
                </p>
              </div>
            </div>
          )}

          {/* 4. Extracted DOM & Telemetry Evidence Fallback / Corroboration */}
          <div className="snapshot-telemetry-panel">
            <div className="telemetry-panel-header">
              <h6>Extracted DOM Telemetry & Structural Evidence</h6>
              <span className="telemetry-panel-note">
                {hasImage
                  ? "Multi-modal corroboration: Visual snapshot paired with DOM telemetry"
                  : "Preserved DOM evidence collected prior to termination"}
              </span>
            </div>

            <div className="telemetry-stats-strip">
              <div className="telemetry-stat-cell">
                <span className="stat-val">{lightbox.domStats?.links ?? 0}</span>
                <span className="stat-lbl">Links</span>
              </div>
              <div className="telemetry-stat-cell">
                <span className="stat-val">{lightbox.domStats?.buttons ?? 0}</span>
                <span className="stat-lbl">Buttons</span>
              </div>
              <div className="telemetry-stat-cell">
                <span className="stat-val">{lightbox.domStats?.inputs ?? 0}</span>
                <span className="stat-lbl">Inputs</span>
              </div>
              <div className="telemetry-stat-cell">
                <span className="stat-val">{lightbox.domStats?.forms ?? 0}</span>
                <span className="stat-lbl">Forms</span>
              </div>
              <div className="telemetry-stat-cell">
                <span className="stat-val">{lightbox.domStats?.checkboxes ?? 0}</span>
                <span className="stat-lbl">Checkboxes</span>
              </div>
              <div className="telemetry-stat-cell">
                <span className="stat-val">{lightbox.domStats?.text_chars ?? 0}</span>
                <span className="stat-lbl">Text Chars</span>
              </div>
            </div>

            {lightbox.textPreview && (
              <div className="telemetry-text-block">
                <span className="telemetry-text-label">Extracted Page Text Sample:</span>
                <div className="telemetry-text-content">{lightbox.textPreview}</div>
              </div>
            )}

            {lightbox.findings && lightbox.findings.length > 0 && (
              <div className="telemetry-findings-block">
                <span className="telemetry-findings-label">
                  Detected Dark Patterns ({lightbox.findings.length}):
                </span>
                <div className="telemetry-findings-list">
                  {lightbox.findings.map((f, i) => (
                    <div key={i} className="telemetry-finding-item">
                      <span className="telemetry-finding-name">{f.pattern || f.category}</span>
                      <span className="telemetry-finding-ev">
                        "{f.exact_text || (Array.isArray(f.evidence) ? f.evidence[0] : f.evidence) || "Element anomaly"}"
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function SingleScanSnapshotCard({
  result,
  website,
  apiBase,
  isBlocked,
  blockProvider,
  onOpenFullView,
}) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [retryKey, setRetryKey] = useState(0);

  // Derive image source
  const sUrl = result?.screenshot_url || website?.screenshot_url;
  const sB64 = website?.screenshot_b64 || result?.screenshot_b64;

  const rawUrl = sUrl
    ? (sUrl.startsWith("http") ? sUrl : `${apiBase}${sUrl}`)
    : (sB64 ? (sB64.startsWith("data:image") ? sB64 : `data:image/jpeg;base64,${sB64}`) : null);

  const imgSrc = rawUrl
    ? (rawUrl.startsWith("data:") ? rawUrl : `${rawUrl}${rawUrl.includes("?") ? "&" : "?"}_r=${retryKey}`)
    : null;

  const hasImage = Boolean(rawUrl);

  useEffect(() => {
    if (hasImage) {
      setLoading(true);
      setError(false);
    } else {
      setLoading(false);
    }
  }, [rawUrl]);

  const handleRetry = (e) => {
    e.stopPropagation();
    setError(false);
    setLoading(true);
    setRetryKey((k) => k + 1);
  };

  return (
    <div className="card visual-snapshot-card">
      <div className="snapshot-header">
        <h4>Viewport Snapshot Evidence</h4>
        <button
          type="button"
          className="btn-expand-screenshot"
          onClick={onOpenFullView}
          title={hasImage && !error ? "View full resolution snapshot modal" : "Inspect DOM and evidence details"}
        >
          {hasImage && !error ? "🔍 Full View" : "ℹ️ Evidence"}
        </button>
      </div>

      <div
        className="snapshot-thumbnail-wrap"
        onClick={onOpenFullView}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") onOpenFullView(); }}
      >
        {/* State 1: Loading */}
        {hasImage && loading && !error && (
          <div className="snapshot-thumb-loading">
            <span className="snapshot-thumb-spinner"></span>
            <span>Retrieving viewport snapshot...</span>
          </div>
        )}

        {/* State 2: Success (Image loaded) */}
        {hasImage && !error && (
          <div
            className="snapshot-thumb-container"
            style={{ display: loading ? "none" : "flex" }}
          >
            <img
              src={imgSrc}
              alt={website?.title || "Rendered page viewport"}
              className="snapshot-thumb-img"
              onLoad={() => setLoading(false)}
              onError={() => {
                setLoading(false);
                setError(true);
              }}
            />
            <span className="snapshot-hover-hint">Click to enlarge</span>
          </div>
        )}

        {/* State 3: Failure (Image failed to load / 404 / decode error) */}
        {hasImage && error && (
          <div className="snapshot-thumb-error" onClick={(e) => e.stopPropagation()}>
            <span className="snapshot-error-emoji">⚠️</span>
            <div className="snapshot-error-meta">
              <strong>Snapshot retrieval failed</strong>
              <span className="snapshot-error-hint">Image bytes could not be retrieved from backend</span>
            </div>
            <button
              type="button"
              className="btn-retry-thumb"
              onClick={handleRetry}
            >
              🔄 Retry
            </button>
          </div>
        )}

        {/* State 4: Unavailable (No snapshot captured, access blocked, or timed out) */}
        {!hasImage && (
          <div className="snapshot-thumb-unavailable">
            <span className="snapshot-unavailable-emoji">{isBlocked ? "🔒" : "📄"}</span>
            <div className="snapshot-unavailable-meta">
              <strong>{isBlocked ? "Snapshot unavailable (access blocked)" : "Snapshot unavailable"}</strong>
              <span className="snapshot-unavailable-hint">
                {isBlocked
                  ? `Access barrier (${blockProvider || "Cloudflare / Bot Shield"}). DOM evidence retained.`
                  : "Viewport screenshot was not captured. Structural DOM evidence is retained below."}
              </span>
            </div>
            <span className="snapshot-inspect-evidence-link">Click for Evidence & Telemetry</span>
          </div>
        )}
      </div>
    </div>
  );
}

export function ScanPage({
  url,
  setUrl,
  onScan,
  loading = false,
  scanStep = 0,
  result = null,
  error = "",
  onSwitchToCapture,
  onDownloadPdf,
  downloadingPdf = false,
  modelInfo = null,
  apiBase = "http://127.0.0.1:8000",
}) {
  // Mode selection: "single" vs "website"
  const [scanModeType, setScanModeType] = useState("single");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [screenshotModal, setScreenshotModal] = useState(false);

  // Whole Website Scan states
  const [maxPages, setMaxPages] = useState(20);
  const [concurrency, setConcurrency] = useState(3);
  const [maxDepth, setMaxDepth] = useState(2);
  const [allowSubdomains, setAllowSubdomains] = useState(false);
  const [websiteLoading, setWebsiteLoading] = useState(false);
  const [websiteScanId, setWebsiteScanId] = useState(null);
  const [websiteProgress, setWebsiteProgress] = useState(null);
  const [websiteSummary, setWebsiteSummary] = useState(null);
  const [websitePages, setWebsitePages] = useState([]);
  const [websiteError, setWebsiteError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [downloadingWebsitePdf, setDownloadingWebsitePdf] = useState(false);
  const [expandedPageUrl, setExpandedPageUrl] = useState(null);
  const [tableSearch, setTableSearch] = useState("");
  const [tableFilter, setTableFilter] = useState("all"); // "all" | "deceptive" | "clean" | "blocked"
  const [websiteLightbox, setWebsiteLightbox] = useState(null); // { url, title, pageId }

  const pollIntervalRef = useRef(null);

  // Clean up polling interval on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const currentModelName = result?.ai_analysis?.model_name || modelInfo?.model_name || "Calibrated Linear SVM V2";
  const currentAcc = result?.ai_analysis?.accuracy_display || modelInfo?.accuracy_display || "96.89%";
  const currentF1 = result?.ai_analysis?.f1_score || modelInfo?.f1_score || "0.9691";
  // Single-page scan data decomposition
  const security = result?.security_analysis;
  const website = result?.website;
  const darkPatternsData = result?.dark_pattern_analysis || security?.dark_pattern_analysis;

  const isBlocked = Boolean(
    result?.status === "blocked" ||
    result?.scan_status === "blocked" ||
    result?.access_blocked ||
    website?.status === "blocked" ||
    website?.access_blocked ||
    darkPatternsData?.status === "blocked" ||
    darkPatternsData?.access_blocked
  );

  const blockProvider =
    result?.block_provider ||
    website?.block_provider ||
    darkPatternsData?.block_provider ||
    "Automated Security Barrier";

  const blockReason =
    result?.message ||
    result?.block_info?.reason ||
    website?.block_info?.reason ||
    "Automated access was restricted by the target web server.";

  const darkPatterns = darkPatternsData?.findings || result?.findings || [];
  const darkRiskScore = darkPatternsData?.risk_score !== undefined ? darkPatternsData.risk_score : (result?.risk_score !== undefined ? result.risk_score : null);
  const darkRiskLevel = darkPatternsData?.risk_level || (darkRiskScore === null ? "Not Assessed" : "None");
  const riskBreakdown = darkPatternsData?.risk_breakdown || result?.combined_analysis?.risk_breakdown || {};

  const isPartial = Boolean(
    !isBlocked && (
      result?.capture_quality === "partial" ||
      result?.status === "partial" ||
      result?.scan_status === "partial" ||
      website?.capture_quality === "partial" ||
      darkPatternsData?.status === "partial" ||
      darkRiskScore === null
    )
  );

  const captureQuality =
    result?.capture_quality ||
    website?.capture_quality ||
    (isBlocked ? "blocked" : (isPartial ? "partial" : "complete"));

  const singleScanMode = result?.scan_mode || website?.scan_mode || "automatic";
  const requestedUrl = result?.requested_url || website?.requested_url || url;
  const pageTitle = website?.title || result?.title || "Untitled Webpage";
  const screenshotB64 = website?.screenshot_b64 || result?.screenshot_b64;
  const screenshotUrl = result?.screenshot_url || website?.screenshot_url;
  const hasScreenshot = Boolean(screenshotUrl || screenshotB64 || result?.has_screenshot || website?.has_screenshot);
  const duration = result?.scan_duration_seconds || website?.scan_duration_seconds;

  const openSnapshotLightbox = (page) => {
    const rawUrl = page.screenshot_url
      ? (page.screenshot_url.startsWith("http") ? page.screenshot_url : `${apiBase}${page.screenshot_url}`)
      : (page.screenshot_b64 ? `data:image/jpeg;base64,${page.screenshot_b64}` : null);

    setWebsiteLightbox({
      url: rawUrl,
      rawUrl: page.screenshot_url || null,
      title: page.title || "Untitled Webpage",
      pageId: page.page_id || "page_1",
      pageUrl: page.url || page.final_url || "",
      status: page.status || "completed",
      isBlocked: Boolean(page.access_blocked || page.status === "blocked"),
      blockProvider: page.block_provider,
      message: page.message || "",
      hasScreenshot: Boolean(rawUrl || page.has_screenshot),
      domStats: page.dom_stats || { links: 0, buttons: 0, inputs: 0, forms: 0, checkboxes: 0, text_chars: 0 },
      textPreview: page.text_preview || "",
      findings: page.findings || [],
      riskScore: page.risk_score,
      riskLevel: page.risk_level || "Low",
    });
  };

  const openSingleScanSnapshot = () => {
    const sUrl = result?.screenshot_url || website?.screenshot_url;
    const sB64 = website?.screenshot_b64 || result?.screenshot_b64;
    const resolvedUrl = sUrl
      ? (sUrl.startsWith("http") ? sUrl : `${apiBase}${sUrl}`)
      : (sB64 ? (sB64.startsWith("data:image") ? sB64 : `data:image/jpeg;base64,${sB64}`) : null);

    setWebsiteLightbox({
      url: resolvedUrl,
      rawUrl: sUrl || null,
      title: pageTitle || result?.website?.title || "Page Viewport",
      pageId: result?.scan_id || "single_scan",
      pageUrl: requestedUrl || result?.requested_url || result?.website?.url || url || "",
      status: result?.scan_status || "completed",
      isBlocked: Boolean(isBlocked),
      blockProvider: result?.block_provider || website?.block_provider,
      message: result?.warning || website?.warning || "",
      hasScreenshot: Boolean(resolvedUrl),
      domStats: {
        links: website?.links?.length || 0,
        buttons: website?.buttons?.length || 0,
        inputs: website?.inputs?.length || 0,
        forms: website?.forms?.length || 0,
        checkboxes: website?.checkboxes?.length || 0,
        text_chars: website?.text?.length || website?.visible_text?.length || 0,
      },
      textPreview: (website?.text || website?.visible_text || "").slice(0, 250),
      findings: result?.findings || [],
      riskScore: result?.risk_score,
      riskLevel: darkRiskLevel || "Low",
    });
  };

  // Single-page scan submit
  const handleSingleSubmit = (e) => {
    e.preventDefault();
    onScan();
  };

  // Whole-website scan start
  const handleStartWebsiteScan = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    const targetUrl = (url || "").trim();
    if (!targetUrl) {
      setWebsiteError("Please enter a website URL.");
      return;
    }
    if (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://")) {
      setWebsiteError("Invalid URL format. Please include http:// or https://");
      return;
    }

    setWebsiteError("");
    setWebsiteSummary(null);
    setWebsitePages([]);
    setWebsiteProgress(null);
    setCancelling(false);
    setWebsiteLoading(true);

    const isLocal = targetUrl.includes("localhost") || targetUrl.includes("127.0.0.1");

    try {
      const response = await fetch(`${apiBase}/scan/website`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: targetUrl,
          max_pages: Number(maxPages),
          concurrency: Number(concurrency),
          max_depth: Number(maxDepth),
          allow_subdomains: Boolean(allowSubdomains),
          allow_local: isLocal,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        setWebsiteError(data.detail || data.message || `Server returned ${response.status}`);
        setWebsiteLoading(false);
        return;
      }

      const activeScanId = data.scan_id;
      setWebsiteScanId(activeScanId);

      // Start live polling loop
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      pollIntervalRef.current = setInterval(async () => {
        try {
          const res = await fetch(`${apiBase}/scan/website/${activeScanId}`);
          if (!res.ok) return;
          const statusData = await res.json();
          setWebsiteProgress(statusData);

          const curStatus = statusData.status || statusData.scan_status;
          if (curStatus === "completed" || curStatus === "cancelled" || curStatus === "failed") {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
            setWebsiteSummary(statusData);
            setWebsiteLoading(false);
            setCancelling(false);

            // Fetch complete page-by-page array
            const pagesRes = await fetch(`${apiBase}/scan/website/${activeScanId}/pages`);
            if (pagesRes.ok) {
              const pagesData = await pagesRes.json();
              setWebsitePages(pagesData.pages || []);
            }
          }
        } catch (err) {
          console.error("Polling error:", err);
        }
      }, 1000);
    } catch (err) {
      console.error(err);
      setWebsiteError("Unable to connect to DarkShield backend server. Please verify FastAPI is running.");
      setWebsiteLoading(false);
    }
  };

  // Cancel in-flight crawl
  const handleCancelWebsiteScan = async () => {
    if (!websiteScanId) return;
    setCancelling(true);
    try {
      await fetch(`${apiBase}/scan/website/${websiteScanId}/cancel`, {
        method: "POST",
      });
    } catch (err) {
      console.error("Cancellation error:", err);
    }
  };

  // Download website-wide PDF report
  const handleDownloadWebsitePdf = async () => {
    if (!websiteScanId) return;
    setDownloadingWebsitePdf(true);
    try {
      const response = await fetch(`${apiBase}/report/website/${websiteScanId}/pdf`);
      if (!response.ok) throw new Error("Website PDF generation failed on server.");

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = `DarkShield_Website_Audit_${websiteScanId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error(err);
      alert("Failed to download whole website PDF report.");
    } finally {
      setDownloadingWebsitePdf(false);
    }
  };

  // Filtered pages for table
  const filteredPages = websitePages.filter((page) => {
    const q = tableSearch.toLowerCase().trim();
    const matchesSearch = !q || page.url.toLowerCase().includes(q) || (page.title || "").toLowerCase().includes(q);
    if (!matchesSearch) return false;

    if (tableFilter === "deceptive") {
      return (page.risk_score || 0) > 0 && page.findings_count > 0;
    } else if (tableFilter === "clean") {
      return (page.risk_score === 0 || page.findings_count === 0) && !page.access_blocked;
    } else if (tableFilter === "blocked") {
      return page.access_blocked || page.status === "blocked";
    }
    return true;
  });

  return (
    <div className="page-container scan-page">
      {/* 1. SCAN INPUT CARD & MODE SELECTOR */}
      <section className="card scan-input-card">
        <div className="scan-card-header">
          <div>
            <h3>Dark Pattern Security Scanner</h3>
            <span className="scan-card-sub">
              Analyze public websites for deceptive design tricks, dark UX traps, and compliance posture.
            </span>
          </div>
        </div>

        {/* Mode Selector Tabs */}
        <div className="scan-mode-tabs">
          <button
            type="button"
            className={`scan-mode-tab ${scanModeType === "single" ? "active" : ""}`}
            onClick={() => setScanModeType("single")}
          >
            📄 Single Page Scan
          </button>
          <button
            type="button"
            className={`scan-mode-tab ${scanModeType === "website" ? "active" : ""}`}
            onClick={() => setScanModeType("website")}
          >
            🕸️ Whole Website Scan
          </button>
        </div>

        {/* Mode A: Single Page Scan Form */}
        {scanModeType === "single" && (
          <form onSubmit={handleSingleSubmit} className="scan-main-form">
            <div className="scan-input-row">
              <div className="scan-url-wrapper">
                <span className="scan-url-icon">🌐</span>
                <input
                  type="text"
                  className="scan-url-input"
                  placeholder="https://example.com/page"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={loading}
                />
              </div>
              <button
                type="submit"
                className="btn-start-scan"
                disabled={loading}
              >
                {loading ? (
                  <>
                    <span className="spinner-sm"></span>
                    <span>Scanning...</span>
                  </>
                ) : (
                  <span>🔍 Start Page Scan</span>
                )}
              </button>
            </div>

            <div className="scan-collapsible-options">
              <button
                type="button"
                className="btn-toggle-options"
                onClick={() => setShowAdvanced(!showAdvanced)}
              >
                {showAdvanced ? "▲ Hide Advanced Options" : "▼ Show Advanced Options"}
              </button>

              {showAdvanced && (
                <div className="advanced-options-panel">
                  <div className="options-grid">
                    <div className="option-item">
                      <span className="option-label">Engine Architecture:</span>
                      <span className="option-val">{currentModelName} ({currentAcc} Test Acc) + 12 Heuristics</span>
                    </div>
                    <div className="option-item">
                      <span className="option-label">Crawler Engine:</span>
                      <span className="option-val">Playwright Headless Chromium (1440x900)</span>
                    </div>
                    <div className="option-item">
                      <span className="option-label">Anti-Bot Handling:</span>
                      <span className="option-val">Strict Gating (Zero Evasion / Ethical Audit)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </form>
        )}

        {/* Mode B: Whole Website Scan Form */}
        {scanModeType === "website" && (
          <form onSubmit={handleStartWebsiteScan} className="scan-main-form">
            <div className="scan-input-row">
              <div className="scan-url-wrapper">
                <span className="scan-url-icon">🌐</span>
                <input
                  type="text"
                  className="scan-url-input"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  disabled={websiteLoading}
                />
              </div>
              <button
                type="submit"
                className="btn-start-scan"
                disabled={websiteLoading}
              >
                {websiteLoading ? (
                  <>
                    <span className="spinner-sm"></span>
                    <span>Crawling...</span>
                  </>
                ) : (
                  <span>🕸️ Start Website Scan</span>
                )}
              </button>
            </div>

            <div className="website-scan-config-row">
              <div className="config-field">
                <label className="config-label">Page Limit:</label>
                <div className="preset-chips-row">
                  {[20, 50, 100].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      className={`preset-chip-btn ${maxPages === preset ? "active" : ""}`}
                      onClick={() => setMaxPages(preset)}
                      disabled={websiteLoading}
                    >
                      {preset}
                    </button>
                  ))}
                  <input
                    type="number"
                    min="1"
                    max="150"
                    className="config-input config-input-sm"
                    value={maxPages}
                    onChange={(e) => setMaxPages(Math.max(1, Math.min(150, parseInt(e.target.value) || 1)))}
                    disabled={websiteLoading}
                    title="Custom page limit (1 to 150)"
                  />
                </div>
              </div>

              <div className="config-field">
                <label className="config-label">Concurrency:</label>
                <select
                  className="config-input"
                  value={concurrency}
                  onChange={(e) => setConcurrency(Math.max(1, Math.min(6, parseInt(e.target.value) || 3)))}
                  disabled={websiteLoading}
                >
                  <option value={1}>1 Worker (Sequential)</option>
                  <option value={2}>2 Workers</option>
                  <option value={3}>3 Workers (Fast / Recommended)</option>
                  <option value={4}>4 Workers</option>
                  <option value={6}>6 Workers (Max)</option>
                </select>
              </div>

              <div className="config-field">
                <label className="config-label">Max Depth:</label>
                <input
                  type="number"
                  min="0"
                  max="5"
                  className="config-input config-input-sm"
                  value={maxDepth}
                  onChange={(e) => setMaxDepth(Math.max(0, Math.min(5, parseInt(e.target.value) || 0)))}
                  disabled={websiteLoading}
                />
              </div>

              <div className="config-field">
                <label className="config-checkbox-label">
                  <input
                    type="checkbox"
                    checked={allowSubdomains}
                    onChange={(e) => setAllowSubdomains(e.target.checked)}
                    disabled={websiteLoading}
                  />
                  <span>Subdomains</span>
                </label>
              </div>
            </div>
          </form>
        )}

        {/* Errors */}
        {scanModeType === "single" && error && (
          <div className="scan-error-alert">
            <span className="error-icon">⚠️</span>
            <div className="error-body">
              <strong>Scan Error:</strong>
              <p>{error}</p>
            </div>
          </div>
        )}

        {scanModeType === "website" && websiteError && (
          <div className="scan-error-alert">
            <span className="error-icon">⚠️</span>
            <div className="error-body">
              <strong>Website Scan Error:</strong>
              <p>{websiteError}</p>
            </div>
          </div>
        )}
      </section>

      {/* ========================================================================= */}
      {/* MODE A: SINGLE PAGE SCAN PROGRESS & RESULTS                                */}
      {/* ========================================================================= */}
      {scanModeType === "single" && (
        <>
          {loading && (
            <section className="scan-progress-section">
              <LoadingStepper currentStep={scanStep} />
            </section>
          )}

          {result && !loading && (
            <section className="scan-results-container">
              {/* Results Action Bar / Metadata */}
              <div className="card results-meta-bar">
                <div className="meta-bar-left">
                  <div className="meta-site-info">
                    <span className="meta-site-url" title={requestedUrl}>{requestedUrl}</span>
                    <span className="meta-site-title">{pageTitle}</span>
                  </div>
                  <div className="meta-badges-row">
                    <ModeBadge mode={singleScanMode} />
                    <span className={`quality-pill quality-${captureQuality}`}>
                      Quality: <strong>{captureQuality.toUpperCase()}</strong>
                    </span>
                    <StatusBadge status={isBlocked ? "blocked" : (isPartial ? "partial" : result.scan_status)} />
                    {duration && <span className="meta-duration-pill">⏱️ {duration}s</span>}
                  </div>
                </div>

                <div className="meta-bar-right">
                  {result.scan_id && (
                    <button
                      type="button"
                      className="btn-export-pdf"
                      onClick={() => onDownloadPdf(result.scan_id)}
                      disabled={downloadingPdf}
                    >
                      {downloadingPdf ? (
                        <>
                          <span className="spinner-sm"></span>
                          <span>Generating PDF...</span>
                        </>
                      ) : (
                        <span>📄 {isBlocked ? "Export Blocked Scan Report" : "Export PDF Report"}</span>
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* IF BLOCKED STATE */}
              {isBlocked ? (
                <BlockedNotice
                  provider={blockProvider}
                  reason={blockReason}
                  url={requestedUrl}
                  onSwitchToCapture={onSwitchToCapture}
                  onRetry={onScan}
                  onExportPdf={result.scan_id ? () => onDownloadPdf(result.scan_id) : null}
                />
              ) : (
                <>
                  {/* INCOMPLETE / PARTIAL CAPTURE NOTICE */}
                  {isPartial && (
                    <div className="card" style={{ borderLeft: "4px solid #f59e0b", backgroundColor: "#fffbeb", padding: "16px 20px", marginBottom: "16px" }}>
                      <div style={{ display: "flex", alignItems: "flex-start", gap: "12px" }}>
                        <span style={{ fontSize: "22px", lineHeight: "1" }}>⚠️</span>
                        <div style={{ flex: 1 }}>
                          <h4 style={{ margin: "0 0 6px 0", color: "#92400e", fontSize: "14px", fontWeight: "600" }}>
                            Incomplete Page Capture — Deceptive UX Risk Scoring Withheld
                          </h4>
                          <p style={{ margin: "0 0 10px 0", color: "#78350f", fontSize: "13px", lineHeight: "1.5" }}>
                            Automated scan captured incomplete page content. Risk scoring was withheld to avoid a false clean result. Try Browser Capture to analyze the fully rendered webpage.
                          </p>
                          <button
                            type="button"
                            className="btn-primary-capture"
                            onClick={onSwitchToCapture}
                            style={{ display: "inline-flex", alignItems: "center", gap: "6px", padding: "6px 14px", fontSize: "12px" }}
                          >
                            <span>🌐 Open Browser Capture Mode</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* CENTRAL OVERALL RISK CARD */}
                  <div className="card central-risk-card">
                    <div className="risk-card-left">
                      <span className="risk-super-label">OVERALL DECEPTIVE UX RISK</span>
                      <div className="risk-headline-row">
                        <span className="risk-score-display">{isPartial || darkRiskScore === null ? "N/A" : darkRiskScore}</span>
                        <span className="risk-score-denominator">/ 100</span>
                      </div>
                      {isPartial || darkRiskScore === null ? (
                        <span className="status-badge-component status-partial">Score Withheld</span>
                      ) : (
                        <RiskBadge level={darkRiskLevel} size="normal" />
                      )}
                      <p className="risk-card-desc">
                        {isPartial
                          ? "Automated scan captured incomplete page content. Risk scoring was withheld to prevent a misleading clean score."
                          : `Evaluated across ${darkPatterns.length} detected pattern(s) using DarkShield's 5-Factor scoring engine.`}
                      </p>
                    </div>

                    <div className="risk-card-gauge">
                      <RadialGauge
                        value={isPartial || darkRiskScore === null ? 0 : darkRiskScore}
                        max={100}
                        label={isPartial ? "Withheld" : `${darkRiskLevel} Risk`}
                        size={150}
                        strokeWidth={12}
                        variant="deception"
                      />
                    </div>
                  </div>

                  {/* 5-FACTOR DECEPTIVE RISK BREAKDOWN */}
                  {riskBreakdown && (
                    <div className="card risk-breakdown-card">
                      <div className="breakdown-header">
                        <h4>5-Factor Risk Weight Breakdown</h4>
                        <span className="breakdown-formula-note">
                          25% Severity + 20% Confidence + 15% Frequency + 25% User Impact + 15% Behavioral Evidence
                        </span>
                      </div>

                      <div className="breakdown-bars-grid">
                        <div className="breakdown-bar-item">
                          <div className="bar-labels-row">
                            <span className="factor-name">Severity (25% Weight)</span>
                            <strong className="factor-pct">{Math.round(riskBreakdown.severity ?? 0)}%</strong>
                          </div>
                          <div className="bar-track">
                            <div
                              className="bar-fill fill-rose"
                              style={{ width: `${Math.min(100, Math.round(riskBreakdown.severity ?? 0))}%` }}
                            />
                          </div>
                        </div>

                        <div className="breakdown-bar-item">
                          <div className="bar-labels-row">
                            <span className="factor-name">Confidence (20% Weight)</span>
                            <strong className="factor-pct">{Math.round(riskBreakdown.confidence ?? 0)}%</strong>
                          </div>
                          <div className="bar-track">
                            <div
                              className="bar-fill fill-sky"
                              style={{ width: `${Math.min(100, Math.round(riskBreakdown.confidence ?? 0))}%` }}
                            />
                          </div>
                        </div>

                        <div className="breakdown-bar-item">
                          <div className="bar-labels-row">
                            <span className="factor-name">Frequency (15% Weight)</span>
                            <strong className="factor-pct">{Math.round(riskBreakdown.frequency ?? 0)}%</strong>
                          </div>
                          <div className="bar-track">
                            <div
                              className="bar-fill fill-amber"
                              style={{ width: `${Math.min(100, Math.round(riskBreakdown.frequency ?? 0))}%` }}
                            />
                          </div>
                        </div>

                        <div className="breakdown-bar-item">
                          <div className="bar-labels-row">
                            <span className="factor-name">User Impact (25% Weight)</span>
                            <strong className="factor-pct">{Math.round(riskBreakdown.user_impact ?? 0)}%</strong>
                          </div>
                          <div className="bar-track">
                            <div
                              className="bar-fill fill-indigo"
                              style={{ width: `${Math.min(100, Math.round(riskBreakdown.user_impact ?? 0))}%` }}
                            />
                          </div>
                        </div>

                        <div className="breakdown-bar-item">
                          <div className="bar-labels-row">
                            <span className="factor-name">Behavioral Evidence (15% Weight)</span>
                            <strong className="factor-pct">{Math.round(riskBreakdown.behavioral_evidence ?? 0)}%</strong>
                          </div>
                          <div className="bar-track">
                            <div
                              className="bar-fill fill-emerald"
                              style={{ width: `${Math.min(100, Math.round(riskBreakdown.behavioral_evidence ?? 0))}%` }}
                            />
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* DARK PATTERN FINDINGS ACCORDION */}
                  <div className="findings-section-wrap">
                    <div className="findings-section-header">
                      <h3>Deceptive Pattern Findings ({darkPatterns.length})</h3>
                      <span className="findings-sub">
                        Verified through {currentModelName} ({currentAcc} Test Acc, F1: {currentF1}) and multi-modal corroboration
                      </span>
                    </div>

                    {darkPatterns.length === 0 ? (
                      <div className="card clean-findings-card">
                        <span className="clean-icon">✓</span>
                        <div>
                          <h4>No Deceptive Patterns Detected</h4>
                          <p>
                            The analyzed page complies with ethical UX transparency standards.
                            No high-pressure countdowns, confirmshaming, or artificial scarcity triggers were found.
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div className="findings-accordion-list">
                        {darkPatterns.map((finding, idx) => (
                          <FindingCard
                            key={idx}
                            finding={finding}
                            index={idx}
                            defaultOpen={idx === 0}
                          />
                        ))}
                      </div>
                    )}
                  </div>

                  {/* DUAL COLUMNS: SECURITY POSTURE & VISUAL SNAPSHOT */}
                  <div className="dual-info-row">
                    <div className="card security-posture-card">
                      <div className="posture-header">
                        <h4>Security & Vulnerability Posture</h4>
                        <span className="posture-score">
                          {security?.security_score ?? 100}/100
                        </span>
                      </div>
                      <div className="posture-stats-grid">
                        <div className="posture-stat-box">
                          <span className="stat-num">{website?.links?.length ?? 0}</span>
                          <span className="stat-name">External Links</span>
                        </div>
                        <div className="posture-stat-box">
                          <span className="stat-num">{website?.inputs?.length ?? 0}</span>
                          <span className="stat-name">Input Fields</span>
                        </div>
                        <div className="posture-stat-box">
                          <span className="stat-num">{website?.buttons?.length ?? 0}</span>
                          <span className="stat-name">Interactive Buttons</span>
                        </div>
                      </div>
                    </div>

                    <SingleScanSnapshotCard
                      result={result}
                      website={website}
                      apiBase={apiBase}
                      isBlocked={isBlocked}
                      blockProvider={result?.block_provider || website?.block_provider}
                      onOpenFullView={openSingleScanSnapshot}
                    />
                  </div>
                </>
              )}
            </section>
          )}
        </>
      )}

      {/* ========================================================================= */}
      {/* MODE B: WHOLE WEBSITE SCAN LIVE PROGRESS & COMPREHENSIVE DASHBOARD         */}
      {/* ========================================================================= */}
      {scanModeType === "website" && (
        <>
          {/* Live Progress Card */}
          {websiteLoading && websiteProgress && (
            <section className="card website-progress-card">
              <div className="progress-header-row">
                <div className="progress-title-wrap">
                  <span className="progress-pulse-badge">
                    <span className="live-pulse-dot"></span>
                    <span>{websiteProgress.status === "cancelling" ? "Cancelling..." : "Crawling Website..."}</span>
                  </span>
                  <strong>{websiteProgress.base_url}</strong>
                  <span className="meta-duration-pill" style={{ marginLeft: "8px" }}>
                    ⏱️ Elapsed: {websiteProgress.elapsed_seconds ?? 0}s (Target: 5s)
                  </span>
                </div>

                <button
                  type="button"
                  className="btn-cancel-crawl"
                  onClick={handleCancelWebsiteScan}
                  disabled={cancelling}
                >
                  {cancelling ? "Halting crawler..." : "⏹️ Cancel Crawl"}
                </button>
              </div>

              {/* Progress Bar */}
              <div className="progress-bar-container">
                <div
                  className="progress-bar-fill"
                  style={{ width: `${Math.max(5, websiteProgress.percent_complete || 0)}%` }}
                />
              </div>

              {/* Live Metric Counters */}
              <div className="website-metrics-grid">
                <div className="website-metric-card">
                  <span className="metric-card-val">{websiteProgress.pages_scanned}</span>
                  <span className="metric-card-lbl">Pages Scanned</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val">{websiteProgress.pages_discovered}</span>
                  <span className="metric-card-lbl">Pages Discovered</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val">{websiteProgress.pages_blocked}</span>
                  <span className="metric-card-lbl">Blocked (WAF)</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val">{websiteProgress.pages_failed}</span>
                  <span className="metric-card-lbl">Failed / Unreachable</span>
                </div>
              </div>

              {websiteProgress.current_url && (
                <div className="crawling-url-pill">
                  ⏳ <strong>Inspecting DOM:</strong> {websiteProgress.current_url}
                </div>
              )}
            </section>
          )}

          {/* Website Scan Finished Summary Dashboard */}
          {websiteSummary && !websiteLoading && (
            <section className="scan-results-container">
              {/* Results Action Bar */}
              <div className="card results-meta-bar">
                <div className="meta-bar-left">
                  <div className="meta-site-info">
                    <span className="meta-site-url" title={websiteSummary.base_url}>
                      {websiteSummary.base_url}
                    </span>
                    <span className="meta-site-title">
                      Whole Website Audit (ID: {websiteSummary.scan_id})
                    </span>
                  </div>
                  <div className="meta-badges-row">
                    <span className="quality-pill quality-complete">Mode: WHOLE WEBSITE</span>
                    <StatusBadge status={websiteSummary.scan_status} />
                    <span className="meta-duration-pill">⏱️ {websiteSummary.duration_seconds}s</span>
                    <span className="meta-duration-pill">
                      📊 {websiteSummary.pages_scanned} / {websiteSummary.total_pages_discovered} Pages ({websiteSummary.coverage_percentage}% Coverage)
                    </span>
                    <span className={`meta-duration-pill ${websiteSummary.target_5s_achieved ? "target-achieved-pill" : (websiteSummary.incomplete_within_target ? "target-incomplete-pill" : "target-missed-pill")}`}>
                      {websiteSummary.target_5s_achieved
                        ? "⚡ 5s Target: ACHIEVED"
                        : (websiteSummary.incomplete_within_target ? "⚠️ 5s Target: EXCEEDED (Incomplete)" : "⏱️ Target: 5s")}
                    </span>
                  </div>
                </div>

                <div className="meta-bar-right">
                  <button
                    type="button"
                    className="btn-export-pdf"
                    onClick={handleDownloadWebsitePdf}
                    disabled={downloadingWebsitePdf}
                  >
                    {downloadingWebsitePdf ? (
                      <>
                        <span className="spinner-sm"></span>
                        <span>Generating PDF...</span>
                      </>
                    ) : (
                      <span>📄 Export Website PDF Report</span>
                    )}
                  </button>
                </div>
              </div>

              {/* Limit Reached Notice Banner */}
              {websiteSummary.limit_reached && (
                <div className="limit-reached-banner">
                  <span className="limit-icon">⚠️</span>
                  <div className="limit-text">
                    <strong>Crawl Limit Reached:</strong> Stopped at configured limit of{" "}
                    <strong>{websiteSummary.pages_scanned} pages</strong> ({websiteSummary.total_pages_discovered} total URLs discovered).
                    Unscanned pages may contain additional design patterns. Increase page limit to audit deeper.
                  </div>
                </div>
              )}

              {/* Scope & Methodology Banner */}
              <div className="scope-notice-banner">
                <span className="scope-notice-icon">ℹ️</span>
                <div className="scope-notice-content">
                  <h5>Sampling Scope & Methodology Disclosure</h5>
                  <p>{websiteSummary.methodology}</p>
                </div>
              </div>

              {/* Central Risk Indicator Card */}
              <div className="card central-risk-card">
                <div className="risk-card-left">
                  <span className="risk-super-label">WEBSITE DECEPTION RISK INDICATOR</span>
                  <div className="risk-headline-row">
                    <span className="risk-score-display">{websiteSummary.website_risk_score}</span>
                    <span className="risk-score-denominator">/ 100</span>
                  </div>
                  <RiskBadge level={websiteSummary.website_risk_level} size="normal" />
                  <p className="risk-card-desc">
                    Synthesizes peak page severity (50%), mean page risk (30%), and deceptive category breadth (20%) across {websiteSummary.pages_successful} inspected page(s).
                  </p>
                </div>

                <div className="risk-card-gauge">
                  <RadialGauge
                    value={websiteSummary.website_risk_score}
                    max={100}
                    label={`${websiteSummary.website_risk_level} Risk`}
                    size={150}
                    strokeWidth={12}
                    variant="deception"
                  />
                </div>
              </div>

              {/* Key Aggregates Cards */}
              <div className="website-metrics-grid">
                <div className="website-metric-card">
                  <span className="metric-card-val" style={{ color: "var(--success)" }}>
                    {websiteSummary.pages_successful}
                  </span>
                  <span className="metric-card-lbl">Successfully Analyzed</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val">{websiteSummary.pages_clean}</span>
                  <span className="metric-card-lbl">Clean Pages</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val" style={{ color: "var(--danger)" }}>
                    {websiteSummary.pages_with_dark_patterns}
                  </span>
                  <span className="metric-card-lbl">Pages with Dark Patterns</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val" style={{ color: "var(--warning)" }}>
                    {websiteSummary.total_unique_findings}
                  </span>
                  <span className="metric-card-lbl">Unique Findings</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val">{websiteSummary.pages_blocked}</span>
                  <span className="metric-card-lbl">Blocked (WAF)</span>
                </div>
                <div className="website-metric-card">
                  <span className="metric-card-val" style={{ color: websiteSummary.target_5s_achieved ? "var(--success)" : (websiteSummary.incomplete_within_target ? "var(--warning)" : "var(--text-secondary)") }}>
                    {websiteSummary.duration_seconds}s
                  </span>
                  <span className="metric-card-lbl">
                    {websiteSummary.target_5s_achieved ? "⚡ 5s Target: Achieved" : (websiteSummary.incomplete_within_target ? "⚠️ 5s Target: Incomplete" : "⏱️ 5s Target: Exceeded")}
                  </span>
                </div>
              </div>

              {/* Category Pills */}
              {websiteSummary.category_counts && Object.keys(websiteSummary.category_counts).length > 0 && (
                <div className="card">
                  <h4 style={{ margin: "0 0 8px 0", fontSize: "0.95rem" }}>Detected Pattern Categories</h4>
                  <div className="category-pills-wrap">
                    {Object.entries(websiteSummary.category_counts).map(([cat, count]) => (
                      <span key={cat} className="category-pill">
                        <span>{cat}</span>
                        <span className="category-pill-count">{count}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Page-by-Page Table */}
              <div className="card">
                <div className="table-filter-bar">
                  <div className="table-search-box">
                    <span style={{ marginRight: "6px" }}>🔍</span>
                    <input
                      type="text"
                      className="table-search-input"
                      placeholder="Search scanned page URLs or titles..."
                      value={tableSearch}
                      onChange={(e) => setTableSearch(e.target.value)}
                    />
                  </div>

                  <div className="table-filter-tabs">
                    <button
                      type="button"
                      className={`table-filter-btn ${tableFilter === "all" ? "active" : ""}`}
                      onClick={() => setTableFilter("all")}
                    >
                      All ({websitePages.length})
                    </button>
                    <button
                      type="button"
                      className={`table-filter-btn ${tableFilter === "deceptive" ? "active" : ""}`}
                      onClick={() => setTableFilter("deceptive")}
                    >
                      Deceptive ({websitePages.filter(p => (p.risk_score || 0) > 0).length})
                    </button>
                    <button
                      type="button"
                      className={`table-filter-btn ${tableFilter === "clean" ? "active" : ""}`}
                      onClick={() => setTableFilter("clean")}
                    >
                      Clean ({websitePages.filter(p => p.risk_score === 0 && !p.access_blocked).length})
                    </button>
                    <button
                      type="button"
                      className={`table-filter-btn ${tableFilter === "blocked" ? "active" : ""}`}
                      onClick={() => setTableFilter("blocked")}
                    >
                      Blocked ({websitePages.filter(p => p.access_blocked || p.status === "blocked").length})
                    </button>
                  </div>
                </div>

                <div className="website-pages-table-container">
                  <table className="website-pages-table">
                    <thead>
                      <tr>
                        <th style={{ width: "60px" }}>Depth</th>
                        <th>Page Title & URL</th>
                        <th style={{ width: "110px" }}>Status</th>
                        <th style={{ width: "130px" }}>Risk Score</th>
                        <th style={{ width: "100px" }}>Findings</th>
                        <th style={{ width: "110px", textAlign: "right" }}>Action</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredPages.length === 0 ? (
                        <tr>
                          <td colSpan="6" style={{ textAlign: "center", padding: "24px", color: "var(--text-muted)" }}>
                            No pages match the current filter.
                          </td>
                        </tr>
                      ) : (
                        filteredPages.map((page, idx) => {
                          const isRowExpanded = expandedPageUrl === page.url;
                          const isPageBlocked = page.access_blocked || page.status === "blocked";
                          return (
                            <React.Fragment key={idx}>
                              <tr>
                                <td>
                                  <span style={{ fontSize: "0.75rem", background: "var(--bg-surface)", padding: "2px 6px", borderRadius: "4px", border: "1px solid var(--border-subtle)" }}>
                                    d={page.depth}
                                  </span>
                                </td>
                                <td>
                                  <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: "2px" }}>
                                    {page.title || "Untitled Webpage"}
                                  </div>
                                  <a
                                    href={page.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    style={{ fontSize: "0.76rem", color: "var(--primary)", textDecoration: "none" }}
                                    title={page.url}
                                  >
                                    {page.url}
                                  </a>
                                </td>
                                <td>
                                  <StatusBadge status={isPageBlocked ? "blocked" : page.status} />
                                </td>
                                <td>
                                  {isPageBlocked || page.risk_score === null ? (
                                    <span className="status-badge-component status-partial">Withheld</span>
                                  ) : (
                                    <RiskBadge level={page.risk_level} size="small" />
                                  )}
                                </td>
                                <td>
                                  <strong style={{ fontSize: "0.9rem" }}>{page.findings_count}</strong>
                                </td>
                                <td style={{ textAlign: "right" }}>
                                  <button
                                    type="button"
                                    className="btn-table-view"
                                    onClick={() => setExpandedPageUrl(isRowExpanded ? null : page.url)}
                                  >
                                    {isRowExpanded ? "▲ Hide" : "▼ Details"}
                                  </button>
                                </td>
                              </tr>

                              {/* Expandable Accordion Row */}
                              {isRowExpanded && (
                                <tr className="page-accordion-row">
                                  <td colSpan="6">
                                    <div className="page-detail-layout">
                                      {/* Left Column: Visual Snapshot & DOM Telemetry */}
                                      <div className="page-snapshot-col">
                                        <div className="snapshot-header-small">
                                          <span className="snapshot-badge-label">Page Snapshot</span>
                                          {page.screenshot_url || page.screenshot_b64 ? (
                                            <button
                                              type="button"
                                              className="btn-lightbox-trigger"
                                              onClick={() => openSnapshotLightbox(page)}
                                            >
                                              🔍 Full Size
                                            </button>
                                          ) : (
                                            <button
                                              type="button"
                                              className="btn-lightbox-trigger"
                                              onClick={() => openSnapshotLightbox(page)}
                                              style={{ fontSize: "0.68rem" }}
                                            >
                                              ℹ️ Evidence
                                            </button>
                                          )}
                                        </div>

                                        {page.screenshot_url || page.screenshot_b64 ? (
                                          <div
                                            className="page-snapshot-preview-wrap"
                                            onClick={() => openSnapshotLightbox(page)}
                                          >
                                            <img
                                              src={page.screenshot_url ? (page.screenshot_url.startsWith("http") ? page.screenshot_url : `${apiBase}${page.screenshot_url}`) : `data:image/jpeg;base64,${page.screenshot_b64}`}
                                              alt={page.title || "Page snapshot"}
                                              className="page-snapshot-thumb"
                                            />
                                            <span className="snapshot-hover-hint">Click to enlarge</span>
                                          </div>
                                        ) : (
                                          <div
                                            className="page-snapshot-placeholder"
                                            onClick={() => openSnapshotLightbox(page)}
                                            style={{ cursor: "pointer" }}
                                            title="Click to view extracted DOM telemetry evidence"
                                          >
                                            <span style={{ fontSize: "1.4rem" }}>{isPageBlocked ? "🔒" : "📄"}</span>
                                            <span style={{ fontSize: "0.74rem", color: "var(--text-muted)", marginTop: "4px" }}>
                                              {isPageBlocked ? "Snapshot unavailable (access blocked)" : "Snapshot not captured"}
                                            </span>
                                            <span style={{ fontSize: "0.68rem", color: "var(--primary)", marginTop: "2px", fontWeight: 600 }}>
                                              View DOM Telemetry
                                            </span>
                                          </div>
                                        )}

                                        {/* DOM telemetry metadata */}
                                        <div className="page-dom-telemetry">
                                          <div className="dom-meta-item">
                                            <span className="dom-meta-lbl">Page ID:</span>
                                            <code className="dom-meta-code">{page.page_id || `page_${idx + 1}`}</code>
                                          </div>
                                          <div className="dom-meta-item">
                                            <span className="dom-meta-lbl">Duration:</span>
                                            <span>{page.scan_duration_seconds ? `${page.scan_duration_seconds}s` : "—"}</span>
                                          </div>
                                          {page.dom_stats && (
                                            <div className="dom-meta-stats-row">
                                              <span>🔗 {page.dom_stats.links ?? 0} links</span>
                                              <span>🔘 {page.dom_stats.buttons ?? 0} buttons</span>
                                              <span>📝 {page.dom_stats.text_chars ?? 0} chars</span>
                                            </div>
                                          )}
                                          {page.captured_at && (
                                            <div className="dom-meta-time" title={page.captured_at}>
                                              Captured: {new Date(page.captured_at).toLocaleTimeString()}
                                            </div>
                                          )}
                                        </div>
                                      </div>

                                      {/* Right Column: Audit Findings & Evidence */}
                                      <div className="page-findings-col">
                                        {isPageBlocked ? (
                                          <div className="page-blocked-box">
                                            <div className="blocked-box-header">
                                              <span style={{ fontSize: "1.1rem" }}>🔒</span>
                                              <strong>Access Restricted by {page.block_provider || "Anti-Bot / WAF Shield"}</strong>
                                            </div>
                                            <p className="blocked-box-desc">
                                              Automated crawl was denied access. Deception UX risk score was safely withheld to prevent an inaccurate 0/100 rating.
                                            </p>
                                          </div>
                                        ) : page.findings && page.findings.length > 0 ? (
                                          <div className="page-findings-list">
                                            <div className="findings-col-heading">
                                              <span>Audit Findings ({page.findings.length})</span>
                                              <span className="findings-col-subtitle">Verified Deceptive UI/UX Elements</span>
                                            </div>

                                            {page.findings.map((f, fIdx) => {
                                              const exactText = f.exact_text || (Array.isArray(f.evidence) ? f.evidence[0] : f.evidence);
                                              const evType = f.evidence_type || "text";
                                              return (
                                                <div key={fIdx} className="page-finding-card">
                                                  <div className="finding-card-top">
                                                    <div className="finding-name-wrap">
                                                      <span className="finding-card-title">{f.pattern}</span>
                                                      <span className="finding-type-pill">{evType.toUpperCase()}</span>
                                                      {f.detection_method && (
                                                        <span className="finding-method-pill">{f.detection_method}</span>
                                                      )}
                                                    </div>
                                                    <div className="finding-badge-wrap">
                                                      {f.confidence && (
                                                        <span className="finding-conf-badge">
                                                          {Math.round(f.confidence * 100)}% Conf
                                                        </span>
                                                      )}
                                                      <RiskBadge level={f.severity || "Medium"} size="small" />
                                                    </div>
                                                  </div>

                                                  {exactText && (
                                                    <div className="finding-quote-box">
                                                      <span className="quote-lbl">Exact Supporting Evidence:</span>
                                                      <div className="quote-text">"{exactText}"</div>
                                                    </div>
                                                  )}

                                                  <div className="finding-meta-footer">
                                                    {f.selector && (
                                                      <div className="finding-selector-row">
                                                        <span className="meta-lbl">Target Element:</span>
                                                        <code className="finding-selector-code">{f.selector}</code>
                                                      </div>
                                                    )}
                                                    {(f.reason || f.description) && (
                                                      <div className="finding-reason-row">
                                                        <span className="meta-lbl">Reason:</span>
                                                        <span className="reason-text">{f.reason || f.description}</span>
                                                      </div>
                                                    )}
                                                  </div>
                                                </div>
                                              );
                                            })}
                                          </div>
                                        ) : (
                                          <div className="page-clean-box">
                                            <div className="clean-box-header">
                                              <span className="clean-check-icon">✓</span>
                                              <strong>Clean Page</strong>
                                            </div>
                                            <p className="clean-box-desc">
                                              {page.clean_message || "No dark patterns detected on this captured page."}
                                            </p>
                                          </div>
                                        )}
                                      </div>
                                    </div>
                                  </td>
                                </tr>
                              )}
                            </React.Fragment>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </section>
          )}

        </>
      )}

      {/* Snapshot Evidence Lightbox Modal (Available to both Single Scan and Website Scan) */}
      {websiteLightbox && (
        <SnapshotEvidenceModal
          lightbox={websiteLightbox}
          onClose={() => setWebsiteLightbox(null)}
        />
      )}
    </div>
  );
}
