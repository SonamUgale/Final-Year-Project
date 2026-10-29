/**
 * DarkShield AI - Extension Popup Logic
 * Coordinates:
 * 1. Single Page Scan: direct DOM capture, screenshot, API transmission, and single-page assessment.
 * 2. Whole Website Scan: background crawl coordinator, configuration panel, real-time BFS progress,
 *    and multi-page audit list with per-page scores, evidence, and snapshots.
 */

const API_BASE = "http://127.0.0.1:8000";
const FRONTEND_BASE = "http://localhost:5173";

let currentTab = null;
let latestSingleScanId = null;
let latestWebsiteScanId = null;
let timerInterval = null;
let scanStartTime = null;
let statusPollTimer = null;

// DOM Elements - Header & Target Tab
const backendPill = document.getElementById("backend-status-pill");
const backendText = document.getElementById("backend-status-text");
const tabTitle = document.getElementById("tab-title");
const tabUrl = document.getElementById("tab-url");

// DOM Elements - Action Area
const actionSection = document.getElementById("action-section");
const btnAnalyze = document.getElementById("btn-analyze");
const btnWholeWebsiteToggle = document.getElementById("btn-whole-website-toggle");

// DOM Elements - Whole Website Config Panel
const wholeSitePanel = document.getElementById("whole-site-panel");
const siteDomainText = document.getElementById("site-domain-text");
const selectMaxPages = document.getElementById("select-max-pages");
const selectMaxDepth = document.getElementById("select-max-depth");
const btnStartSiteScan = document.getElementById("btn-start-site-scan");
const btnCloseSitePanel = document.getElementById("btn-close-site-panel");

// DOM Elements - Single Page Progress & Results
const progressSection = document.getElementById("progress-section");
const progressBarFill = document.getElementById("progress-bar-fill");
const progressStatusMsg = document.getElementById("progress-status-msg");
const progressStepNote = document.getElementById("progress-step-note");
const resultsSection = document.getElementById("results-section");
const resScore = document.getElementById("res-score");
const resRiskBadge = document.getElementById("res-risk-badge");
const resPatternsCount = document.getElementById("res-patterns-count");
const patternsList = document.getElementById("patterns-list");
const btnOpenDashboard = document.getElementById("btn-open-dashboard");
const btnDownloadPdf = document.getElementById("btn-download-pdf");
const btnSingleNewScan = document.getElementById("btn-single-new-scan");

// DOM Elements - Whole Website Progress & Results
const siteProgressSection = document.getElementById("site-progress-section");
const siteProgDomain = document.getElementById("site-prog-domain");
const siteProgTimer = document.getElementById("site-prog-timer");
const siteProgressBarFill = document.getElementById("site-progress-bar-fill");
const siteStatDiscovered = document.getElementById("site-stat-discovered");
const siteStatScanned = document.getElementById("site-stat-scanned");
const siteStatBlocked = document.getElementById("site-stat-blocked");
const siteStatFailed = document.getElementById("site-stat-failed");
const siteCurrentUrl = document.getElementById("site-current-url");
const btnCancelSiteScan = document.getElementById("btn-cancel-site-scan");

// DOM Elements - Whole Website Live Score Card (Immediate Assessment)
const siteLiveScoreCard = document.getElementById("site-live-score-card");
const siteLiveScoreVal = document.getElementById("site-live-score-val");
const siteLiveBadge = document.getElementById("site-live-badge");
const siteLiveFindingsTitle = document.getElementById("site-live-findings-title");
const siteLivePageTitle = document.getElementById("site-live-page-title");

function updateLiveScoreCard(pageRecord) {
  if (!pageRecord || !siteLiveScoreCard) return;
  siteLiveScoreCard.classList.remove("hidden");
  const isBlocked = Boolean(pageRecord.access_blocked || pageRecord.status === "blocked");
  const score = isBlocked ? null : (pageRecord.risk_score !== undefined ? pageRecord.risk_score : null);
  const badgeClass = getRiskBadgeClass(score);
  const badgeName = isBlocked ? "Blocked" : getRiskLevelName(score);

  if (siteLiveScoreVal) {
    siteLiveScoreVal.innerText = score !== null && score !== undefined ? score : "N/A";
  }
  if (siteLiveBadge) {
    siteLiveBadge.className = `risk-badge ${badgeClass}`;
    siteLiveBadge.innerText = badgeName;
  }
  const fCount = (pageRecord.findings || []).length || pageRecord.findings_count || 0;
  if (siteLiveFindingsTitle) {
    siteLiveFindingsTitle.innerText = isBlocked
      ? "Access Barrier Encountered"
      : (fCount === 0 ? "✓ 0 Deceptive Patterns Found" : `⚠️ ${fCount} Deceptive Pattern${fCount === 1 ? '' : 's'} Detected`);
  }
  if (siteLivePageTitle) {
    const rawTitle = pageRecord.title || pageRecord.url || "Initial Webpage";
    siteLivePageTitle.innerText = rawTitle.length > 40 ? rawTitle.slice(0, 37) + "..." : rawTitle;
  }
}

const siteResultsSection = document.getElementById("site-results-section");
const siteResTargetTitle = document.getElementById("site-res-target-title");
const siteResTargetUrl = document.getElementById("site-res-target-url");
const siteResStatusPill = document.getElementById("site-res-status-pill");
const siteResScore = document.getElementById("site-res-score");
const siteResRiskBadge = document.getElementById("site-res-risk-badge");
const siteResSummaryText = document.getElementById("site-res-summary-text");
const siteResCoverage = document.getElementById("site-res-coverage");
const siteResIncompleteTag = document.getElementById("site-res-incomplete-tag");
const siteResMethodology = document.getElementById("site-res-methodology");
const pillScanned = document.getElementById("pill-scanned");
const pillClean = document.getElementById("pill-clean");
const pillPatterns = document.getElementById("pill-patterns");
const pillBlocked = document.getElementById("pill-blocked");
const pillTimedOut = document.getElementById("pill-timed-out");
const pillFailed = document.getElementById("pill-failed");
const siteCategoryBreakdown = document.getElementById("site-category-breakdown");
const auditPageCount = document.getElementById("audit-page-count");
const btnToggleAllPages = document.getElementById("btn-toggle-all-pages");
const sitePagesList = document.getElementById("site-pages-list");
const siteLiveStreamBox = document.getElementById("site-live-stream-box");
const siteLiveStreamCount = document.getElementById("site-live-stream-count");
const siteLiveStreamList = document.getElementById("site-live-stream-list");
const btnSiteOpenDashboard = document.getElementById("btn-site-open-dashboard");
const btnSiteDownloadPdf = document.getElementById("btn-site-download-pdf");
const btnSiteNewScan = document.getElementById("btn-site-new-scan");

// DOM Elements - Error Banner
const errorBanner = document.getElementById("error-banner");
const errorText = document.getElementById("error-text");

function showError(msg) {
  errorText.innerText = msg;
  errorBanner.classList.remove("hidden");
}

function clearError() {
  errorBanner.classList.add("hidden");
  errorText.innerText = "";
}

/**
 * Maps raw exceptions to precise, user-actionable DarkShield diagnostics.
 */
function formatExtensionError(err) {
  const msg = (err && (err.message || err.detail)) || String(err || "");
  if (msg.includes("Receiving end does not exist") || msg.includes("Could not establish connection")) {
    return "Service worker unavailable: Background process could not be reached after multiple attempts. Please reload the extension at chrome://extensions.";
  }
  if (
    msg.includes("Script injection failed") ||
    msg.includes("Cannot access contents") ||
    msg.includes("Content script unavailable") ||
    msg.includes("Unable to extract rendered DOM")
  ) {
    return "Content script unavailable: Script injection failed on this tab. DarkShield AI inspects HTTP, HTTPS, or local test webpages.";
  }
  if (msg.includes("Failed to fetch") || msg.includes("NetworkError") || msg.includes("Backend unreachable")) {
    return `Backend unreachable: DarkShield API is offline at ${API_BASE}. Please start FastAPI on port 8000.`;
  }
  return msg;
}

