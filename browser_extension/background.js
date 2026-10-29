/**
 * DarkShield AI - Background Service Worker (Manifest V3)
 * Manages background whole-website crawling, tab lifecycle isolation,
 * queue processing, bounded timeouts, and backend API synchronization.
 */

const API_BASE = "http://127.0.0.1:8000";

// Crawl Execution & Timeout Limits
const PER_PAGE_TIMEOUT_MS = 10000;       // Strict 10s ceiling per page (nav + extract + analysis)
const OVERALL_SCAN_DEADLINE_MS = 240000; // Strict 240s overall scan deadline (up to 100 pages)
const NAV_READINESS_TIMEOUT_MS = 3500;  // Max 3.5s waiting for DOM readiness
const SCRIPT_INJECT_TIMEOUT_MS = 2000;  // Max 2.0s for script execution
const SCREENSHOT_TIMEOUT_MS = 800;      // Max 800ms for screenshot capture
const BACKEND_FETCH_TIMEOUT_MS = 4000;  // Max 4.0s for backend submission

// Standard tracking parameters to strip during URL normalization
const TRACKING_PARAMS = new Set([
  "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
  "gclid", "gclsrc", "dclid", "fbclid", "msclkid", "twclid", "igshid", "wbraid", "gbraid",
  "mc_eid", "_hsenc", "_hsmi", "ref", "ref_", "tag", "trk", "tracking", "spm", "scm",
  "aff_id", "affiliate", "source", "campaign", "click_id", "sessionid", "session_id", "sid",
  "token", "timestamp", "_t", "_k", "cb", "v_id", "client_id", "fb_action_ids", "fb_action_types"
]);

// Combinatorial e-commerce facet, filter, sorting, and pagination parameters to strip for canonical deduplication
const FACET_PARAMS = new Set([
  "sort", "order", "dir", "direction", "sort_by", "orderby",
  "filter", "filters", "color", "colour", "size", "variant", "sku",
  "page", "p", "pg", "page_no", "page_number", "paged", "pagination", "offset", "limit"
]);

// Binary/media/static file extensions to exclude from crawler
const EXCLUDED_EXTENSIONS = [
  ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp", ".ico",
  ".mp4", ".mp3", ".avi", ".mov", ".wmv", ".webm",
  ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
  ".zip", ".tar", ".gz", ".7z", ".rar", ".exe", ".dmg", ".apk",
  ".css", ".js", ".mjs", ".xml", ".json", ".csv",
  ".woff", ".woff2", ".ttf", ".eot", ".otf"
];

// Destructive / state-changing path keywords regex
const DESTRUCTIVE_REGEX = /\/(logout|signout|delete|remove|destroy|cancel|reset-password|leave|exit|unsubscribe)(\/|$)/i;

// In-flight scan state
let currentCrawl = null;
let activeAbortController = null;

// Top-level startup banner: guarantees immediate diagnostic visibility whenever worker evaluates
console.log("[DarkShield SW] ========================================================");
console.log(`[DarkShield SW] Service Worker evaluated & active at: ${new Date().toISOString()}`);
console.log(`[DarkShield SW] Target Backend: ${API_BASE}`);
console.log("[DarkShield SW] ========================================================");

chrome.runtime.onInstalled.addListener((details) => {
  console.log("[DarkShield SW] Extension installed/updated:", details.reason);
});

/**
 * Long-lived Port Listener for active crawl monitoring and keepalive
 */
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === "darkshield_crawl_port") {
    console.log("[DarkShield SW] Long-lived crawl port connected from popup");
    if (currentCrawl) {
      try {
        port.postMessage({
          type: "SCAN_PROGRESS",
          pagesScanned: currentCrawl.pages.length,
          pagesDiscovered: Math.min(currentCrawl.maxPages, currentCrawl.discoveredUrls.size),
          pagesBlocked: currentCrawl.blockedCount,
          pagesFailed: currentCrawl.failedCount,
          pagesTimedOut: currentCrawl.timedOutCount || 0,
          maxPages: currentCrawl.maxPages,
          currentUrl: currentCrawl.currentUrl,
          pages: currentCrawl.pages,
          first_page: currentCrawl.pages.length > 0 ? currentCrawl.pages[0] : null
        });
      } catch (e) {}
    }
  }
});

