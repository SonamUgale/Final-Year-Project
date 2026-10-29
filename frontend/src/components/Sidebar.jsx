import React from "react";

export function Sidebar({
  activePage = "dashboard",
  onNavigate,
  backendConnected = true,
  historyCount = 0,
  mobileOpen = false,
  onCloseMobile,
}) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: "📊" },
    { id: "scan", label: "Scan Website", icon: "🔍" },
    { id: "capture", label: "Browser Capture", icon: "🌐" },
    { id: "history", label: "Scan History", icon: "📋", badge: historyCount > 0 ? historyCount : null },
    { id: "reports", label: "Reports", icon: "📄" },
    { id: "about", label: "About", icon: "ℹ️" },
  ];

  const handleItemClick = (id) => {
    onNavigate(id);
    if (onCloseMobile) onCloseMobile();
  };

  return (
    <>
      {mobileOpen && (
        <div className="sidebar-backdrop" onClick={onCloseMobile} />
      )}
      <aside className={`app-sidebar ${mobileOpen ? "is-mobile-open" : ""}`}>
        {/* Brand Header */}
        <div className="sidebar-brand-box">
          <div className="brand-logo-icon">🛡️</div>
          <div className="brand-title-wrap">
            <h1 className="brand-app-name">DarkShield AI</h1>
            <span className="brand-app-sub">AI-Powered Deception Detection</span>
          </div>
          {mobileOpen && (
            <button
              type="button"
              className="sidebar-close-btn"
              onClick={onCloseMobile}
              aria-label="Close navigation"
            >
              ✕
            </button>
          )}
        </div>

        {/* Navigation List */}
        <nav className="sidebar-nav">
          <span className="nav-section-label">MAIN NAVIGATION</span>
          <ul className="nav-menu-list">
            {navItems.map((item) => {
              const isActive = activePage === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    className={`nav-menu-btn ${isActive ? "is-active" : ""}`}
                    onClick={() => handleItemClick(item.id)}
                  >
                    <span className="nav-item-icon">{item.icon}</span>
                    <span className="nav-item-label">{item.label}</span>
                    {item.badge !== null && item.badge !== undefined && (
                      <span className="nav-item-badge">{item.badge}</span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Footer System Status */}
        <div className="sidebar-footer">
          <div className={`system-status-indicator ${backendConnected ? "is-online" : "is-offline"}`}>
            <span className="status-indicator-dot"></span>
            <div className="status-text-wrap">
              <span className="status-primary-text">
                {backendConnected ? "Backend Connected" : "Backend Offline"}
              </span>
              <span className="status-sub-text">
                {backendConnected ? "FastAPI :8000 Online" : "FastAPI Disconnected"}
              </span>
            </div>
          </div>
          <div className="sidebar-version-tag">
            <span>v2.4 Multi-Engine Edition</span>
          </div>
        </div>
      </aside>
    </>
  );
}
