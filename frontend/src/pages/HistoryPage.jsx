import React, { useState, useMemo } from "react";
import { RiskBadge } from "../components/RiskBadge";
import { StatusBadge } from "../components/StatusBadge";
import { ModeBadge } from "../components/ModeBadge";
import { EmptyState } from "../components/EmptyState";

export function HistoryPage({
  history = [],
  onSelectScan,
  onDownloadPdf,
  onDeleteHistory,
  onNavigate,
}) {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [riskFilter, setRiskFilter] = useState("all");
  const [modeFilter, setModeFilter] = useState("all");
  const [sortOrder, setSortOrder] = useState("newest");

  const filteredHistory = useMemo(() => {
    return history.filter((item) => {
      // Search filter
      if (search.trim()) {
        const query = search.toLowerCase();
        const matchesUrl = (item.url || "").toLowerCase().includes(query);
        const matchesTitle = (item.title || "").toLowerCase().includes(query);
        if (!matchesUrl && !matchesTitle) return false;
      }

      // Status filter
      if (statusFilter !== "all") {
        const st = (item.scan_status || "").toLowerCase();
        if (statusFilter === "completed" && st !== "complete") return false;
        if (statusFilter === "blocked" && st !== "blocked") return false;
        if (statusFilter === "failed" && st !== "failed") return false;
      }

      // Risk filter
      if (riskFilter !== "all") {
        const rk = (item.dark_risk_level || "").toLowerCase();
        if (riskFilter === "none" && rk !== "none" && rk !== "clean") return false;
        if (riskFilter === "low" && rk !== "low") return false;
        if (riskFilter === "medium" && rk !== "medium") return false;
        if (riskFilter === "high" && rk !== "high") return false;
        if (riskFilter === "very-high" && rk !== "very high" && rk !== "critical") return false;
      }

      // Mode filter
      if (modeFilter !== "all") {
        const isCapture = item.scan_mode === "browser_capture" || item.scan_mode === "capture";
        if (modeFilter === "automatic" && isCapture) return false;
        if (modeFilter === "capture" && !isCapture) return false;
      }

      return true;
    }).sort((a, b) => {
      const dateA = new Date(a.timestamp || 0).getTime();
      const dateB = new Date(b.timestamp || 0).getTime();
      return sortOrder === "newest" ? dateB - dateA : dateA - dateB;
    });
  }, [history, search, statusFilter, riskFilter, modeFilter, sortOrder]);

  return (
    <div className="page-container history-page">
      {/* 1. HEADER */}
      <div className="page-header-box">
        <h2>Scan Audit History</h2>
        <p className="page-header-sub">
          Review, filter, and inspect past website dark pattern scans and security audits.
        </p>
      </div>

      {/* 2. FILTER & SEARCH CONTROLS BAR */}
      <section className="card history-filters-card">
        <div className="filters-search-wrapper">
          <span className="search-icon">🔍</span>
          <input
            type="text"
            className="history-search-input"
            placeholder="Search by URL or page title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          {search && (
            <button
              type="button"
              className="btn-clear-search"
              onClick={() => setSearch("")}
            >
              ✕
            </button>
          )}
        </div>

        <div className="filter-dropdowns-row">
          <div className="filter-dropdown-item">
            <label htmlFor="filter-status">Status:</label>
            <select
              id="filter-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="completed">Completed</option>
              <option value="blocked">Blocked</option>
              <option value="failed">Failed</option>
            </select>
          </div>

          <div className="filter-dropdown-item">
            <label htmlFor="filter-risk">Risk Level:</label>
            <select
              id="filter-risk"
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
            >
              <option value="all">All Risk Levels</option>
              <option value="none">Clean / None</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
              <option value="very-high">Very High Risk</option>
            </select>
          </div>

          <div className="filter-dropdown-item">
            <label htmlFor="filter-mode">Scan Mode:</label>
            <select
              id="filter-mode"
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
            >
              <option value="all">All Modes</option>
              <option value="automatic">Automated Crawler</option>
              <option value="capture">Browser Capture</option>
            </select>
          </div>

          <div className="filter-dropdown-item">
            <label htmlFor="filter-sort">Sort:</label>
            <select
              id="filter-sort"
              value={sortOrder}
              onChange={(e) => setSortOrder(e.target.value)}
            >
              <option value="newest">Newest First</option>
              <option value="oldest">Oldest First</option>
            </select>
          </div>
        </div>
      </section>

      {/* 3. TABLE / CARDS RESULTS */}
      <section className="card history-results-card">
        <div className="history-results-header">
          <span className="results-count-text">
            Showing <strong>{filteredHistory.length}</strong> of {history.length} audit record(s)
          </span>
        </div>

        {filteredHistory.length === 0 ? (
          <EmptyState
            icon="📋"
            title="No Matching Records"
            message={
              history.length === 0
                ? "No scans have been recorded yet. Perform your first scan to build history."
                : "No past scans match your current search and filter criteria."
            }
            actionLabel={history.length === 0 ? "Scan a Website" : "Reset Filters"}
            onAction={() => {
              if (history.length === 0) {
                onNavigate("scan");
              } else {
                setSearch("");
                setStatusFilter("all");
                setRiskFilter("all");
                setModeFilter("all");
              }
            }}
          />
        ) : (
          <div className="table-responsive-wrapper">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Target Website</th>
                  <th>Scan Mode</th>
                  <th>Deceptive Risk</th>
                  <th>Patterns</th>
                  <th>Status</th>
                  <th>Date & Time</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.map((item) => (
                  <tr key={item.scan_id} className="history-row">
                    <td className="cell-website">
                      <strong className="website-row-url" title={item.url}>
                        {item.url}
                      </strong>
                      <span className="website-row-title">{item.title || "Untitled"}</span>
                    </td>
                    <td>
                      <ModeBadge mode={item.scan_mode} />
                    </td>
                    <td>
                      {item.scan_status === "blocked" || item.scan_status === "partial" || item.dark_risk_score === null ? (
                        <RiskBadge level="Withheld" size="small" />
                      ) : (
                        <RiskBadge level={item.dark_risk_level || "None"} size="small" />
                      )}
                    </td>
                    <td className="cell-patterns">
                      <strong>{item.total_dark_patterns ?? 0}</strong>
                    </td>
                    <td>
                      <StatusBadge status={item.scan_status} />
                    </td>
                    <td className="cell-date">
                      {item.timestamp
                        ? new Date(item.timestamp).toLocaleString(undefined, {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "N/A"}
                    </td>
                    <td className="cell-actions-group">
                      <button
                        type="button"
                        className="btn-action-view"
                        onClick={() => onSelectScan(item.scan_id)}
                        title="View online report"
                      >
                        View
                      </button>
                      <button
                        type="button"
                        className="btn-action-pdf"
                        onClick={() => onDownloadPdf(item.scan_id)}
                        title="Download PDF report"
                      >
                        PDF
                      </button>
                      <button
                        type="button"
                        className="btn-action-delete"
                        onClick={(e) => onDeleteHistory(item.scan_id, e)}
                        title="Delete record"
                      >
                        🗑️
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