/**
 * Top-level Message Listener - registered synchronously at startup
 */
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  const msgType = message ? message.type : "UNKNOWN";
  console.log(`[DarkShield SW] Runtime message received: [${msgType}]`, {
    scanId: message?.scanId,
    url: message?.config?.url,
    sender: sender?.tab ? `tab:${sender.tab.id}` : "popup",
    hasInitialPage: Boolean(message?.initialPageRecord),
    linksCount: message?.discoveredLinks?.length
  });

  if (!message || !message.type) {
    sendResponse({ ok: false, error: "Missing message type" });
    return false;
  }

  // Liveness check
  if (message.type === "PING") {
    console.log("[DarkShield SW] Responding PONG to liveness check.");
    sendResponse({ ok: true, pong: true, time: Date.now() });
    return false;
  }

  if (message.type === "GET_SCAN_STATUS") {
    if (currentCrawl) {
      sendResponse({
        ok: true,
        active: currentCrawl.status === "crawling" || currentCrawl.status === "initializing",
        scanId: currentCrawl.scanId,
        baseUrl: currentCrawl.baseUrl,
        status: currentCrawl.status,
        current_stage: currentCrawl.currentStage || `Crawling page ${currentCrawl.pages.length + 1}/${currentCrawl.maxPages}`,
        stage: currentCrawl.currentStage || `Crawling page ${currentCrawl.pages.length + 1}/${currentCrawl.maxPages}`,
        pagesScanned: currentCrawl.pages.length,
        pagesDiscovered: currentCrawl.discoveredUrls ? currentCrawl.discoveredUrls.size : currentCrawl.pages.length,
        pagesBlocked: currentCrawl.blockedCount,
        pagesFailed: currentCrawl.failedCount,
        pagesTimedOut: currentCrawl.timedOutCount || 0,
        currentUrl: currentCrawl.currentUrl,
        maxPages: currentCrawl.maxPages,
        maxDepth: currentCrawl.maxDepth,
        elapsedSeconds: Math.round((Date.now() - currentCrawl.startTime) / 1000),
        pages: currentCrawl.pages,
        summary: currentCrawl.summary,
        first_page: currentCrawl.pages.length > 0 ? currentCrawl.pages[0] : null,
        error: currentCrawl.error
      });
      return false; // Synchronous response
    } else {
      // Check storage for persisted scan state and auto-resume if active crawl exists
      chrome.storage.local.get("darkshield_website_scan", async (result) => {
        const last = result ? result.darkshield_website_scan : null;
        if (last && (last.status === "crawling" || last.status === "initializing")) {
          const elapsed = (last.elapsedSeconds || 0) * 1000;
          if (elapsed < OVERALL_SCAN_DEADLINE_MS && last.queue && last.queue.length > 0 && (last.pages ? last.pages.length : 0) < (last.maxPages || 20)) {
            console.log(`[DarkShield SW] Auto-resuming crawl ${last.scanId} from storage on GET_SCAN_STATUS: queue=${last.queue.length}, scanned=${last.pages?.length || 0}/${last.maxPages}`);
            currentCrawl = {
              scanId: last.scanId,
              baseUrl: last.baseUrl,
              baseHostname: last.baseHostname,
              maxPages: last.maxPages || 20,
              maxDepth: last.maxDepth || 2,
              allowSubdomains: Boolean(last.allowSubdomains || last.config?.allowSubdomains),
              allowLocal: last.allowLocal !== false && last.config?.allowLocal !== false,
              scanTabId: null,
              status: "crawling",
              startTime: Date.now() - elapsed,
              currentUrl: last.currentUrl,
              queue: last.queue || [],
              visitedUrls: new Set(last.visitedUrls || []),
              discoveredUrls: new Set(last.discoveredUrlsList || [last.baseUrl]),
              pages: last.pages || [],
              blockedCount: last.pagesBlocked || 0,
              failedCount: last.pagesFailed || 0,
              timedOutCount: last.pagesTimedOut || 0,
              cancelled: false,
              limitReached: false,
              currentStage: last.current_stage || "Resuming crawl...",
              stage: last.stage || "Resuming crawl...",
              summary: null,
              error: null
            };
            runCrawlLoop(currentCrawl);
            sendResponse({
              ok: true,
              active: true,
              scanId: currentCrawl.scanId,
              baseUrl: currentCrawl.baseUrl,
              status: currentCrawl.status,
              current_stage: currentCrawl.currentStage,
              stage: currentCrawl.stage,
              pagesScanned: currentCrawl.pages.length,
              pagesDiscovered: currentCrawl.discoveredUrls ? currentCrawl.discoveredUrls.size : currentCrawl.pages.length,
              pagesBlocked: currentCrawl.blockedCount,
              pagesFailed: currentCrawl.failedCount,
              pagesTimedOut: currentCrawl.timedOutCount || 0,
              currentUrl: currentCrawl.currentUrl,
              maxPages: currentCrawl.maxPages,
              maxDepth: currentCrawl.maxDepth,
              elapsedSeconds: Math.round((Date.now() - currentCrawl.startTime) / 1000),
              pages: currentCrawl.pages,
              summary: currentCrawl.summary,
              first_page: currentCrawl.pages.length > 0 ? currentCrawl.pages[0] : null,
              error: currentCrawl.error
            });
            return;
          }

          if ((last.pages ? last.pages.length : 0) >= (last.maxPages || 20) || !last.queue || last.queue.length === 0) {
            console.log(`[DarkShield SW] Scan ${last.scanId} finished all pages or queue empty.`);
            last.status = "completed";
            last.current_stage = "Scan completed";
            last.stage = last.current_stage;
            if (last.scanId) {
              await safeFetch(`${API_BASE}/scan/website/browser/${last.scanId}/finish`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  total_discovered: last.pagesDiscovered || last.pagesScanned || 1,
                  scan_status: "completed",
                  limit_reached: true
                })
              }, 3000).catch(() => {});
            }
            await chrome.storage.local.set({ darkshield_website_scan: last }).catch(() => {});
            sendResponse({
              ok: true,
              active: false,
              lastScan: last
            });
            return;
          }
        }
        sendResponse({
          ok: true,
          active: false,
          lastScan: last
        });
      });
      return true; // Asynchronous response via callback
    }
  }

  if (message.type === "START_WEBSITE_SCAN") {
    try {
      if (currentCrawl && (currentCrawl.status === "crawling" || currentCrawl.status === "initializing")) {
        if (currentCrawl.scanId && message.scanId && currentCrawl.scanId === message.scanId) {
          sendResponse({ ok: true, message: "Whole website scan already in progress.", scanId: message.scanId });
          return false;
        }
        console.log(`[DarkShield SW] Preempting previous active crawl ${currentCrawl.scanId} for incoming scan ${message.scanId}`);
        cancelActiveScan();
      }

      executeWholeWebsiteScan(
        message.config,
        message.scanId,
        message.initialPageRecord || null,
        message.discoveredLinks || []
      );
      sendResponse({ ok: true, message: "Whole website scan started.", scanId: message.scanId });
      return false; // Synchronous response
    } catch (err) {
      console.error("[DarkShield] Service worker failed to start website scan:", err);
      sendResponse({ ok: false, error: err.message || "Failed to start website crawl." });
      return false;
    }
  }

  if (message.type === "CANCEL_WEBSITE_SCAN") {
    cancelActiveScan();
    sendResponse({ ok: true });
    return false; // Synchronous response
  }

  if (message.type === "CLEAR_SAVED_SCAN") {
    currentCrawl = null;
    chrome.storage.local.remove("darkshield_website_scan", () => {
      sendResponse({ ok: true });
    });
    return true; // Asynchronous response
  }

  sendResponse({ ok: false, error: `Unhandled message type: ${message.type}` });
  return false;
});

/**
 * Top-level Storage Listener - fail-safe activation channel for crawl requests
 */
