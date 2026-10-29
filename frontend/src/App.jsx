import { useState, useEffect } from "react";
import "./App.css";

import { Sidebar } from "./components/Sidebar";
import { Topbar } from "./components/Topbar";
import { DashboardPage } from "./pages/DashboardPage";
import { ScanPage } from "./pages/ScanPage";
import { BrowserCapturePage } from "./pages/BrowserCapturePage";
import { HistoryPage } from "./pages/HistoryPage";
import { ReportsPage } from "./pages/ReportsPage";
import { AboutPage } from "./pages/AboutPage";
import { SCAN_PIPELINE_STEPS } from "./components/LoadingStepper";
import { DEFAULT_MODEL_METADATA } from "./constants/modelMetadata";

const API_BASE = "http://127.0.0.1:8000";

function App() {
  // Navigation State
  const [activePage, setActivePage] = useState("dashboard");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [backendConnected, setBackendConnected] = useState(true);
  const [modelInfo, setModelInfo] = useState(DEFAULT_MODEL_METADATA);

  // Scanner State
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [scanStep, setScanStep] = useState(0);
  const [error, setError] = useState("");

  // Browser Capture State
  const [captureUrl, setCaptureUrl] = useState("");
  const [captureTitle, setCaptureTitle] = useState("");
  const [captureHtml, setCaptureHtml] = useState("");
  const [captureScreenshot, setCaptureScreenshot] = useState("");
  const [copiedBookmarklet, setCopiedBookmarklet] = useState(false);

  // Scan History State
  const [history, setHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // PDF Export State
  const [downloadingPdf, setDownloadingPdf] = useState(false);

  // Check Backend Connection & Fetch History on Mount
  useEffect(() => {
    checkBackendHealth();
    fetchHistory();
    const interval = setInterval(checkBackendHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  // Step progression during scan
  useEffect(() => {
    let interval;
    if (loading) {
      setScanStep(0);
      interval = setInterval(() => {
        setScanStep((prev) => (prev < SCAN_PIPELINE_STEPS.length - 1 ? prev + 1 : prev));
      }, 2200);
    } else {
      setScanStep(0);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const checkBackendHealth = async () => {
    try {
      const res = await fetch(`${API_BASE}/`, { method: "GET" });
      if (res.ok) {
        setBackendConnected(true);
        const data = await res.json();
        if (data.model_metadata && data.model_metadata.test_accuracy) {
          setModelInfo(data.model_metadata);
        }
      } else {
        setBackendConnected(false);
      }
    } catch {
      setBackendConnected(false);
    }
  };

  const fetchHistory = async () => {
    try {
      setHistoryLoading(true);
      const res = await fetch(`${API_BASE}/history?limit=50`);
      if (res.ok) {
        const data = await res.json();
        setHistory(data);
      }
    } catch {
      // Backend not running
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleStartScan = async (targetUrl) => {
    const scanTarget = (targetUrl || url).trim();
    if (!scanTarget) {
      setError("Please enter a website URL.");
      return;
    }

    setUrl(scanTarget);
    setError("");
    setResult(null);
    setLoading(true);
    setActivePage("scan");

    try {
      const response = await fetch(`${API_BASE}/scan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: scanTarget }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.detail || data.message || `Server returned ${response.status}`);
        setLoading(false);
        return;
      }

      setResult(data);
      fetchHistory();
    } catch (err) {
      console.error(err);
      setError("Unable to connect to the DarkShield backend server. Please verify FastAPI is running at http://127.0.0.1:8000.");
    } finally {
      setLoading(false);
    }
  };

  const handleCaptureScan = async () => {
    setError("");
    setResult(null);

    const trimmedUrl = captureUrl.trim();
    if (!trimmedUrl) {
      setError("Please enter the page URL of the captured browser session.");
      return;
    }
    if (!captureHtml.trim()) {
      setError("Please paste the page HTML or DOM text to analyze.");
      return;
    }

    setLoading(true);
    setActivePage("scan");

    try {
      const response = await fetch(`${API_BASE}/scan/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          url: trimmedUrl,
          title: captureTitle.trim() || undefined,
          html: captureHtml,
          screenshot_b64: captureScreenshot.trim() || undefined,
          browser_metadata: {
            source: "manual_browser_capture",
            user_agent: navigator.userAgent,
          },
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        setError(data.detail || data.message || `Server returned ${response.status}`);
        setLoading(false);
        return;
      }

      setResult(data);
      fetchHistory();
    } catch (err) {
      console.error(err);
      setError("Unable to process the browser capture response from the server.");
    } finally {
      setLoading(false);
    }
  };

  const handleSelectScan = async (scanId) => {
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
      setActivePage("scan");
    } catch (err) {
      setError("Could not load historical scan details.");
    } finally {
      setLoading(false);
    }
  };

  // Deep link support (e.g. from Chrome Extension "Open in Dashboard")
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const scanId = params.get("scan_id");
    if (scanId) {
      handleSelectScan(scanId);
    }
  }, []);

  const handleDeleteHistory = async (scanId, e) => {
    if (e && e.stopPropagation) e.stopPropagation();
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

  const handleCopyBookmarklet = async () => {
    try {
      const res = await fetch(`${API_BASE}/capture/bookmarklet`);
      if (res.ok) {
        const data = await res.json();
        await navigator.clipboard.writeText(data.bookmarklet);
        setCopiedBookmarklet(true);
        setTimeout(() => setCopiedBookmarklet(false), 2500);
      }
    } catch {
      alert("Could not copy bookmarklet automatically. Please inspect http://127.0.0.1:8000/capture/bookmarklet");
    }
  };

  const handleSwitchToCapture = () => {
    setActivePage("capture");
    const siteUrl = result?.requested_url || result?.website?.url || url;
    if (siteUrl) {
      setCaptureUrl(siteUrl);
    }
  };

  return (
    <div className="app-shell-layout">
      {/* 1. SIDEBAR */}
      <Sidebar
        activePage={activePage}
        onNavigate={(page) => {
          setActivePage(page);
          setError("");
        }}
        backendConnected={backendConnected}
        historyCount={history.length}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />

      {/* 2. MAIN APP CONTENT CONTAINER */}
      <div className="app-main-viewport">
        {/* Topbar */}
        <Topbar
          activePage={activePage}
          backendConnected={backendConnected}
          onOpenMobileSidebar={() => setMobileOpen(true)}
          onNewScan={() => {
            setActivePage("scan");
            setResult(null);
            setError("");
          }}
        />

        {/* Dynamic Page Routing */}
        <main className="app-page-content">
          {activePage === "dashboard" && (
            <DashboardPage
              history={history}
              onStartScan={(targetUrl) => handleStartScan(targetUrl)}
              onNavigate={(page) => {
                setActivePage(page);
                setError("");
              }}
              onSelectScan={handleSelectScan}
              loading={loading}
              modelInfo={modelInfo}
            />
          )}

          {activePage === "scan" && (
            <ScanPage
              url={url}
              setUrl={setUrl}
              onScan={() => handleStartScan(url)}
              loading={loading}
              scanStep={scanStep}
              result={result}
              error={error}
              onSwitchToCapture={handleSwitchToCapture}
              onDownloadPdf={handleDownloadPdf}
              downloadingPdf={downloadingPdf}
              modelInfo={modelInfo}
              apiBase={API_BASE}
            />
          )}

          {activePage === "capture" && (
            <BrowserCapturePage
              captureUrl={captureUrl}
              setCaptureUrl={setCaptureUrl}
              captureTitle={captureTitle}
              setCaptureTitle={setCaptureTitle}
              captureHtml={captureHtml}
              setCaptureHtml={setCaptureHtml}
              captureScreenshot={captureScreenshot}
              setCaptureScreenshot={setCaptureScreenshot}
              onCaptureScan={handleCaptureScan}
              onCopyBookmarklet={handleCopyBookmarklet}
              copiedBookmarklet={copiedBookmarklet}
              loading={loading}
              error={error}
            />
          )}

          {activePage === "history" && (
            <HistoryPage
              history={history}
              onSelectScan={handleSelectScan}
              onDownloadPdf={handleDownloadPdf}
              onDeleteHistory={handleDeleteHistory}
              onNavigate={setActivePage}
            />
          )}

          {activePage === "reports" && (
            <ReportsPage
              history={history}
              onSelectScan={handleSelectScan}
              onDownloadPdf={handleDownloadPdf}
              onNavigate={setActivePage}
            />
          )}

          {activePage === "about" && <AboutPage modelInfo={modelInfo} />}
        </main>
      </div>
    </div>
  );
}

export default App;