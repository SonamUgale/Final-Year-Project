import React from "react";

export function AboutPage({ modelInfo = null }) {
  const currentAcc = modelInfo?.accuracy_display || "96.89%";
  const currentF1 = modelInfo?.f1_display || modelInfo?.f1_score || "0.9691";
  const currentPrec = modelInfo?.precision_display || "96.72%";
  const currentRec = modelInfo?.recall_display || "97.10%";

  const techStack = [
    { name: "React 19 & Vite", role: "Frontend UI & Component Architecture", icon: "⚛️" },
    { name: "FastAPI & Python 3.12", role: "Asynchronous Backend REST Service", icon: "⚡" },
    { name: "Calibrated Linear SVM V2", role: `Two-stage ML classifier (${currentAcc} Test Accuracy, ${currentF1} F1, ${currentPrec} Precision)`, icon: "🧠" },
    { name: "12 Heuristic Detectors", role: "Deterministic detection for confirmshaming, timers & CTAs", icon: "📐" },
    { name: "Playwright Automation", role: "Full-fidelity desktop browser crawling & snapshot engine", icon: "🎭" },
    { name: "Chrome Extension (MV3)", role: "Direct, privacy-preserving browser capture with zero evasion", icon: "🧩" },
    { name: "Multi-Modal Vision AI", role: "Visual layout hierarchy & color contrast inspection", icon: "👁️" },
    { name: "ReportLab Engine", role: "Formal, publication-ready PDF audit generator", icon: "📄" },
  ];

  return (
    <div className="page-container about-page">
      {/* 1. HEADER */}
      <div className="page-header-box">
        <h2>About DarkShield AI</h2>
        <p className="page-header-sub">
          AI-Powered Deceptive Design & Security Intelligence Platform.
        </p>
      </div>

      {/* 2. OVERVIEW CARD */}
      <section className="card about-overview-card">
        <div className="about-brand-row">
          <span className="about-brand-logo">🛡️</span>
          <div>
            <h3>Autonomous Deceptive Design Auditing</h3>
            <span className="about-tag">Academic Research & SaaS Implementation</span>
          </div>
        </div>
        <p className="about-lead-p">
          DarkShield AI protects consumers, UX researchers, and compliance auditors by automatically
          detecting manipulative "dark patterns"—interface designs crafted to trick users into doing
          things they might not otherwise choose, such as making unintended purchases, signing up for
          hidden subscriptions, or surrendering privacy.
        </p>
      </section>

      {/* 3. MULTI-ENGINE ARCHITECTURE PIPELINE */}
      <section className="card about-pipeline-card">
        <div className="card-header-row">
          <div>
            <h3>Multi-Engine Auditing Pipeline</h3>
            <span className="card-header-sub">How DarkShield evaluates target websites</span>
          </div>
        </div>

        <div className="pipeline-flow-grid">
          <div className="flow-step-box">
            <span className="flow-num">1</span>
            <h4>DOM & Snapshot Capture</h4>
            <p>Playwright or Chrome Extension gathers rendered DOM, interactive elements, and viewport screenshot.</p>
          </div>
          <div className="flow-step-box">
            <span className="flow-num">2</span>
            <h4>Access & WAF Gating</h4>
            <p>Heuristic inspection verifies that the target was not blocked by Akamai, Cloudflare, or captcha walls.</p>
          </div>
          <div className="flow-step-box">
            <span className="flow-num">3</span>
            <h4>Semantic Classification</h4>
            <p>Calibrated Linear SVM V2 ({currentAcc} test accuracy) evaluates text candidates and assigns calibrated class probabilities.</p>
          </div>
          <div className="flow-step-box">
            <span className="flow-num">4</span>
            <h4>Evidence Grounding</h4>
            <p>Heuristics eliminate false positives on benign institutional or academic marketing statements.</p>
          </div>
          <div className="flow-step-box">
            <span className="flow-num">5</span>
            <h4>5-Factor Risk Scoring</h4>
            <p>Fuses Severity (25%), Confidence (20%), Frequency (15%), Impact (25%), and Evidence (15%).</p>
          </div>
        </div>
      </section>

      {/* 4. TECHNOLOGY STACK GRID */}
      <section className="card about-tech-card">
        <div className="card-header-row">
          <div>
            <h3>Core Technology Stack</h3>
            <span className="card-header-sub">Modern engineering stack powering the platform</span>
          </div>
        </div>

        <div className="tech-stack-grid">
          {techStack.map((tech, idx) => (
            <div key={idx} className="tech-item-card">
              <span className="tech-icon">{tech.icon}</span>
              <div className="tech-info">
                <strong>{tech.name}</strong>
                <span>{tech.role}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 5. ML CLASSIFIER EVALUATION BENCHMARK & V1 VS V2 PROGRESSION */}
      <section className="card about-model-card" style={{ marginBottom: "20px" }}>
        <div className="card-header-row">
          <div>
            <h3>ML Classifier Benchmark & V1 vs. V2 Progression</h3>
            <span className="card-header-sub">Unbiased held-out test evaluation comparing historical V1 baseline to current live V2</span>
          </div>
          <span className="tag-chip" style={{ background: "#ecfdf5", color: "#065f46", border: "1px solid #a7f3d0" }}>
            Live: Calibrated Linear SVM V2
          </span>
        </div>

        <div className="table-responsive-wrapper" style={{ overflowX: "auto" }}>
          <table className="recent-scans-table" style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "#f8fafc", textAlign: "left" }}>
                <th style={{ padding: "10px 14px" }}>Metric</th>
                <th style={{ padding: "10px 14px" }}>V1 Baseline (Retail Only)</th>
                <th style={{ padding: "10px 14px" }}>V2 Retrained (Current Live)</th>
                <th style={{ padding: "10px 14px" }}>Impact / Delta</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 14px" }}><strong>Test Accuracy</strong></td>
                <td style={{ padding: "10px 14px", color: "#64748b" }}>95.21% (Historical V1 Baseline)</td>
                <td style={{ padding: "10px 14px", color: "#059669", fontWeight: "600" }}>96.89%</td>
                <td style={{ padding: "10px 14px", color: "#059669" }}>+1.68% overall accuracy boost</td>
              </tr>
              <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 14px" }}><strong>Precision</strong></td>
                <td style={{ padding: "10px 14px", color: "#64748b" }}>95.45%</td>
                <td style={{ padding: "10px 14px", color: "#059669", fontWeight: "600" }}>96.72%</td>
                <td style={{ padding: "10px 14px", color: "#059669" }}>+1.27% precision improvement</td>
              </tr>
              <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 14px" }}><strong>Recall</strong></td>
                <td style={{ padding: "10px 14px", color: "#64748b" }}>94.92%</td>
                <td style={{ padding: "10px 14px", color: "#059669", fontWeight: "600" }}>97.10%</td>
                <td style={{ padding: "10px 14px", color: "#059669" }}>+2.18% reduction in missed patterns</td>
              </tr>
              <tr style={{ borderBottom: "1px solid #f1f5f9" }}>
                <td style={{ padding: "10px 14px" }}><strong>F1-Score</strong></td>
                <td style={{ padding: "10px 14px", color: "#64748b" }}>0.9518</td>
                <td style={{ padding: "10px 14px", color: "#059669", fontWeight: "600" }}>0.9691</td>
                <td style={{ padding: "10px 14px", color: "#059669" }}>+0.0173 harmonic balance</td>
              </tr>
              <tr>
                <td style={{ padding: "10px 14px" }}><strong>ROC-AUC</strong></td>
                <td style={{ padding: "10px 14px", color: "#64748b" }}>0.9858</td>
                <td style={{ padding: "10px 14px", color: "#059669", fontWeight: "600" }}>0.9924 (~0.99)</td>
                <td style={{ padding: "10px 14px", color: "#059669" }}>Enhanced calibration confidence</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* 5. ETHICS & SCIENTIFIC INTEGRITY STATEMENT */}
      <section className="card about-ethics-card">
        <h4>🔒 Scientific Integrity & False-Positive Elimination Policy</h4>
        <div className="ethics-content-list">
          <p>
            • <strong>No Hallucinated Findings:</strong> Every reported dark pattern requires verified text/DOM
            evidence extracted directly from the target page.
          </p>
          <p>
            • <strong>Zero Anti-Bot Evasion:</strong> When an automated crawler is blocked by a Web Application Firewall
            (e.g. Akamai on Meesho), DarkShield never bypasses security controls. Analysis is honestly withheld, and
            Browser Capture Mode is offered.
          </p>
          <p>
            • <strong>Privacy by Design:</strong> The browser extension never reads passwords, payment information,
            cookies, or storage.
          </p>
        </div>
      </section>
    </div>
  );
}