chrome.storage.onChanged.addListener((changes, area) => {
  if (area !== "local") return;
  console.log(`[DarkShield SW] storage.onChanged [${area}]:`, Object.keys(changes));

  if (changes.darkshield_pending_crawl && changes.darkshield_pending_crawl.newValue) {
    const req = changes.darkshield_pending_crawl.newValue;
    chrome.storage.local.remove("darkshield_pending_crawl");
    if (req && req.config && req.scanId) {
      if (currentCrawl && (currentCrawl.status === "crawling" || currentCrawl.status === "initializing")) {
        if (currentCrawl.scanId === req.scanId) {
          return;
        }
        console.log(`[DarkShield SW] Preempting active crawl ${currentCrawl.scanId} for storage-triggered scan: ${req.scanId}`);
        cancelActiveScan();
      }
      console.log(`[DarkShield SW] Received start crawl trigger via storage event for scan: ${req.scanId}`);
      executeWholeWebsiteScan(req.config, req.scanId, req.initialPageRecord || null, req.discoveredLinks || []);
    }
  }

  if (changes.darkshield_cancel_crawl && changes.darkshield_cancel_crawl.newValue) {
    chrome.storage.local.remove("darkshield_cancel_crawl");
    cancelActiveScan();
  }
});

// Check for unhandled pending crawl or active in-flight crawl on service worker start
chrome.storage.local.get(["darkshield_pending_crawl", "darkshield_website_scan"], (result) => {
  if (result && result.darkshield_pending_crawl) {
    const req = result.darkshield_pending_crawl;
    chrome.storage.local.remove("darkshield_pending_crawl");
    if (req && req.config && req.scanId) {
      if (currentCrawl && (currentCrawl.status === "crawling" || currentCrawl.status === "initializing")) {
        if (currentCrawl.scanId === req.scanId) return;
        console.log(`[DarkShield SW] Preempting active crawl on startup for scan: ${req.scanId}`);
        cancelActiveScan();
      }
      console.log(`[DarkShield SW] Processing unhandled pending crawl on startup for scan: ${req.scanId}`);
      executeWholeWebsiteScan(req.config, req.scanId, req.initialPageRecord || null, req.discoveredLinks || []);
      return;
    }
  }

  if (result && result.darkshield_website_scan && !currentCrawl) {
    const last = result.darkshield_website_scan;
    if (last && (last.status === "crawling" || last.status === "initializing")) {
      const elapsed = (last.elapsedSeconds || 0) * 1000;
      if (elapsed < OVERALL_SCAN_DEADLINE_MS && last.queue && last.queue.length > 0 && (last.pages ? last.pages.length : 0) < (last.maxPages || 20)) {
        console.log(`[DarkShield SW] Top-level startup: resuming active crawl ${last.scanId} (queue: ${last.queue.length})`);
        currentCrawl = {
          scanId: last.scanId,
          baseUrl: last.baseUrl,
          baseHostname: last.baseHostname,
          maxPages: last.maxPages || 20,
          maxDepth: last.maxDepth || 2,
          allowSubdomains: Boolean(last.allowSubdomains || last.config?.allowSubdomains),
          allowLocal: last.allowLocal !== false && last.config?.allowLocal !== false,
          scanTabId: null,
          status: "crawling",
          startTime: Date.now() - elapsed,
          currentUrl: last.currentUrl,
          queue: last.queue || [],
          visitedUrls: new Set(last.visitedUrls || []),
          discoveredUrls: new Set(last.discoveredUrlsList || [last.baseUrl]),
          pages: last.pages || [],
          blockedCount: last.pagesBlocked || 0,
          failedCount: last.pagesFailed || 0,
          timedOutCount: last.pagesTimedOut || 0,
          cancelled: false,
          limitReached: false,
          currentStage: last.current_stage || "Resuming crawl...",
          stage: last.stage || "Resuming crawl...",
          summary: null,
          error: null
        };
        runCrawlLoop(currentCrawl);
      }
    }
  }
});

/**
 * Cancels active crawl cleanly, aborting pending requests and closing tabs.
 */
function cancelActiveScan() {
  if (currentCrawl) {
    currentCrawl.cancelled = true;
    currentCrawl.status = "cancelled";
    currentCrawl.currentStage = "Scan cancelled";
    currentCrawl.stage = "Scan cancelled";

    if (activeAbortController) {
      try { activeAbortController.abort(); } catch (e) {}
      activeAbortController = null;
    }

    if (currentCrawl.scanId) {
      safeFetch(`${API_BASE}/scan/website/browser/${currentCrawl.scanId}/cancel`, { method: "POST" }, 2000).catch(() => {});
    }

    if (currentCrawl.scanTabId) {
      chrome.tabs.remove(currentCrawl.scanTabId).catch(() => {});
      currentCrawl.scanTabId = null;
    }

    persistState();
    broadcastMessage("SCAN_CANCELLED");
  }
}

/**
 * Normalizes URL: removes fragments, strips tracking and facet parameters, normalizes slashes,
 * and canonically sorts remaining query arguments.
 */
function normalizeUrl(rawUrl, baseUrl = null) {
  if (!rawUrl || typeof rawUrl !== "string") return null;
  try {
    let u = null;
    try {
      u = new URL(rawUrl.trim(), baseUrl || undefined);
    } catch {
      return null;
    }
    u.hash = "";

    // Remove tracking & combinatorial facet params
    const keysToDelete = [];
    u.searchParams.forEach((_, key) => {
      const k = key.toLowerCase();
      if (
        TRACKING_PARAMS.has(k) ||
        FACET_PARAMS.has(k) ||
        k.startsWith("utm_") ||
        k.startsWith("aff_") ||
        k.startsWith("ref_")
      ) {
        keysToDelete.push(key);
      }
    });
    keysToDelete.forEach(k => u.searchParams.delete(k));

    // Sort remaining query parameters for canonical deduplication
    u.searchParams.sort();

    // Normalize path
    if (u.pathname.length > 1 && u.pathname.endsWith("/")) {
      u.pathname = u.pathname.slice(0, -1);
    }
    // Lowercase protocol and host
    u.protocol = u.protocol.toLowerCase();
    u.hostname = u.hostname.toLowerCase();

    return u.toString();
  } catch {
    return null;
  }
}