/**
 * Safe runtime message sender with automatic retry and wake-up for dormant MV3 service workers.
 * Retries up to maxAttempts with exponential backoff before rejecting.
 */
function sendRuntimeMessage(message, maxAttempts = 15, retryDelayMs = 200) {
  return new Promise((resolve, reject) => {
    let attempt = 0;

    function trySend() {
      attempt++;
      try {
        chrome.runtime.sendMessage(message, (response) => {
          const lastError = chrome.runtime.lastError;
          if (lastError) {
            const errMsg = lastError.message || String(lastError);
            if (
              attempt < maxAttempts &&
              (errMsg.includes("Receiving end does not exist") || errMsg.includes("Could not establish connection"))
            ) {
              console.warn(`[DarkShield] Background service worker dormant. Retrying (${attempt}/${maxAttempts}) in ${retryDelayMs}ms...`);
              setTimeout(trySend, retryDelayMs);
              return;
            }
            return reject(lastError);
          }
          resolve(response);
        });
      } catch (err) {
        const errMsg = err?.message || String(err);
        if (
          attempt < maxAttempts &&
          (errMsg.includes("Receiving end does not exist") || errMsg.includes("Could not establish connection"))
        ) {
          console.warn(`[DarkShield] Background service worker dormant. Retrying (${attempt}/${maxAttempts}) in ${retryDelayMs}ms...`);
          setTimeout(trySend, retryDelayMs);
          return;
        }
        reject(err);
      }
    }

    trySend();
  });
}

function updateSingleProgress(step, totalSteps, title, detail) {
  progressSection.classList.remove("hidden");
  const pct = Math.round((step / totalSteps) * 100);
  progressBarFill.style.width = `${pct}%`;
  progressStatusMsg.innerText = title;
  progressStepNote.innerText = `Step ${step} of ${totalSteps}: ${detail}`;
}

async function checkBackendHealth() {
  try {
    const res = await fetch(`${API_BASE}/`, { method: "GET" });
    if (res.ok) {
      backendPill.className = "status-pill status-online";
      backendText.innerText = "Online";
      return true;
    }
    const errBody = await res.json().catch(() => ({}));
    const detail = errBody.detail || errBody.message || res.statusText || "Server error";
    showError(`Invalid API response (HTTP ${res.status}): ${detail}`);
  } catch {
    showError(`Backend unreachable: DarkShield API is offline at ${API_BASE}. Please start FastAPI on port 8000.`);
  }
  backendPill.className = "status-pill status-offline";
  backendText.innerText = "Offline";
  return false;
}

function getRiskBadgeClass(score) {
  if (score === null || score === undefined) return "risk-blocked";
  if (score === 0) return "risk-clean";
  if (score < 25) return "risk-low";
  if (score < 50) return "risk-medium";
  if (score < 75) return "risk-high";
  return "risk-very-high";
}

function getRiskLevelName(score) {
  if (score === null || score === undefined) return "Insufficient Data";
  if (score === 0) return "Clean";
  if (score < 25) return "Low Risk";
  if (score < 50) return "Medium Risk";
  if (score < 75) return "High Risk";
  return "Very High Risk";
}

function startTimer(startTimeMs) {
  scanStartTime = startTimeMs || Date.now();
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(() => {
    const elapsed = Math.round((Date.now() - scanStartTime) / 1000);
    if (siteProgTimer) siteProgTimer.innerText = `⏱️ ${elapsed}s`;
  }, 1000);
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function stopStatusPolling() {
  if (statusPollTimer) {
    clearInterval(statusPollTimer);
    statusPollTimer = null;
  }
}

function startStatusPolling(scanId) {
  if (statusPollTimer) clearInterval(statusPollTimer);
  if (!scanId) return;

  const pollStartTime = Date.now();
  let lastScannedCount = 0;
  let lastProgressTime = Date.now();
  const MAX_POLL_DURATION_MS = 120000; // 120-second client-side watchdog
  const STALL_TIMEOUT_MS = 45000;       // 45-second stall detector to recover from dormant SW

  statusPollTimer = setInterval(async () => {
    try {
      const now = Date.now();
      if (now - pollStartTime > MAX_POLL_DURATION_MS) {
        console.warn("[DarkShield] Status polling reached overall deadline (90s). Forcing completion fetch...");
        stopStatusPolling();
        try {
          await fetch(`${API_BASE}/scan/website/browser/${scanId}/finish`, { method: "POST" });
        } catch (e) {}
        const [sumRes, pagesRes] = await Promise.all([
          fetch(`${API_BASE}/scan/website/${scanId}`),
          fetch(`${API_BASE}/scan/website/${scanId}/pages`)
        ]);
        if (sumRes.ok && pagesRes.ok) {
          const sumData = await sumRes.json();
          const pData = await pagesRes.json();
          renderWebsiteResults(sumData.summary || sumData, pData.pages || []);
        } else {
          showError("Website scan timed out after 90 seconds.");
          resetView();
        }
        return;
      }

      const res = await fetch(`${API_BASE}/scan/website/${scanId}`);
      if (!res.ok) return;
      const data = await res.json();
      const status = data.status || data.scan_status;

      if (status === "crawling" || status === "initializing") {
        const scanned = data.pages_scanned || 0;
        if (scanned > lastScannedCount) {
          lastScannedCount = scanned;
          lastProgressTime = now;
        } else if (now - lastProgressTime > STALL_TIMEOUT_MS) {
          // Check if background service worker is still crawling or waking up
          sendRuntimeMessage({ type: "GET_SCAN_STATUS" }, 3, 200).then((swStatus) => {
            if (swStatus && swStatus.active) {
              lastProgressTime = now;
              return;
            }
            fetch(`${API_BASE}/scan/website/${scanId}`).then(r => r.json()).then(latest => {
              if (latest.status === "completed" || latest.status === "cancelled") {
                stopStatusPolling();
                fetch(`${API_BASE}/scan/website/${scanId}/pages`)
                  .then(pr => pr.json())
                  .then(pdata => renderWebsiteResults(latest.summary || latest, pdata.pages || []));
              }
            }).catch(() => {});
          }).catch(() => {});
        }

        showWebsiteProgressView({
          pagesScanned: scanned,
          pagesDiscovered: data.pages_discovered || data.total_discovered || data.discovered_count || 1,
          maxPages: data.config?.max_pages || data.max_pages || 20,
          pagesBlocked: data.pages_blocked || 0,
          pagesFailed: data.pages_failed || 0,
          pagesTimedOut: data.pages_timed_out || 0,
          current_stage: data.current_stage || data.stage,
          stage: data.current_stage || data.stage,
          currentUrl: data.current_stage || data.stage || data.current_url || "Processing pages...",
          first_page: data.first_page,
          latest_page: data.latest_page
        });
      } else if (status === "completed" || status === "cancelled") {
        stopStatusPolling();
        // Fetch detailed page records
        const pagesRes = await fetch(`${API_BASE}/scan/website/${scanId}/pages`);
        const pagesData = pagesRes.ok ? await pagesRes.json() : { pages: [] };
        renderWebsiteResults(data.summary || data, pagesData.pages || []);
      } else if (status === "failed") {
        stopStatusPolling();
        stopTimer();
        siteProgressSection.classList.add("hidden");
        actionSection.classList.remove("hidden");
        showError(data.error || "Whole website scan failed on backend.");
      }
    } catch (e) {
      // Ignore transient network blips during background polling
    }
  }, 1000);
}

/**
 * Reset UI to ready state
 */
function resetView() {
  clearError();
  stopTimer();
  stopStatusPolling();
  if (siteLiveScoreCard) siteLiveScoreCard.classList.add("hidden");
  if (siteLiveStreamBox) siteLiveStreamBox.classList.add("hidden");
  if (siteLiveStreamList) siteLiveStreamList.innerHTML = "";
  progressSection.classList.add("hidden");
  resultsSection.classList.add("hidden");
  siteProgressSection.classList.add("hidden");
  siteResultsSection.classList.add("hidden");
  wholeSitePanel.classList.add("hidden");
  actionSection.classList.remove("hidden");
  btnAnalyze.disabled = false;
  btnWholeWebsiteToggle.disabled = false;
}

// -------------------------------------------------
// TAB DISCOVERY & RESILIENT EXTRACTION HELPERS
// -------------------------------------------------

/**
 * Accurately discovers the target web tab across popup bubbles, standalone windows, and test runners.
 */
async function getTargetTab() {
  // 1. Check active tab in current window
  const activeTabs = await new Promise((res) => chrome.tabs.query({ active: true, currentWindow: true }, res));
  if (activeTabs && activeTabs.length > 0) {
    const tab = activeTabs[0];
    if (tab.url && (tab.url.startsWith("http://") || tab.url.startsWith("https://") || tab.url.startsWith("file://"))) {
      return tab;
    }
  }

  // 2. Check active tab in last focused window (standard when popup is in its own window/dev panel)
  const lastFocusedTabs = await new Promise((res) => chrome.tabs.query({ active: true, lastFocusedWindow: true }, res));
  if (lastFocusedTabs && lastFocusedTabs.length > 0) {
    const tab = lastFocusedTabs[0];
    if (tab.url && (tab.url.startsWith("http://") || tab.url.startsWith("https://") || tab.url.startsWith("file://"))) {
      return tab;
    }
  }

  // 3. Fallback: Search all open tabs across all windows for the most recent web page
  const allTabs = await new Promise((res) => chrome.tabs.query({}, res));
  if (allTabs && allTabs.length > 0) {
    const webTabs = allTabs.filter(t => t.url && (t.url.startsWith("http://") || t.url.startsWith("https://") || t.url.startsWith("file://")));
    if (webTabs.length > 0) {
      return webTabs.find(t => t.active) || webTabs[webTabs.length - 1];
    }
    return allTabs[0];
  }
  return null;
}

/**
 * Safe screenshot capture wrapped in a 1200ms timeout promise.
 * Guaranteed never to hang even if window focus is lost or callback is dropped.
 */
async function safeCaptureScreenshot(windowId = null, timeoutMs = 1200) {
  return new Promise((resolve) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        resolve(null);
      }
    }, timeoutMs);

    try {
      chrome.tabs.captureVisibleTab(windowId, { format: "jpeg", quality: 75 }, (dataUrl) => {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          if (chrome.runtime.lastError || !dataUrl) {
            resolve(null);
          } else {
            resolve(dataUrl);
          }
        }
      });
    } catch {
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        resolve(null);
      }
    }
  });
}

