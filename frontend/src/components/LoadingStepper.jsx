import React from "react";

export const SCAN_PIPELINE_STEPS = [
  { label: "Connecting & Launching Browser", detail: "Initializing Playwright & desktop browser context" },
  { label: "Rendering DOM & Capturing Screenshot", detail: "Awaiting client scripts and taking full viewport snapshot" },
  { label: "Extracting Interactive Elements", detail: "Evaluating buttons, inputs, links, headings, and cookie notices" },
  { label: "Running Calibrated Linear SVM V2", detail: "Classifying candidate interface text with TF-IDF vectors" },
  { label: "Executing Heuristic Rule Detectors", detail: "Scanning for confirmshaming, countdown timers, and deceptive CTAs" },
  { label: "Synthesizing 5-Factor Risk Score", detail: "Computing Severity, Confidence, Frequency, Impact, and Evidence" },
  { label: "Generating Final Audit Report", detail: "Persisting scan record and assembling downloadable PDF audit" },
];

export function LoadingStepper({ currentStep = 0 }) {
  return (
    <div className="loading-stepper-card">
      <div className="stepper-card-header">
        <div className="stepper-brand">
          <span className="stepper-spinner"></span>
          <div>
            <h4>Audit In Progress — Real-Time AI Pipeline</h4>
            <span className="stepper-sub">
              Step {currentStep + 1} of {SCAN_PIPELINE_STEPS.length}
            </span>
          </div>
        </div>
      </div>

      <div className="stepper-steps-track">
        {SCAN_PIPELINE_STEPS.map((step, idx) => {
          const isDone = idx < currentStep;
          const isActive = idx === currentStep;
          return (
            <div
              key={idx}
              className={`stepper-step-node ${isDone ? "is-done" : isActive ? "is-active" : "is-pending"}`}
            >
              <div className="step-circle-badge">
                {isDone ? "✓" : idx + 1}
              </div>
              <span className="step-node-label">{step.label}</span>
            </div>
          );
        })}
      </div>

      <div className="stepper-live-detail">
        <span className="detail-pulse-dot">●</span>
        <span className="detail-text">
          {SCAN_PIPELINE_STEPS[currentStep]?.detail || "Processing analysis..."}
        </span>
      </div>
    </div>
  );
}