/**
 * Checks if target URL belongs to same domain and is safe to crawl.
 */
function isCrawlableUrl(targetUrl, baseHostname, allowSubdomains = false) {
  try {
    const u = new URL(targetUrl);
    if (u.protocol !== "http:" && u.protocol !== "https:" && u.protocol !== "file:") {
      return false;
    }

    const targetHost = u.hostname.toLowerCase();
    const baseHost = baseHostname.toLowerCase();

    // Normalize www vs apex: e.g. meesho.com vs www.meesho.com
    const cleanTargetHost = targetHost.replace(/^www\./, "");
    const cleanBaseHost = baseHost.replace(/^www\./, "");

    const isMatch = (targetHost === baseHost) || (cleanTargetHost === cleanBaseHost) || (
      allowSubdomains && (targetHost.endsWith("." + baseHost) || cleanTargetHost.endsWith("." + cleanBaseHost))
    );

    if (!isMatch) return false;

    // Check destructive path
    if (DESTRUCTIVE_REGEX.test(u.pathname)) return false;

    // Check excluded static extensions
    const pathLower = u.pathname.toLowerCase();
    for (const ext of EXCLUDED_EXTENSIONS) {
      if (pathLower.endsWith(ext)) return false;
    }

    return true;
  } catch {
    return false;
  }
}

/**
 * Safe fetch with strict AbortController timeout. Never hangs indefinitely.
 */
async function safeFetch(url, options = {}, timeoutMs = BACKEND_FETCH_TIMEOUT_MS) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    return res;
  } catch (err) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Safe script execution wrapped in strict timeout promise. Never hangs.
 */
function safeExecuteScript(params, timeoutMs = SCRIPT_INJECT_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (!settled) {
        settled = true;
        resolve(null);
      }
    }, timeoutMs);

    chrome.scripting.executeScript(params)
      .then((results) => {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          resolve(results);
        }
      })
      .catch((err) => {
        if (!settled) {
          settled = true;
          clearTimeout(timer);
          resolve(null);
        }
      });
  });
}

/**
 * Bounded readiness waiter: does not block on endless network streaming.
 * Verifies that the tab has reached complete or interactive state on same host.
 */
function waitForTabReady(tabId, expectedUrl = null, timeoutMs = NAV_READINESS_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let settled = false;
    let timer = null;
    let pollInterval = null;

    const cleanup = () => {
      if (settled) return;
      settled = true;
      if (timer) clearTimeout(timer);
      if (pollInterval) clearInterval(pollInterval);
      chrome.tabs.onUpdated.removeListener(onUpdateListener);
    };

    let expectedHost = null;
    try {
      if (expectedUrl) expectedHost = new URL(expectedUrl).hostname.toLowerCase().replace(/^www\./, "");
    } catch {}

    const onUpdateListener = (updatedTabId, changeInfo, tab) => {
      if (updatedTabId === tabId && changeInfo.status === "complete") {
        let currentHost = null;
        try {
          if (tab && tab.url) currentHost = new URL(tab.url).hostname.toLowerCase().replace(/^www\./, "");
        } catch {}
        if (!expectedHost || !currentHost || currentHost === expectedHost) {
          cleanup();
          resolve("complete");
        }
      }
    };

    chrome.tabs.onUpdated.addListener(onUpdateListener);

    // Fast-path polling after 300ms: check document.readyState
    setTimeout(() => {
      if (settled) return;
      pollInterval = setInterval(async () => {
        if (settled) return;
        try {
          const res = await safeExecuteScript({
            target: { tabId },
            func: () => ({ url: window.location.href, readyState: document.readyState })
          }, 800);
          if (res && res[0] && res[0].result) {
            const { url, readyState } = res[0].result;
            let currentHost = null;
            try { currentHost = new URL(url).hostname.toLowerCase().replace(/^www\./, ""); } catch {}
            if (!expectedHost || currentHost === expectedHost) {
              if (readyState === "complete" || readyState === "interactive") {
                cleanup();
                resolve(readyState);
              }
            }
          }
        } catch {}
      }, 200);
    }, 300);

    timer = setTimeout(() => {
      cleanup();
      resolve("timeout");
    }, timeoutMs);
  });
}

/**
 * Safe screenshot capture wrapped in a strict promise timeout.
 * Guaranteed never to hang even if window focus is lost or callback is dropped.
 */
function safeCaptureScreenshot(timeoutMs = SCREENSHOT_TIMEOUT_MS) {
  return new Promise((resolve) => {
    let resolved = false;
    const timer = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        resolve(null);
      }
    }, timeoutMs);

    try {
      chrome.tabs.captureVisibleTab(null, { format: "jpeg", quality: 60 }, (dataUrl) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timer);
          if (chrome.runtime.lastError || !dataUrl) {
            resolve(null);
          } else {
            resolve(dataUrl);
          }
        }
      });
    } catch {
      if (!resolved) {
        resolved = true;
        clearTimeout(timer);
        resolve(null);
      }
    }
  });
}

/**
 * Browser-side anti-bot heuristic detection (Cloudflare, Akamai, Bot Challenges).
 */
function detectBrowserAccessBlock(title = "", text = "", html = "") {
  const combined = ((title || "") + " " + (text || "").slice(0, 1500)).toLowerCase();
  if (
    combined.includes("just a moment...") ||
    combined.includes("attention required! | cloudflare") ||
    combined.includes("verify you are human") ||
    combined.includes("access denied") ||
    combined.includes("security check to continue") ||
    combined.includes("unusual activity from your computer network") ||
    combined.includes("cf-browser-verification")
  ) {
    if (combined.includes("cloudflare")) return { isBlocked: true, provider: "Cloudflare" };
    if (combined.includes("akamai")) return { isBlocked: true, provider: "Akamai" };
    return { isBlocked: true, provider: "Bot Challenge / WAF" };
  }
  return { isBlocked: false, provider: null };
}

/**
 * Sleep helper
 */
const delay = (ms) => new Promise(r => setTimeout(r, ms));

/**
 * Synchronizes scan stage to backend
 */