/**
 * Extracts DOM and interactive elements with automatic functional script fallback.
 */
async function extractPageFromTab(tabId) {
  let pageData = null;
  // 1. Try file injection
  try {
    const injectionResults = await chrome.scripting.executeScript({
      target: { tabId },
      files: ["content.js"]
    });
    if (injectionResults && injectionResults[0] && injectionResults[0].result) {
      pageData = injectionResults[0].result;
    }
  } catch (injErr) {
    console.warn("[DarkShield] Content script file injection warning:", injErr);
  }

  // 2. Functional fallback if file injection didn't return data
  if (!pageData) {
    try {
      const fbResults = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
          if (typeof window.__darkshield_extract_page === "function") {
            try { return window.__darkshield_extract_page(); } catch {}
          }
          const rawText = document.body ? (document.body.innerText || "") : "";
          const rawHtml = document.documentElement ? (document.documentElement.outerHTML || "") : "";
          const links = [];
          const seen = new Set();
          document.querySelectorAll('a[href]').forEach(a => {
            const h = a.href;
            if (h && (h.startsWith('http://') || h.startsWith('https://')) && !seen.has(h)) {
              seen.add(h);
              links.push(h);
            }
          });
          return {
            url: window.location.href,
            title: document.title || "Captured Webpage",
            html: rawHtml.slice(0, 400000),
            visible_text: rawText.slice(0, 100000),
            elements: [],
            discovered_links: links,
            browser_metadata: { source: "darkshield_popup_fallback_extractor" }
          };
        }
      });
      if (fbResults && fbResults[0] && fbResults[0].result) {
        pageData = fbResults[0].result;
      }
    } catch (fbErr) {
      console.warn("[DarkShield] Functional fallback extraction warning:", fbErr);
    }
  }

  return pageData;
}

// -------------------------------------------------
// TAB INITIALIZATION & ACTIVE SCAN STATUS RECOVERY
// -------------------------------------------------

getTargetTab().then(async (detectedTab) => {
  if (!detectedTab) {
    tabTitle.innerText = "No active tab detected";
    return;
  }
  currentTab = detectedTab;
  tabTitle.innerText = currentTab.title || "Untitled Tab";
  tabUrl.innerText = currentTab.url || "N/A";

  let hostname = "this website";
  try {
    hostname = new URL(currentTab.url).hostname;
  } catch {}
  if (siteDomainText) siteDomainText.innerText = hostname;
  if (siteProgDomain) siteProgDomain.innerText = hostname;

  const isHttp = currentTab.url && (
    currentTab.url.startsWith("http://") ||
    currentTab.url.startsWith("https://") ||
    currentTab.url.startsWith("file://")
  );

  const isOnline = await checkBackendHealth();

  if (isHttp && isOnline) {
    btnAnalyze.disabled = false;
    btnWholeWebsiteToggle.disabled = false;
  } else if (!isHttp) {
    btnAnalyze.disabled = true;
    btnWholeWebsiteToggle.disabled = true;
    showError("Content script unavailable: Script injection failed on this tab. DarkShield AI inspects HTTP, HTTPS, or local test webpages.");
  }

  // Check if a whole website scan is currently running or completed in background
  const restoreScanState = (state) => {
    if (!state) return;
    const s = state.lastScan || state;
    const isCrawling = s.active || s.status === "crawling" || s.status === "initializing";
    const isDone = s.status === "completed" || s.status === "cancelled";

    if (isCrawling) {
      latestWebsiteScanId = s.scanId;
      showWebsiteProgressView(s);
      startTimer(Date.now() - ((s.elapsedSeconds || 0) * 1000));
      startStatusPolling(s.scanId);
    } else if (isDone && s.summary) {
      latestWebsiteScanId = s.scanId;
      renderWebsiteResults(s.summary, s.pages || []);
    } else if (isDone && s.scanId) {
      latestWebsiteScanId = s.scanId;
      fetch(`${API_BASE}/scan/website/${s.scanId}`)
        .then(r => r.json())
        .then(summary => {
          fetch(`${API_BASE}/scan/website/${s.scanId}/pages`)
            .then(pr => pr.json())
            .then(pdata => renderWebsiteResults(summary, pdata.pages || []))
            .catch(() => renderWebsiteResults(summary, []));
        })
        .catch(() => {});
    }
  };

  const checkStorageFallback = () => {
    chrome.storage.local.get("darkshield_website_scan", (res) => {
      if (res && res.darkshield_website_scan) {
        const item = res.darkshield_website_scan;
        restoreScanState(item);
      }
    });
  };

  sendRuntimeMessage({ type: "GET_SCAN_STATUS" })
    .then((response) => {
      if (!response) {
        checkStorageFallback();
        return;
      }
      restoreScanState(response);
    })
    .catch((err) => {
      console.warn("[DarkShield] Dormant service worker on popup open, reading storage:", err);
      checkStorageFallback();
    });
});

// -------------------------------------------------
// BUTTON: ANALYZE CURRENT PAGE (SINGLE PAGE MODE)
// -------------------------------------------------

