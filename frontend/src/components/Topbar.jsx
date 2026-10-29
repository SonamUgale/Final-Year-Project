import React from "react";

export function Topbar({
  activePage = "dashboard",
  backendConnected = true,
  onOpenMobileSidebar,
  onNewScan,
}) {
  const titles = {
    dashboard: "Dashboard Overview",
    scan: "Website Scanner",
    capture: "Browser Capture Mode",
    history: "Scan Audit History",
    reports: "Audit Reports Library",
    about: "About DarkShield AI",
  };

  const breadcrumbs = {
    dashboard: ["Platform", "Dashboard"],
    scan: ["Scanner", "Live Website Audit"],
    capture: ["Scanner", "Browser Capture (Extension)"],
    history: ["Audits", "Historical Records"],
    reports: ["Audits", "Generated PDF Reports"],
    about: ["System", "Architecture & Ethics"],
  };

  const pageTitle = titles[activePage] || "DarkShield AI";
  const path = breadcrumbs[activePage] || ["Platform", "Overview"];

  return (
    <header className="app-topbar">
      <div className="topbar-left">
        <button
          type="button"
          className="topbar-mobile-toggle"
          onClick={onOpenMobileSidebar}
          aria-label="Toggle navigation menu"
        >
          ☰
        </button>

        <div className="topbar-breadcrumb-wrap">
          <div className="topbar-breadcrumbs">
            <span>DarkShield</span>
            <span className="breadcrumb-sep">/</span>
            <span>{path[0]}</span>
            <span className="breadcrumb-sep">/</span>
            <span className="breadcrumb-current">{path[1]}</span>
          </div>
          <h2 className="topbar-page-title">{pageTitle}</h2>
        </div>
      </div>

      <div className="topbar-right">
        <div className={`topbar-connection-chip ${backendConnected ? "chip-online" : "chip-offline"}`}>
          <span className="chip-dot"></span>
          <span>{backendConnected ? "AI Engine Online" : "Engine Offline"}</span>
        </div>

        {activePage !== "scan" && onNewScan && (
          <button
            type="button"
            className="topbar-new-scan-btn"
            onClick={onNewScan}
          >
            <span>+ New Scan</span>
          </button>
        )}
      </div>
    </header>
  );
}