async function syncStageToBackend(scanId, stageText, url = null) {
  if (!scanId) return;
  await safeFetch(`${API_BASE}/scan/website/browser/${scanId}/stage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage: stageText, url: url })
  }, 1500);
}

/**
 * Persists current scan state to chrome.storage.local
 */
async function persistState() {
  if (!currentCrawl) return;
  const snapshot = {
    scanId: currentCrawl.scanId,
    baseUrl: currentCrawl.baseUrl,
    baseHostname: currentCrawl.baseHostname,
    status: currentCrawl.status,
    current_stage: currentCrawl.currentStage || "Crawling website pages...",
    stage: currentCrawl.currentStage || "Crawling website pages...",
    pagesScanned: currentCrawl.pages.length,
    pagesDiscovered: currentCrawl.discoveredUrls ? (currentCrawl.discoveredUrls.size || currentCrawl.discoveredUrls.length || currentCrawl.pages.length) : currentCrawl.pages.length,
    pagesBlocked: currentCrawl.blockedCount,
    pagesFailed: currentCrawl.failedCount,
    pagesTimedOut: currentCrawl.timedOutCount || 0,
    currentUrl: currentCrawl.currentUrl,
    maxPages: currentCrawl.maxPages,
    maxDepth: currentCrawl.maxDepth,
    allowSubdomains: currentCrawl.allowSubdomains,
    allowLocal: currentCrawl.allowLocal,
    elapsedSeconds: Math.round((Date.now() - currentCrawl.startTime) / 1000),
    pages: currentCrawl.pages,
    queue: currentCrawl.queue || [],
    visitedUrls: currentCrawl.visitedUrls ? Array.from(currentCrawl.visitedUrls) : [],
    discoveredUrlsList: currentCrawl.discoveredUrls ? Array.from(currentCrawl.discoveredUrls) : [],
    config: {
      url: currentCrawl.baseUrl,
      maxPages: currentCrawl.maxPages,
      maxDepth: currentCrawl.maxDepth,
      allowSubdomains: currentCrawl.allowSubdomains,
      allowLocal: currentCrawl.allowLocal
    },
    summary: currentCrawl.summary || null,
    error: currentCrawl.error || null
  };

  try {
    await chrome.storage.local.set({ darkshield_website_scan: snapshot });
  } catch (e) {
    console.warn("[DarkShield AI] Failed to persist state to storage:", e);
  }
}

/**
 * Broadcasts message to extension views (popup)
 */
function broadcastMessage(type, payload = {}) {
  try {
    chrome.runtime.sendMessage({ type, ...payload }, () => {
      if (chrome.runtime.lastError) {
        // Expected when popup is not open
      }
    });
  } catch {
    // Expected when extension context changes
  }
}

/**
 * Ensures a clean, usable background scan tab exists.
 */
async function ensureCleanScanTab() {
  if (currentCrawl && currentCrawl.scanTabId) {
    try {
      const existing = await chrome.tabs.get(currentCrawl.scanTabId);
      if (existing && existing.id) {
        return existing.id;
      }
    } catch {}
  }

  try {
    const tab = await chrome.tabs.create({ url: "about:blank", active: false });
    if (currentCrawl) currentCrawl.scanTabId = tab.id;
    return tab.id;
  } catch (err) {
    console.error("[DarkShield] Failed to create background scan tab:", err);
    return null;
  }
}

/**
 * Closes the background scan tab cleanly.
 */
async function closeScanTab() {
  if (currentCrawl && currentCrawl.scanTabId) {
    const tabId = currentCrawl.scanTabId;
    currentCrawl.scanTabId = null;
    try {
      await chrome.tabs.remove(tabId);
    } catch {}
  }
}

/**
 * Main background crawling routine.
 */
async function executeWholeWebsiteScan(config, preAssignedScanId = null, initialPageRecord = null, initialDiscoveredLinks = []) {
  const { url, maxPages = 20, maxDepth = 2, allowSubdomains = false, allowLocal = true } = (config || {});

  const normalizedStart = normalizeUrl(url);
  if (!normalizedStart) {
    broadcastMessage("SCAN_FAILED", { error: "Invalid starting URL: unable to normalize address." });
    return;
  }

  const baseObj = new URL(normalizedStart);
  const baseHostname = baseObj.hostname;
  const hasInitialPage = Boolean(initialPageRecord);

  const thisCrawl = {
    scanId: preAssignedScanId || null,
    baseUrl: normalizedStart,
    baseHostname: baseHostname,
    maxPages: Math.max(1, Math.min(maxPages, 100)),
    maxDepth: Math.max(0, Math.min(maxDepth, 3)),
    allowSubdomains: allowSubdomains,
    allowLocal: allowLocal,
    scanTabId: null,
    status: preAssignedScanId ? "crawling" : "initializing",
    startTime: Date.now(),
    currentUrl: normalizedStart,
    queue: [],
    visitedUrls: new Set(hasInitialPage ? [normalizedStart] : []),
    discoveredUrls: new Set([normalizedStart]),
    pages: hasInitialPage ? [initialPageRecord] : [],
    blockedCount: (hasInitialPage && initialPageRecord.access_blocked) ? 1 : 0,
    failedCount: 0,
    timedOutCount: 0,
    cancelled: false,
    limitReached: false,
    currentStage: hasInitialPage ? "Initial page analyzed, processing crawl queue" : "Scan initialized",
    stage: hasInitialPage ? "Initial page analyzed, processing crawl queue" : "Scan initialized",
    summary: null,
    error: null
  };
  currentCrawl = thisCrawl;

  console.log(`[DarkShield Scan ${currentCrawl.scanId || preAssignedScanId || "init"}] [Scan started] ${normalizedStart} - maxPages=${currentCrawl.maxPages}, maxDepth=${currentCrawl.maxDepth}`);
  if (hasInitialPage) {
    console.log(`[DarkShield Scan ${currentCrawl.scanId || preAssignedScanId}] [Initial page captured] ${initialPageRecord.url || normalizedStart} - Title: ${initialPageRecord.title || "Initial Webpage"}`);
    console.log(`[DarkShield Scan ${currentCrawl.scanId || preAssignedScanId}] [Initial page analyzed] ${initialPageRecord.url || normalizedStart} - Score: ${initialPageRecord.risk_score}, Status: ${initialPageRecord.status || "completed"}`);
  }

  // Seed BFS queue with internal links discovered from initial page (strictly bounded by maxPages)
  if (hasInitialPage && initialDiscoveredLinks && Array.isArray(initialDiscoveredLinks)) {
    for (const rawHref of initialDiscoveredLinks) {
      if (currentCrawl.discoveredUrls.size >= currentCrawl.maxPages) break;
      const normalized = normalizeUrl(rawHref, normalizedStart);
      if (
        normalized &&
        !currentCrawl.discoveredUrls.has(normalized) &&
        isCrawlableUrl(normalized, currentCrawl.baseHostname, currentCrawl.allowSubdomains)
      ) {
        currentCrawl.discoveredUrls.add(normalized);
        if (currentCrawl.queue.length + currentCrawl.pages.length < currentCrawl.maxPages) {
          currentCrawl.queue.push({ url: normalized, depth: 1 });
          console.log(`[DarkShield Scan ${currentCrawl.scanId || preAssignedScanId}] [URL added to queue] ${normalized} - Depth: 1, Queue length: ${currentCrawl.queue.length}`);
        }
      }
    }
  } else if (!hasInitialPage) {
    currentCrawl.queue.push({ url: normalizedStart, depth: 0 });
  }

  await persistState();
  broadcastMessage("SCAN_STARTED", { scan: currentCrawl });

  await runCrawlLoop(thisCrawl);
}

/**
 * Main Crawl Loop: processes URLs in BFS queue, handles navigation, content extraction,
 * screenshot, timeout limits, risk scoring, link discovery, and finalization.
 */
async function runCrawlLoop(thisCrawl) {
  let keepAliveTimer = null;

  try {
    // 1. Initialize scan session with backend if not already pre-assigned by popup
    if (!thisCrawl.scanId) {
      const startRes = await safeFetch(`${API_BASE}/scan/website/browser/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: thisCrawl.baseUrl,
          max_pages: thisCrawl.maxPages,
          max_depth: thisCrawl.maxDepth,
          allow_subdomains: thisCrawl.allowSubdomains,
          allow_local: thisCrawl.allowLocal
        })
      }, 4000);

      if (!startRes || !startRes.ok) {
        throw new Error(`Server initialization failed: HTTP ${startRes ? startRes.status : "timeout"}`);
      }

      const startData = await startRes.json();
      thisCrawl.scanId = startData.scan_id;
      thisCrawl.status = "crawling";
      await persistState();
    }

    // 2. Initialize dedicated background scan tab
    await ensureCleanScanTab();

    // Service Worker Keepalive Heartbeat: periodic storage touch ensures worker stays responsive
    keepAliveTimer = setInterval(() => {
      if (currentCrawl && (currentCrawl.status === "crawling" || currentCrawl.status === "initializing")) {
        console.log(`[DarkShield SW Heartbeat] active=${currentCrawl.status}, scanId=${currentCrawl.scanId}, queue=${currentCrawl.queue.length}, scanned=${currentCrawl.pages.length}/${currentCrawl.maxPages}`);
        persistState();
      } else {
        clearInterval(keepAliveTimer);
      }
    }, 6000);

    // 3. Main Crawl Loop for Subsequent Pages
    while (thisCrawl.queue.length > 0 && thisCrawl.pages.length < thisCrawl.maxPages) {
      // Check cancellation or preemption
      if (currentCrawl !== thisCrawl || thisCrawl.cancelled) {
        thisCrawl.status = "cancelled";
        break;
      }

      // Check overall scan deadline
      const elapsedOverall = Date.now() - currentCrawl.startTime;
      if (elapsedOverall > OVERALL_SCAN_DEADLINE_MS) {
        console.warn(`[DarkShield Scan ${currentCrawl.scanId}] Overall scan deadline (${OVERALL_SCAN_DEADLINE_MS / 1000}s) reached. Finalizing partial crawl.`);
        currentCrawl.limitReached = true;
        break;
      }

      const item = currentCrawl.queue.shift();
      const targetUrl = item.url;
      const depth = item.depth;

      if (currentCrawl.visitedUrls.has(targetUrl)) {
        continue;
      }

      currentCrawl.visitedUrls.add(targetUrl);
      currentCrawl.currentUrl = targetUrl;
      currentCrawl.currentStage = `Crawling page ${currentCrawl.pages.length + 1}/${currentCrawl.maxPages}: ${targetUrl}`;
      currentCrawl.stage = currentCrawl.currentStage;
      console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Next URL selected] ${targetUrl} - Queue remaining: ${currentCrawl.queue.length}`);
      await syncStageToBackend(currentCrawl.scanId, currentCrawl.currentStage, targetUrl);

      await persistState();
      broadcastMessage("SCAN_PROGRESS", {
        pagesScanned: currentCrawl.pages.length,
        pagesDiscovered: currentCrawl.discoveredUrls.size,
        pagesBlocked: currentCrawl.blockedCount,
        pagesFailed: currentCrawl.failedCount,
        pagesTimedOut: currentCrawl.timedOutCount,
        maxPages: currentCrawl.maxPages,
        currentUrl: targetUrl,
        current_stage: currentCrawl.currentStage,
        stage: currentCrawl.stage,
        pages: currentCrawl.pages,
        first_page: currentCrawl.pages.length > 0 ? currentCrawl.pages[0] : null
      });

      // Execute single page audit with strict overarching per-page deadline
      const pageTimeoutPromise = new Promise((resolve) => {
        setTimeout(() => resolve({ timedOut: true }), PER_PAGE_TIMEOUT_MS);
      });

      let pageOutcome = null;
      try {
        pageOutcome = await Promise.race([
          auditSinglePage(targetUrl, depth),
          pageTimeoutPromise
        ]);
      } catch (err) {
        pageOutcome = { failed: true, error: err.message || "Page execution exception" };
      }

      if (currentCrawl.cancelled) break;

      // Handle outcomes
      if (pageOutcome && pageOutcome.timedOut) {
        currentCrawl.timedOutCount++;
        const failRecord = {
          page_id: `page_${currentCrawl.pages.length + 1}`,
          url: targetUrl,
          title: "Navigation Timed Out",
          depth: depth,
          status: "timed_out",
          access_blocked: false,
          risk_score: null,
          risk_level: "Timed Out",
          findings_count: 0,
          findings: [],
          has_screenshot: false,
          screenshot_url: null,
          message: `Page audit exceeded ${PER_PAGE_TIMEOUT_MS / 1000}s deadline.`
        };

        // Notify backend of timed_out status
        await safeFetch(`${API_BASE}/scan/website/browser/${currentCrawl.scanId}/page`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: targetUrl,
            final_url: targetUrl,
            title: failRecord.title,
            depth: depth,
            status: "timed_out",
            access_blocked: false
          })
        }, 2000).catch(() => {});

        currentCrawl.pages.push(failRecord);
        console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Page marked completed] ${targetUrl} - Terminal status: timed_out`);

        // Close scan tab to prevent stuck navigation from corrupting subsequent pages
        await closeScanTab();

      } else if (pageOutcome && pageOutcome.failed) {
        currentCrawl.failedCount++;
        const failRecord = {
          page_id: `page_${currentCrawl.pages.length + 1}`,
          url: targetUrl,
          title: "Extraction Failed",
          depth: depth,
          status: "failed",
          access_blocked: false,
          risk_score: null,
          risk_level: "Failed",
          findings_count: 0,
          findings: [],
          has_screenshot: false,
          screenshot_url: null,
          message: pageOutcome.error || "Unable to extract rendered DOM in background session."
        };

        await safeFetch(`${API_BASE}/scan/website/browser/${currentCrawl.scanId}/page`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: targetUrl,
            final_url: targetUrl,
            title: failRecord.title,
            depth: depth,
            status: "failed",
            access_blocked: false
          })
        }, 2000).catch(() => {});

        currentCrawl.pages.push(failRecord);
        console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Page marked completed] ${targetUrl} - Terminal status: failed`);

        await closeScanTab();

      } else if (pageOutcome && pageOutcome.pageRecord) {
        const record = pageOutcome.pageRecord;
        currentCrawl.pages.push(record);
        if (record.access_blocked) {
          currentCrawl.blockedCount++;
        }
        console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Risk score calculated] ${targetUrl} - Score: ${record.risk_score}, Level: ${record.risk_level}`);
        console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Page marked completed] ${targetUrl} - Terminal status: ${record.status}`);

        // Discover and enqueue new links from pageOutcome
        if (depth < currentCrawl.maxDepth && pageOutcome.discoveredLinks && pageOutcome.discoveredLinks.length > 0) {
          for (const rawHref of pageOutcome.discoveredLinks) {
            if (currentCrawl.discoveredUrls.size >= currentCrawl.maxPages) break;
            const normalized = normalizeUrl(rawHref, targetUrl);
            if (
              normalized &&
              !currentCrawl.discoveredUrls.has(normalized) &&
              isCrawlableUrl(normalized, currentCrawl.baseHostname, currentCrawl.allowSubdomains)
            ) {
              currentCrawl.discoveredUrls.add(normalized);
              if (currentCrawl.queue.length + currentCrawl.pages.length < currentCrawl.maxPages) {
                currentCrawl.queue.push({ url: normalized, depth: depth + 1 });
                console.log(`[DarkShield Scan ${currentCrawl.scanId}] [URL added to queue] ${normalized} - Depth: ${depth + 1}, Queue length: ${currentCrawl.queue.length}`);
              }
            }
          }
        }
      } else {
        // Fallback for any unhandled or null outcome
        currentCrawl.failedCount++;
        const failRecord = {
          page_id: `page_${currentCrawl.pages.length + 1}`,
          url: targetUrl,
          title: "Unhandled Execution Failure",
          depth: depth,
          status: "failed",
          access_blocked: false,
          risk_score: null,
          risk_level: "Failed",
          findings_count: 0,
          findings: [],
          has_screenshot: false,
          screenshot_url: null,
          message: "Page processing produced an unhandled response."
        };

        await safeFetch(`${API_BASE}/scan/website/browser/${currentCrawl.scanId}/page`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            url: targetUrl,
            final_url: targetUrl,
            title: failRecord.title,
            depth: depth,
            status: "failed",
            access_blocked: false
          })
        }, 2000).catch(() => {});

        currentCrawl.pages.push(failRecord);
        console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Page marked completed] ${targetUrl} - Terminal status: failed (unhandled)`);

        await closeScanTab();
      }

      await persistState();
      broadcastMessage("SCAN_PROGRESS", {
        pagesScanned: currentCrawl.pages.length,
        pagesDiscovered: currentCrawl.discoveredUrls.size,
        pagesBlocked: currentCrawl.blockedCount,
        pagesFailed: currentCrawl.failedCount,
        pagesTimedOut: currentCrawl.timedOutCount,
        maxPages: currentCrawl.maxPages,
        currentUrl: targetUrl,
        current_stage: currentCrawl.currentStage,
        stage: currentCrawl.stage,
        pages: currentCrawl.pages,
        first_page: currentCrawl.pages.length > 0 ? currentCrawl.pages[0] : null
      });
    }

    if (currentCrawl !== thisCrawl) {
      console.log(`[DarkShield Scan ${thisCrawl.scanId}] Crawl was superseded by a newer crawl. Halting finalization cleanly.`);
      return;
    }

    // 4. Finalize scan session
    thisCrawl.currentUrl = null;
    const finalStatus = thisCrawl.cancelled ? "cancelled" : "completed";
    thisCrawl.status = finalStatus;
    thisCrawl.currentStage = finalStatus === "cancelled" ? "Scan cancelled" : "Scan completed";
    thisCrawl.stage = thisCrawl.currentStage;
    console.log(`[DarkShield Scan ${thisCrawl.scanId}] [Finalization entry] Status: ${finalStatus}, Pages: ${thisCrawl.pages.length}, Blocked: ${thisCrawl.blockedCount}, TimedOut: ${thisCrawl.timedOutCount}, Failed: ${thisCrawl.failedCount}`);
    await syncStageToBackend(thisCrawl.scanId, thisCrawl.currentStage);

    if (thisCrawl.scanId) {
      try {
        const finishRes = await safeFetch(`${API_BASE}/scan/website/browser/${thisCrawl.scanId}/finish`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            total_discovered: thisCrawl.discoveredUrls.size,
            scan_status: finalStatus,
            limit_reached: thisCrawl.limitReached || (thisCrawl.pages.length >= thisCrawl.maxPages)
          })
        }, 5000);

        if (finishRes && finishRes.ok) {
          const finishData = await finishRes.json();
          thisCrawl.summary = finishData.summary;
          console.log(`[DarkShield Scan ${thisCrawl.scanId}] [Finalization exit] Summary received: Score: ${thisCrawl.summary?.website_risk_score}, Level: ${thisCrawl.summary?.website_risk_level}`);
        }
      } catch (e) {
        console.warn("[DarkShield AI] Finish API call failed:", e);
      }
    }

  } catch (err) {
    console.error("[DarkShield AI] Crawl execution error:", err);
    if (currentCrawl === thisCrawl) {
      thisCrawl.status = "failed";
      thisCrawl.currentStage = "Crawl failed";
      thisCrawl.stage = "Crawl failed";
      thisCrawl.error = err.message || "Whole website crawl failed";
      syncStageToBackend(thisCrawl.scanId, "Crawl failed");
      broadcastMessage("SCAN_FAILED", { error: thisCrawl.error });
    }
  } finally {
    if (keepAliveTimer) {
      clearInterval(keepAliveTimer);
      keepAliveTimer = null;
    }

    if (currentCrawl === thisCrawl) {
      // 5. Clean up dedicated scan tab
      await closeScanTab();

      await persistState();
      if (thisCrawl.status !== "failed") {
        broadcastMessage("SCAN_COMPLETED", {
          status: thisCrawl.status,
          summary: thisCrawl.summary,
          pages: thisCrawl.pages,
          error: thisCrawl.error
        });
      }
    }
  }
}