btnAnalyze.addEventListener("click", async () => {
  if (!currentTab || !currentTab.id) return;
  clearError();
  btnAnalyze.disabled = true;
  btnWholeWebsiteToggle.disabled = true;
  wholeSitePanel.classList.add("hidden");
  resultsSection.classList.add("hidden");
  siteResultsSection.classList.add("hidden");

  try {
    // 1. Extract DOM & interactive elements via content script injection with functional fallback
    updateSingleProgress(1, 4, "Extracting rendered DOM & interactive elements...", "Reading buttons, links, inputs, and layout");
    const pageData = await extractPageFromTab(currentTab.id);
    if (!pageData) {
      throw new Error("Content script unavailable: Script injection failed on this tab. DarkShield AI inspects HTTP, HTTPS, or local test webpages.");
    }

    // 2. Capture visible viewport screenshot with safe 1200ms timeout
    updateSingleProgress(2, 4, "Capturing viewport screenshot...", "Encoding visible canvas for Vision AI pipeline");
    const screenshotDataUrl = await safeCaptureScreenshot(currentTab.windowId || null, 1200);

    // 3. Assemble payload and dispatch to POST /scan/capture
    updateSingleProgress(3, 4, "Transmitting data to DarkShield AI engine...", "Sending DOM and visual signals to local analyzer");

    const payload = {
      url: pageData.url || currentTab.url,
      title: pageData.title || currentTab.title,
      html: pageData.html,
      visible_text: pageData.visible_text,
      elements: pageData.elements,
      screenshot: screenshotDataUrl,
      browser_metadata: pageData.browser_metadata
    };

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 35000);

    let response = null;
    try {
      response = await fetch(`${API_BASE}/scan/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
    } catch (fetchErr) {
      clearTimeout(timeoutId);
      if (fetchErr.name === "AbortError") {
        throw new Error("Analysis request timed out after 35 seconds. Please try again.");
      }
      throw new Error(`Backend unreachable: DarkShield API is offline at ${API_BASE}. Please start FastAPI on port 8000.`);
    }
    clearTimeout(timeoutId);

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const detail = errData.detail || errData.message || response.statusText || "Server error";
      throw new Error(`Invalid API response (HTTP ${response.status}): ${detail}`);
    }

    // 4. Processing results
    updateSingleProgress(4, 4, "Analyzing patterns with Calibrated Linear SVM V2 & Rules...", "Finalizing multi-factor deceptive design score");
    const scanResult = await response.json();
    latestSingleScanId = scanResult.scan_id;

    renderSingleResults(scanResult);

  } catch (err) {
    console.error("[DarkShield Extension] Capture error:", err);
    showError(formatExtensionError(err));
  } finally {
    progressSection.classList.add("hidden");
    btnAnalyze.disabled = false;
    btnWholeWebsiteToggle.disabled = false;
  }
});

function renderSingleResults(result) {
  resultsSection.classList.remove("hidden");
  actionSection.classList.add("hidden");

  const darkAnalysis = result.dark_pattern_analysis || {};
  const isBlocked = result.access_blocked || result.status === "blocked";
  const riskScore = isBlocked ? null : (darkAnalysis.risk_score !== undefined ? darkAnalysis.risk_score : result.risk_score);
  const findings = darkAnalysis.findings || result.findings || [];

  resScore.innerText = riskScore !== null && riskScore !== undefined ? riskScore : "N/A";
  const badgeClass = getRiskBadgeClass(riskScore);
  const badgeLevel = isBlocked ? "Access Blocked" : getRiskLevelName(riskScore);

  resRiskBadge.className = `risk-badge ${badgeClass}`;
  resRiskBadge.innerText = badgeLevel;

  resPatternsCount.innerText = isBlocked
    ? "Analysis Withheld"
    : `${findings.length} deceptive pattern${findings.length === 1 ? "" : "s"} detected`;

  // Render pattern items
  patternsList.innerHTML = "";
  if (isBlocked) {
    const blockedItem = document.createElement("div");
    blockedItem.className = "pattern-item";
    blockedItem.style.borderLeftColor = "#94a3b8";
    blockedItem.innerHTML = `
      <div class="pattern-name" style="color: #cbd5e1;">⚠️ Access Barrier Encountered</div>
      <div class="pattern-evidence">${(result.message || "Anti-bot barrier active. Deceptive design analysis withheld.").replace(/"/g, '&quot;')}</div>
    `;
    patternsList.appendChild(blockedItem);
  } else if (findings.length === 0) {
    const emptyItem = document.createElement("div");
    emptyItem.className = "pattern-item";
    emptyItem.style.borderLeftColor = "#10b981";
    emptyItem.innerHTML = `
      <div class="pattern-name" style="color: #34d399;">✓ No Deceptive Patterns Detected</div>
      <div class="pattern-evidence">Rendered interface complies with transparent design guidelines.</div>
    `;
    patternsList.appendChild(emptyItem);
  } else {
    findings.slice(0, 5).forEach((p) => {
      const pItem = document.createElement("div");
      pItem.className = "pattern-item";
      const confPct = Math.round((p.confidence || 0.9) * 100);
      const pCategory = p.pattern || p.pattern_category || p.category || p.pattern_type || "Deceptive Design";
      let rawSnippet = p.evidence_text || p.context || p.evidence || "Interface element signature match";
      if (Array.isArray(rawSnippet)) {
        rawSnippet = rawSnippet[0] || "Interface element signature match";
      }
      const evidenceSnippet = String(rawSnippet);
      pItem.innerHTML = `
        <div class="pattern-name">
          <span>${pCategory}</span>
          <span class="pattern-conf">${confPct}%</span>
        </div>
        <div class="pattern-evidence">"${evidenceSnippet.replace(/"/g, '&quot;')}"</div>
      `;
      patternsList.appendChild(pItem);
    });
  }
}

// -------------------------------------------------
// BUTTON: SCAN WHOLE WEBSITE (TOGGLE & START)
// -------------------------------------------------

// Toggle whole website configuration panel
btnWholeWebsiteToggle.addEventListener("click", () => {
  clearError();
  const isHidden = wholeSitePanel.classList.contains("hidden");
  if (isHidden) {
    wholeSitePanel.classList.remove("hidden");
    wholeSitePanel.scrollIntoView({ behavior: "smooth" });
  } else {
    wholeSitePanel.classList.add("hidden");
  }
});

btnCloseSitePanel.addEventListener("click", () => {
  wholeSitePanel.classList.add("hidden");
});

// Start whole website crawl
btnStartSiteScan.addEventListener("click", async () => {
  if (!currentTab || !currentTab.url) return;
  clearError();

  // Clear any previous triggers
  try {
    await chrome.storage.local.remove(["darkshield_pending_crawl", "darkshield_cancel_crawl"]);
  } catch {}

  const maxPages = parseInt(selectMaxPages.value, 10) || 20;
  const maxDepth = parseInt(selectMaxDepth.value, 10) || 2;
  const targetUrl = currentTab.url;

  if (!targetUrl.startsWith("http://") && !targetUrl.startsWith("https://") && !targetUrl.startsWith("file://")) {
    showError("Invalid page URL. Whole website scan requires an HTTP, HTTPS, or local test webpage.");
    return;
  }

  const t_start = Date.now();
  console.log(`[DarkShield Timing] Whole website scan initiated at ${new Date().toISOString()} for target: ${targetUrl}`);

  btnStartSiteScan.disabled = true;
  const originalBtnHtml = btnStartSiteScan.innerHTML;
  btnStartSiteScan.innerHTML = '<span class="spinner-small"></span> <span>Extracting Active Page...</span>';

  // 1. Immediate Initial Page Capture (Page 1) directly from user's active tab
  // Guarantees zero deadlock and delivers instant findings within ~2s
  console.log("[DarkShield Timing] Capturing active tab (Page 1) content directly...");
  const initialPageData = await extractPageFromTab(currentTab.id);
  const initialScreenshot = await safeCaptureScreenshot(currentTab.windowId || null, 1200);
  console.log(`[DarkShield Timing] Initial page captured in ${Date.now() - t_start}ms`);
  console.log(`[DarkShield Scan init] [Initial page captured] ${targetUrl} - Title: ${initialPageData ? initialPageData.title : "Initial Webpage"}, Elements: ${initialPageData ? initialPageData.elements.length : 0}`);

  // 2. Pre-flight session initialization directly with backend
  btnStartSiteScan.innerHTML = '<span class="spinner-small"></span> <span>Initializing Scan Session...</span>';
  let scanData = null;
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 12000);

    let startRes = null;
    try {
      startRes = await fetch(`${API_BASE}/scan/website/browser/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: targetUrl,
          max_pages: maxPages,
          max_depth: maxDepth,
          allow_subdomains: false,
          allow_local: true
        }),
        signal: controller.signal
      });
    } catch (fetchErr) {
      clearTimeout(timeoutId);
      if (fetchErr.name === "AbortError") {
        throw new Error(`Connection to DarkShield backend timed out (12s) at ${API_BASE}. Please verify FastAPI is running.`);
      }
      if (fetchErr.message && fetchErr.message.includes("Failed to fetch")) {
        throw new Error(`Backend unreachable: DarkShield API is offline at ${API_BASE}. Please start FastAPI on port 8000.`);
      }
      throw new Error(`Backend unreachable: DarkShield API is offline at ${API_BASE}. Please start FastAPI on port 8000.`);
    }
    clearTimeout(timeoutId);

    if (!startRes.ok) {
      const errBody = await startRes.json().catch(() => ({}));
      const detail = errBody.detail || errBody.message || startRes.statusText || "Server error";
      if (startRes.status === 404) {
        throw new Error(`Invalid API response (HTTP 404): Endpoint not found at ${API_BASE}/scan/website/browser/start. Please ensure the latest DarkShield backend is running.`);
      } else if (startRes.status === 400) {
        throw new Error(`Invalid API response (HTTP 400): ${detail}`);
      } else if (startRes.status === 500) {
        throw new Error(`Invalid API response (HTTP 500): ${detail}`);
      } else {
        throw new Error(`Invalid API response (HTTP ${startRes.status}): ${detail}`);
      }
    }

    scanData = await startRes.json();
    latestWebsiteScanId = scanData.scan_id;
  } catch (err) {
    btnStartSiteScan.disabled = false;
    btnStartSiteScan.innerHTML = originalBtnHtml;
    console.error("[DarkShield] Whole website start failed:", err);
    showError(formatExtensionError(err));
    return;
  }

  btnStartSiteScan.disabled = false;
  btnStartSiteScan.innerHTML = originalBtnHtml;

  // 3. Transition UI to progress tracking view immediately
  actionSection.classList.add("hidden");
  wholeSitePanel.classList.add("hidden");
  resultsSection.classList.add("hidden");
  siteResultsSection.classList.add("hidden");

  const rawDiscovered = initialPageData ? Math.max(1, (initialPageData.discovered_links || []).length + 1) : 1;
  const initialDiscoveredCount = Math.min(maxPages, rawDiscovered);
  siteProgressSection.classList.remove("hidden");
  siteProgressBarFill.style.width = "5%";
  siteStatDiscovered.innerText = String(initialDiscoveredCount);
  siteStatScanned.innerText = "0";
  siteStatBlocked.innerText = "0";
  siteStatFailed.innerText = "0";
  siteCurrentUrl.innerText = targetUrl;
  startTimer();

  // 4. Immediately submit Page 1 to backend to produce an instant deceptive score
  let initialPageRecord = null;
  if (initialPageData) {
    const t_p1 = Date.now();
    console.log("[DarkShield Timing] Submitting initial Page 1 to backend analyzer...");
    try {
      const p1Payload = {
        url: initialPageData.url || targetUrl,
        final_url: initialPageData.url || targetUrl,
        title: initialPageData.title || currentTab.title || "Initial Webpage",
        depth: 0,
        html: initialPageData.html,
        text: initialPageData.visible_text,
        visible_text: initialPageData.visible_text,
        elements: initialPageData.elements,
        screenshot: initialScreenshot,
        browser_metadata: initialPageData.browser_metadata,
        discovered_urls: initialPageData.discovered_links || []
      };

      const p1Controller = new AbortController();
      const p1Timeout = setTimeout(() => p1Controller.abort(), 10000);

      const p1Res = await fetch(`${API_BASE}/scan/website/browser/${scanData.scan_id}/page`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(p1Payload),
        signal: p1Controller.signal
      });
      clearTimeout(p1Timeout);

      if (p1Res.ok) {
        const p1Json = await p1Res.json();
        initialPageRecord = p1Json.page_record;
        console.log(`[DarkShield Scan ${scanData.scan_id}] [Initial page analyzed] ${targetUrl} - Score: ${initialPageRecord.risk_score}, Status: ${initialPageRecord.status || "completed"}`);
        console.log(`[DarkShield Timing] Page 1 analyzed in ${Date.now() - t_p1}ms (Total elapsed: ${Date.now() - t_start}ms) | Score: ${initialPageRecord.risk_score}`);
        siteStatScanned.innerText = `1/${maxPages}`;
        siteProgressBarFill.style.width = "10%";
        updateLiveScoreCard(initialPageRecord);
      }
    } catch (subErr) {
      console.warn("[DarkShield Timing] Immediate Page 1 submission warning:", subErr);
    }
  }

  // 5. Initiate status polling from backend as reliable primary channel
  startStatusPolling(scanData.scan_id);

  // 6. Initiate dedicated background crawl tab via service worker (seeded with Page 1 links)
  // Fail-Safe Dual-Channel Activation:
  // Channel A: Save to chrome.storage.local (fires chrome.storage.onChanged which Chrome wakes the SW for with 100% reliability)
  // Channel B: Send direct runtime message with generous retries
  const crawlPayload = {
    scanId: scanData.scan_id,
    config: {
      url: targetUrl,
      maxPages: maxPages,
      maxDepth: maxDepth,
      allowSubdomains: false,
      allowLocal: true
    },
    initialPageCompleted: Boolean(initialPageRecord),
    initialPageRecord: initialPageRecord,
    discoveredLinks: initialPageData ? initialPageData.discovered_links : []
  };

  // Ensure background service worker is awake and active via PING handshake
  console.log("[DarkShield Timing] Pre-activating service worker via PING handshake...");
  try {
    const pingRes = await sendRuntimeMessage({ type: "PING" }, 12, 200);
    console.log("[DarkShield Timing] Service worker is responsive:", pingRes);
  } catch (pingErr) {
    console.warn("[DarkShield Timing] SW wake-up ping warning:", pingErr?.message || pingErr);
  }

  // Connect long-lived port for real-time progress updates and background keepalive
  try {
    const crawlPort = chrome.runtime.connect({ name: "darkshield_crawl_port" });
    crawlPort.onDisconnect.addListener(() => {
      if (chrome.runtime.lastError) {}
    });
    crawlPort.onMessage.addListener((msg) => {
      if (msg && msg.type === "SCAN_PROGRESS") {
        showWebsiteProgressView(msg);
      }
    });
  } catch (portErr) {
    console.warn("[DarkShield] Optional crawl port connection skipped:", portErr);
  }

  // Primary activation: send direct runtime message to service worker
  console.log(`[DarkShield Timing] Dispatching START_WEBSITE_SCAN for scanId: ${scanData.scan_id}`);
  let swStarted = false;
  try {
    const swRes = await sendRuntimeMessage({
      type: "START_WEBSITE_SCAN",
      ...crawlPayload
    }, 15, 250);

    if (swRes && swRes.ok) {
      swStarted = true;
    } else if (swRes && !swRes.ok) {
      console.warn("[DarkShield] Service worker start response:", swRes.error);
    }
  } catch (swErr) {
    console.log("[DarkShield] Direct runtime message encountered dormancy, activating storage fallback:", swErr?.message || swErr);
  }

  // Fail-Safe Fallback: if direct runtime message failed or service worker was dormant, write to storage
  if (!swStarted) {
    try {
      await chrome.storage.local.set({ darkshield_pending_crawl: crawlPayload });
    } catch (storeErr) {
      console.warn("[DarkShield] Pending crawl storage write error:", storeErr);
    }
  }
});