/**
 * Audits a single page: tab navigation, content extraction, screenshot, and backend transmission.
 */
async function auditSinglePage(targetUrl, depth) {
  const tabId = await ensureCleanScanTab();
  if (!tabId) {
    return { failed: true, error: "Unable to allocate background tab" };
  }

  // Navigate scan tab
  console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Navigation started] ${targetUrl} - TabId: ${tabId}`);
  try {
    await chrome.tabs.update(tabId, { url: targetUrl });
  } catch (navErr) {
    return { failed: true, error: `Navigation error: ${navErr.message || navErr}` };
  }

  // Wait for tab readiness (max 2.5s)
  const navStatus = await waitForTabReady(tabId, targetUrl, NAV_READINESS_TIMEOUT_MS);
  console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Navigation completed] ${targetUrl} - TabId: ${tabId}, Status: ${navStatus}`);
  await delay(150);

  if (currentCrawl.cancelled) return { failed: true, error: "Cancelled" };

  // Extract DOM and elements via content.js injection with timeout
  let pageData = null;
  const results = await safeExecuteScript({
    target: { tabId },
    files: ["content.js"]
  }, SCRIPT_INJECT_TIMEOUT_MS);

  if (results && results[0] && results[0].result) {
    pageData = results[0].result;
  }

  // Functional fallback if content.js returned empty
  if (!pageData) {
    const fallbackResults = await safeExecuteScript({
      target: { tabId },
      func: () => {
        const url = window.location.href;
        const title = document.title || "Captured Webpage";
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
          url: url,
          title: title,
          html: rawHtml.slice(0, 300000),
          visible_text: rawText.slice(0, 80000),
          elements: [],
          discovered_links: links,
          browser_metadata: { source: "darkshield_functional_fallback" }
        };
      }
    }, SCRIPT_INJECT_TIMEOUT_MS);

    if (fallbackResults && fallbackResults[0] && fallbackResults[0].result) {
      pageData = fallbackResults[0].result;
    }
  }

  // If both navigations timed out and no page content could be retrieved
  if (!pageData || !pageData.url || pageData.url === "about:blank") {
    if (navStatus === "timeout") {
      return { timedOut: true };
    }
    return { failed: true, error: "Empty or unnavigated page content" };
  }

  // Anti-bot barrier check
  const blockCheck = detectBrowserAccessBlock(pageData.title, pageData.visible_text, pageData.html);
  let screenshotDataUrl = null;
  try {
    screenshotDataUrl = await safeCaptureScreenshot(SCREENSHOT_TIMEOUT_MS);
  } catch (snapErr) {
    screenshotDataUrl = null;
  }

  // Submit page to backend
  console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Backend analysis requested] ${targetUrl} - Submitting payload to backend`);
  const pagePayload = {
    url: pageData.url || targetUrl,
    final_url: pageData.url || targetUrl,
    title: pageData.title || "Captured Webpage",
    depth: depth,
    html: pageData.html || "",
    text: pageData.visible_text || "",
    visible_text: pageData.visible_text || "",
    elements: pageData.elements || [],
    screenshot: screenshotDataUrl,
    status: blockCheck.isBlocked ? "blocked" : "completed",
    access_blocked: blockCheck.isBlocked,
    block_provider: blockCheck.provider,
    browser_metadata: pageData.browser_metadata,
    discovered_urls: (pageData.discovered_links || []).slice(0, currentCrawl.maxPages)
  };

  console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Backend request start] Submitting ${targetUrl} (Status: ${pagePayload.status})`);
  const pageRes = await safeFetch(`${API_BASE}/scan/website/browser/${currentCrawl.scanId}/page`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(pagePayload)
  }, BACKEND_FETCH_TIMEOUT_MS);
  console.log(`[DarkShield Scan ${currentCrawl.scanId}] [Backend request completed] ${targetUrl} - HTTP ${pageRes ? pageRes.status : "timeout/error"}`);

  if (pageRes && pageRes.ok) {
    const resData = await pageRes.json();
    return {
      success: true,
      pageRecord: resData.page_record,
      discoveredLinks: pageData.discovered_links || []
    };
  }

  return { failed: true, error: `Backend submission failed (HTTP ${pageRes ? pageRes.status : "timeout"})` };
}