// Cancel active website scan
btnCancelSiteScan.addEventListener("click", async () => {
  btnCancelSiteScan.disabled = true;
  btnCancelSiteScan.innerText = "Cancelling...";
  stopStatusPolling();

  if (latestWebsiteScanId) {
    try {
      await fetch(`${API_BASE}/scan/website/browser/${latestWebsiteScanId}/cancel`, { method: "POST" });
    } catch (e) {}
  }

  try {
    await chrome.storage.local.set({ darkshield_cancel_crawl: { timestamp: Date.now() } });
  } catch (e) {}

  try {
    await sendRuntimeMessage({ type: "CANCEL_WEBSITE_SCAN" }, 3, 200);
  } catch (e) {
    console.warn("[DarkShield] Service worker cancel notification skipped:", e);
  } finally {
    btnCancelSiteScan.disabled = false;
    btnCancelSiteScan.innerText = "⏹️ Cancel Scan";
  }

  // Fetch partial results after cancellation
  if (latestWebsiteScanId) {
    setTimeout(async () => {
      try {
        const [sumRes, pagesRes] = await Promise.all([
          fetch(`${API_BASE}/scan/website/${latestWebsiteScanId}`),
          fetch(`${API_BASE}/scan/website/${latestWebsiteScanId}/pages`)
        ]);
        if (sumRes.ok && pagesRes.ok) {
          const sumData = await sumRes.json();
          const pData = await pagesRes.json();
          renderWebsiteResults(sumData.summary || sumData, pData.pages || []);
        }
      } catch (e) {}
    }, 500);
  }
});

function showWebsiteProgressView(state) {
  actionSection.classList.add("hidden");
  wholeSitePanel.classList.add("hidden");
  resultsSection.classList.add("hidden");
  siteResultsSection.classList.add("hidden");
  siteProgressSection.classList.remove("hidden");

  const scanned = state.pagesScanned || 0;
  const maxP = state.maxPages || 20;
  const discovered = Math.min(maxP, Math.max(scanned, state.pagesDiscovered || 1));
  const target = Math.min(maxP, discovered);
  const pct = Math.min(98, Math.round((scanned / Math.max(1, target)) * 100));

  siteProgressBarFill.style.width = `${pct}%`;
  siteStatDiscovered.innerText = String(discovered);
  siteStatScanned.innerText = `${scanned}/${maxP}`;
  siteStatBlocked.innerText = String(state.pagesBlocked || 0);
  const failed = (state.pagesFailed || 0) + (state.pagesTimedOut || 0);
  siteStatFailed.innerText = String(failed);
  siteCurrentUrl.innerText = state.current_stage || state.stage || state.currentUrl || "Processing pages...";

  if (state.first_page) {
    updateLiveScoreCard(state.first_page);
  } else if (state.firstPage) {
    updateLiveScoreCard(state.firstPage);
  } else if (state.pages && state.pages.length > 0) {
    updateLiveScoreCard(state.pages[0]);
  }

  // Live completed pages stream (Real-time updates as pages complete)
  if (state.pages && state.pages.length > 0 && siteLiveStreamBox && siteLiveStreamList) {
    siteLiveStreamBox.classList.remove("hidden");
    if (siteLiveStreamCount) siteLiveStreamCount.innerText = String(state.pages.length);
    siteLiveStreamList.innerHTML = state.pages.slice(-5).map((p, pIdx) => {
      const pBlocked = Boolean(p.access_blocked || p.status === "blocked");
      const pScore = p.risk_score;
      const bClass = getRiskBadgeClass(pScore);
      const bText = pBlocked
        ? "Blocked"
        : (p.status === "timed_out" ? "Timed Out" : (p.status === "failed" ? "Failed" : (pScore !== null && pScore !== undefined ? `${pScore}/100` : "Assessing")));
      const displayUrl = (p.url || "").replace(/^https?:\/\//, "");
      return `
        <div class="live-stream-item">
          <span class="live-stream-url" title="${(p.url || '').replace(/"/g, '&quot;')}">${displayUrl}</span>
          <span class="risk-badge ${bClass}" style="font-size: 8px; padding: 1px 5px;">${bText}</span>
        </div>
      `;
    }).join("");
  }
}

// -------------------------------------------------
// RENDER WHOLE WEBSITE RESULTS & PAGE-BY-PAGE AUDIT
// -------------------------------------------------

function renderWebsiteResults(summary, pages = []) {
  stopTimer();
  stopStatusPolling();
  siteProgressSection.classList.add("hidden");
  actionSection.classList.add("hidden");
  siteResultsSection.classList.remove("hidden");

  summary = summary || {};
  pages = pages || [];
  latestWebsiteScanId = summary.scan_id || latestWebsiteScanId;

  // 1. Target Website Domain and Starting URL
  const targetUrl = summary.base_url || (pages[0] && pages[0].url) || (currentTab && currentTab.url) || "https://example.com/";
  let domain = "Target Website";
  try {
    domain = new URL(targetUrl).hostname;
  } catch {}
  const targetTitle = summary.site_title || (pages[0] && pages[0].title) || domain;
  if (siteResTargetTitle) siteResTargetTitle.innerText = targetTitle;
  if (siteResTargetUrl) siteResTargetUrl.innerText = targetUrl;

  // 2. Overall Scan Status
  const rawStatus = (summary.scan_status || summary.status || "completed").toLowerCase();
  const isPartial = Boolean(
    summary.is_partial_scan ||
    summary.incomplete_within_target ||
    summary.limit_reached ||
    rawStatus === "cancelled" ||
    (summary.pages_timed_out > 0 || summary.pages_failed > 0 || summary.pages_blocked > 0)
  );

  if (siteResStatusPill) {
    siteResStatusPill.className = "site-status-pill";
    if (rawStatus === "cancelled") {
      siteResStatusPill.classList.add("status-cancelled");
      siteResStatusPill.innerText = "⏹️ Cancelled (Partial)";
    } else if (rawStatus === "completed" && isPartial) {
      siteResStatusPill.classList.add("status-incomplete");
      siteResStatusPill.innerText = "⚠️ Incomplete (Partial)";
    } else if (rawStatus === "completed") {
      siteResStatusPill.classList.add("status-completed");
      siteResStatusPill.innerText = "✓ Completed";
    } else {
      siteResStatusPill.classList.add("status-incomplete");
      siteResStatusPill.innerText = "⚠️ Incomplete";
    }
  }

  // 3. Website Risk Summary Card (Matches single-page style)
  const score = summary.website_risk_score;
  const isScoreValid = score !== null && score !== undefined;
  const level = summary.website_risk_level || (isScoreValid ? (score === 0 ? "Clean" : getRiskLevelName(score)) : "Insufficient Data");
  const badgeClass = getRiskBadgeClass(score);

  siteResScore.innerText = isScoreValid ? String(score) : "N/A";
  siteResRiskBadge.className = `risk-badge ${badgeClass}`;
  siteResRiskBadge.innerText = level;

  // Count unique findings across pages
  const uniqueCount = summary.total_unique_findings !== undefined
    ? summary.total_unique_findings
    : (() => {
        const seen = new Set();
        pages.forEach(p => {
          (p.findings || []).forEach(f => {
            const pat = f.pattern || f.category || "Deceptive Design";
            const text = f.exact_text || (Array.isArray(f.evidence) ? f.evidence[0] : f.evidence) || "";
            seen.add(`${pat}::${text}`);
          });
        });
        return seen.size;
      })();

  siteResSummaryText.innerText = uniqueCount === 0
    ? (isScoreValid ? "0 deceptive patterns detected" : "Insufficient data for pattern analysis")
    : `${uniqueCount} unique deceptive pattern${uniqueCount === 1 ? "" : "s"} detected`;

  // 4. Coverage Information & Methodology Note
  const maxPages = summary.config?.max_pages || summary.max_pages || 20;
  const discoveredCount = summary.total_pages_discovered || summary.pages_discovered || Math.max(pages.length, 1);
  const analyzedCount = pages.length;
  const coveragePct = summary.coverage_percentage !== undefined
    ? summary.coverage_percentage
    : Math.min(100, Math.round((analyzedCount / Math.max(1, discoveredCount)) * 100));

  if (siteResCoverage) {
    siteResCoverage.innerText = `${analyzedCount}/${discoveredCount} pages analyzed (${coveragePct}% coverage)`;
  }

  const isIncomplete = Boolean(
    summary.incomplete_within_target ||
    summary.limit_reached ||
    (analyzedCount < discoveredCount && rawStatus === "cancelled")
  );

  if (siteResIncompleteTag) {
    if (isIncomplete) {
      siteResIncompleteTag.classList.remove("hidden");
      siteResIncompleteTag.innerText = summary.limit_reached
        ? `⚡ Limit Reached (${maxPages}p)`
        : "⚠️ Incomplete Coverage";
    } else {
      siteResIncompleteTag.classList.add("hidden");
    }
  }

  if (siteResMethodology) {
    siteResMethodology.innerText = summary.methodology_note ||
      "Website Deception Index: 50% Peak Page Score + 30% Average Page Score + 20% Category Diversity across inspected pages.";
  }

  // 5. Overview Tallies
  const cleanCount = summary.pages_clean !== undefined
    ? summary.pages_clean
    : pages.filter(p => !p.access_blocked && p.status === "completed" && (p.risk_score === 0 || (p.findings_count === 0 && (!p.findings || p.findings.length === 0)))).length;

  const patternCount = summary.pages_with_dark_patterns !== undefined
    ? summary.pages_with_dark_patterns
    : pages.filter(p => !p.access_blocked && (p.findings_count > 0 || (p.findings && p.findings.length > 0))).length;

  const blockedCount = summary.pages_blocked !== undefined
    ? summary.pages_blocked
    : pages.filter(p => Boolean(p.access_blocked || p.status === "blocked")).length;

  const timedOutCount = summary.pages_timed_out !== undefined
    ? summary.pages_timed_out
    : pages.filter(p => p.status === "timed_out").length;

  const failedCount = summary.pages_failed !== undefined
    ? summary.pages_failed
    : pages.filter(p => p.status === "failed").length;

  pillScanned.innerText = `${analyzedCount} Scanned`;
  pillClean.innerText = `${cleanCount} Clean`;
  pillPatterns.innerText = `${patternCount} With Patterns`;
  pillBlocked.innerText = `${blockedCount} Blocked`;

  if (pillTimedOut) {
    if (timedOutCount > 0) {
      pillTimedOut.classList.remove("hidden");
      pillTimedOut.innerText = `${timedOutCount} Timed Out`;
    } else {
      pillTimedOut.classList.add("hidden");
    }
  }

  if (pillFailed) {
    if (failedCount > 0) {
      pillFailed.classList.remove("hidden");
      pillFailed.innerText = `${failedCount} Failed`;
    } else {
      pillFailed.classList.add("hidden");
    }
  }

  // 6. Category Breakdown
  const catCounts = summary.category_counts || {};
  const catKeys = Object.keys(catCounts);
  if (catKeys.length > 0) {
    siteCategoryBreakdown.classList.remove("hidden");
    siteCategoryBreakdown.innerHTML = catKeys.map(cat => {
      return `<span class="cat-pill">${cat}: ${catCounts[cat]}</span>`;
    }).join("");
  } else {
    siteCategoryBreakdown.classList.add("hidden");
  }

  // 7. Page-by-Page Results with Expandable Cards
  auditPageCount.innerText = `${pages.length} page${pages.length === 1 ? "" : "s"}`;
  sitePagesList.innerHTML = "";

  if (pages.length === 0) {
    sitePagesList.innerHTML = `<div class="card" style="font-size: 11px; color: var(--text-muted); text-align: center; padding: 12px;">No individual page records available.</div>`;
    return;
  }

  pages.forEach((p, idx) => {
    const pCard = document.createElement("div");
    pCard.className = "page-audit-card";
    pCard.dataset.pageId = p.page_id || `page_${idx + 1}`;

    const isBlocked = Boolean(p.access_blocked || p.status === "blocked");
    const isTimedOut = p.status === "timed_out";
    const isFailed = p.status === "failed";
    const pScore = p.risk_score;
    const pFindings = p.findings || [];
    const isClean = !isBlocked && !isTimedOut && !isFailed && (pScore === 0 || pFindings.length === 0);

    let pBadgeClass = "risk-clean";
    let pScoreText = "0/100";
    let pBadgeLabel = "Clean";

    if (isBlocked) {
      pBadgeClass = "risk-blocked";
      pScoreText = "Blocked";
      pBadgeLabel = "Blocked";
    } else if (isTimedOut) {
      pBadgeClass = "risk-blocked";
      pScoreText = "Timed Out";
      pBadgeLabel = "Timed Out";
    } else if (isFailed) {
      pBadgeClass = "risk-blocked";
      pScoreText = "Failed";
      pBadgeLabel = "Failed";
    } else if (pScore !== null && pScore !== undefined) {
      pScoreText = `${pScore}/100`;
      pBadgeClass = getRiskBadgeClass(pScore);
      pBadgeLabel = getRiskLevelName(pScore);
    }

    const hasSnapshot = Boolean(p.has_screenshot || p.screenshot_url);
    const snapUrl = p.screenshot_url
      ? (p.screenshot_url.startsWith("http") ? p.screenshot_url : `${API_BASE}${p.screenshot_url}`)
      : `${API_BASE}/scan/website/${latestWebsiteScanId}/pages/${p.page_id}/screenshot`;

    const snapBadgeHtml = hasSnapshot
      ? `<span class="page-snapshot-badge has-snap" title="Click to view captured screenshot">📸 Snapshot</span>`
      : `<span class="page-snapshot-badge no-snap">📸 No Snapshot</span>`;

    // Findings text & items
    let findingsCountLabel = "";
    let findingsListHtml = "";

    if (isBlocked) {
      findingsCountLabel = "Access Barrier Encountered";
      findingsListHtml = `
        <div class="pattern-item" style="border-left-color: #94a3b8;">
          <div class="pattern-name" style="color: #cbd5e1;">⚠️ Access Barrier Encountered</div>
          <div class="pattern-evidence">${(p.message || "Anti-bot barrier active. Deceptive design analysis withheld.").replace(/"/g, '&quot;')}</div>
        </div>
      `;
    } else if (isTimedOut) {
      findingsCountLabel = "Navigation Timed Out";
      findingsListHtml = `
        <div class="pattern-item" style="border-left-color: #f59e0b;">
          <div class="pattern-name" style="color: #fbbf24;">⏱️ Navigation Timed Out</div>
          <div class="pattern-evidence">${(p.message || "Page navigation exceeded readiness deadline (3500ms).").replace(/"/g, '&quot;')}</div>
        </div>
      `;
    } else if (isFailed) {
      findingsCountLabel = "Extraction Failed";
      findingsListHtml = `
        <div class="pattern-item" style="border-left-color: #ef4444;">
          <div class="pattern-name" style="color: #f87171;">❌ Extraction Failed</div>
          <div class="pattern-evidence">${(p.message || "Unable to inspect rendered DOM in background session.").replace(/"/g, '&quot;')}</div>
        </div>
      `;
    } else if (isClean) {
      findingsCountLabel = "✓ 0 deceptive patterns detected";
      findingsListHtml = `
        <div class="pattern-item" style="border-left-color: #10b981;">
          <div class="pattern-name" style="color: #34d399;">✓ No Deceptive Patterns Detected</div>
          <div class="pattern-evidence">Rendered interface complies with transparent design guidelines.</div>
        </div>
      `;
    } else {
      findingsCountLabel = `⚠️ ${pFindings.length} deceptive pattern${pFindings.length === 1 ? '' : 's'} detected`;
      findingsListHtml = pFindings.map(f => {
        const cat = f.pattern || f.category || f.pattern_category || "Deceptive Design";
        const conf = Math.round((f.confidence || 0.9) * 100);
        let evidence = f.exact_text || (Array.isArray(f.evidence) ? f.evidence[0] : f.evidence) || f.evidence_text || "Interface signature match";
        if (typeof evidence !== "string") evidence = String(evidence);
        const reasonHtml = f.reason
          ? `<div style="font-size: 9px; color: var(--text-muted); margin-top: 2px;">${f.reason.replace(/"/g, '&quot;')}</div>`
          : "";
        return `
          <div class="pattern-item">
            <div class="pattern-name">
              <span>${cat}</span>
              <span class="pattern-conf">${conf}%</span>
            </div>
            <div class="pattern-evidence">"${evidence.replace(/"/g, '&quot;')}"</div>
            ${reasonHtml}
          </div>
        `;
      }).join("");
    }

    const snapshotActionHtml = hasSnapshot
      ? `
        <div class="page-snapshot-action">
          <span>Captured Viewport</span>
          <a href="${snapUrl}" target="_blank" class="btn-snapshot-link">
            <span>📸 View Full Snapshot</span>
          </a>
        </div>
      `
      : "";

    // Card starts expanded if it has findings or if it's the first page
    const shouldStartExpanded = pFindings.length > 0 || idx === 0 || isBlocked || isTimedOut;

    pCard.innerHTML = `
      <div class="page-card-header" title="Click to expand/collapse page details">
        <div class="page-info">
          <div class="page-title-row" title="${(p.title || 'Untitled Webpage').replace(/"/g, '&quot;')}">
            ${idx + 1}. ${p.title || "Untitled Webpage"}
          </div>
          <div class="page-url-row" title="${(p.url || '').replace(/"/g, '&quot;')}">${p.url || ''}</div>
          <div class="page-meta-row">
            ${snapBadgeHtml}
            <span class="page-findings-badge">${findingsCountLabel}</span>
          </div>
        </div>
        <div class="page-card-right">
          <div class="page-card-score-box">
            <span class="page-card-score-num">${pScoreText}</span>
          </div>
          <span class="risk-badge ${pBadgeClass}" style="font-size: 9px; padding: 2px 6px;">${pBadgeLabel}</span>
          <button class="page-expand-btn ${shouldStartExpanded ? 'expanded' : ''}" type="button" aria-label="Toggle details">▼</button>
        </div>
      </div>
      <div class="page-card-details ${shouldStartExpanded ? '' : 'hidden'}">
        ${snapshotActionHtml}
        <div class="page-findings-list">
          ${findingsListHtml}
        </div>
      </div>
    `;

    // Click on header toggles expansion
    const cardHeader = pCard.querySelector(".page-card-header");
    const cardDetails = pCard.querySelector(".page-card-details");
    const expandBtn = pCard.querySelector(".page-expand-btn");

    cardHeader.addEventListener("click", (e) => {
      // Don't toggle if clicking snapshot badge directly
      if (e.target.closest(".has-snap")) {
        e.stopPropagation();
        chrome.tabs.create({ url: snapUrl });
        return;
      }
      const isHidden = cardDetails.classList.contains("hidden");
      if (isHidden) {
        cardDetails.classList.remove("hidden");
        expandBtn.classList.add("expanded");
      } else {
        cardDetails.classList.add("hidden");
        expandBtn.classList.remove("expanded");
      }
    });

    sitePagesList.appendChild(pCard);
  });

  if (btnToggleAllPages) {
    const hiddenPanels = sitePagesList.querySelectorAll(".page-card-details.hidden");
    btnToggleAllPages.innerText = hiddenPanels.length > 0 ? "Expand All" : "Collapse All";
  }
}

// -------------------------------------------------
// BACKGROUND MESSAGE LISTENER
// -------------------------------------------------

chrome.runtime.onMessage.addListener((message) => {
  if (message.type === "SCAN_PROGRESS") {
    showWebsiteProgressView(message);
  } else if (message.type === "SCAN_COMPLETED") {
    if (message.status === "failed") {
      stopTimer();
      siteProgressSection.classList.add("hidden");
      actionSection.classList.remove("hidden");
      showError(message.error || "Whole website scan encountered a fatal error.");
    } else {
      renderWebsiteResults(message.summary, message.pages);
    }
  } else if (message.type === "SCAN_CANCELLED") {
    // Check if partial summary exists
    sendRuntimeMessage({ type: "GET_SCAN_STATUS" })
      .then((res) => {
        if (res && res.lastScan) {
          renderWebsiteResults(res.lastScan.summary, res.lastScan.pages);
        } else {
          resetView();
        }
      })
      .catch(() => resetView());
  } else if (message.type === "SCAN_FAILED") {
    stopTimer();
    siteProgressSection.classList.add("hidden");
    actionSection.classList.remove("hidden");
    showError(message.error || "Whole website scan failed.");
  }
});

// -------------------------------------------------
// ACTION BUTTONS (DASHBOARD, PDF, NEW SCAN)
// -------------------------------------------------

// Single page dashboard & PDF
btnOpenDashboard.addEventListener("click", () => {
  const url = latestSingleScanId
    ? `${FRONTEND_BASE}/?scan_id=${latestSingleScanId}`
    : FRONTEND_BASE;
  chrome.tabs.create({ url: url });
});

btnDownloadPdf.addEventListener("click", () => {
  if (latestSingleScanId) {
    const pdfUrl = `${API_BASE}/report/${latestSingleScanId}`;
    chrome.tabs.create({ url: pdfUrl });
  } else {
    showError("No scan ID available for PDF download.");
  }
});

btnSingleNewScan.addEventListener("click", () => {
  resetView();
});

// Whole website dashboard & PDF
btnSiteOpenDashboard.addEventListener("click", () => {
  const url = latestWebsiteScanId
    ? `${FRONTEND_BASE}/?scan_id=${latestWebsiteScanId}`
    : FRONTEND_BASE;
  chrome.tabs.create({ url: url });
});

btnSiteDownloadPdf.addEventListener("click", () => {
  if (latestWebsiteScanId) {
    const pdfUrl = `${API_BASE}/report/website/${latestWebsiteScanId}/pdf`;
    chrome.tabs.create({ url: pdfUrl });
  } else {
    showError("No website scan ID available for PDF download.");
  }
});

btnSiteNewScan.addEventListener("click", () => {
  sendRuntimeMessage({ type: "CLEAR_SAVED_SCAN" })
    .catch(() => {
      chrome.storage.local.remove("darkshield_website_scan");
    })
    .finally(() => {
      resetView();
    });
});

if (btnToggleAllPages) {
  btnToggleAllPages.addEventListener("click", () => {
    const detailPanels = sitePagesList.querySelectorAll(".page-card-details");
    const expandBtns = sitePagesList.querySelectorAll(".page-expand-btn");
    if (!detailPanels || detailPanels.length === 0) return;

    // Check if any panel is currently hidden
    const hasHidden = Array.from(detailPanels).some(panel => panel.classList.contains("hidden"));

    detailPanels.forEach(panel => {
      if (hasHidden) {
        panel.classList.remove("hidden");
      } else {
        panel.classList.add("hidden");
      }
    });

    expandBtns.forEach(btn => {
      if (hasHidden) {
        btn.classList.add("expanded");
      } else {
        btn.classList.remove("expanded");
      }
    });

    btnToggleAllPages.innerText = hasHidden ? "Collapse All" : "Expand All";
  });
}

