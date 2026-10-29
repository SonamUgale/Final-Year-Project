# DarkShield AI — Browser Capture Chrome Extension (Manifest V3)

The **DarkShield AI Browser Capture Extension** allows researchers and users to audit complex, interactive web applications—including platforms behind Web Application Firewalls (such as Akamai on Meesho or Cloudflare)—by inspecting the page directly within the user's authentic browser session.

---

## Key Capabilities

1. **Zero Evasion / Ethical Inspection**: Operates directly on the rendered DOM and viewport in an authorized browser tab. No anti-bot bypasses, proxy rotations, or CAPTCHA solvers are used.
2. **Comprehensive Content Capture**: Gathers rendered HTML, inner text, buttons, links, inputs, checkboxes, computed styles, and tab viewport screenshot.
3. **Strict Privacy Sanitization**:
   - Drops all password inputs and fields matching `/password|card|cvv|ssn|auth|token|secret/i`.
   - Never accesses `document.cookie`, `localStorage`, `sessionStorage`, or browsing history.
4. **Unified Intelligence Pipeline**: Feeds captured DOM and screenshots to the exact same DarkShield backend (`POST /scan/capture`), executing:
   - Calibrated Linear SVM V2
   - Rule-based heuristic detectors
   - Multi-Modal Vision AI (or offline fallback)
   - Evidence grounding verification
   - 5-factor risk scoring engine

---

## Extension Structure (Manifest V3)

```
browser_extension/
├── manifest.json       # Manifest V3 permissions & action configuration
├── background.js       # Background service worker
├── content.js          # DOM extraction & sensitive data sanitization script
├── popup.html          # Extension popup user interface
├── popup.js            # Capture orchestration, API dispatch & result rendering
├── popup.css           # Polished DarkShield dark theme styles
├── icons/              # 16px, 48px, 128px shield icons
└── README.md           # Documentation & installation guide
```

---

## Installation Steps (Load Unpacked)

1. Open Google Chrome.
2. Navigate to:
   ```
   chrome://extensions/
   ```
3. In the top-right corner, turn on **Developer mode**.
4. In the top-left corner, click **Load unpacked**.
5. Select this folder:
   ```
   D:\VSCode\final_year_project\Final-Year-Project\browser_extension
   ```
6. The **DarkShield AI** extension icon (🛡️) will now appear in your Chrome toolbar. (You may click the puzzle icon to pin it for easy access).

---

## How to Analyze a Protected Website (e.g. Meesho)

1. Make sure your DarkShield backend server is running:
   ```powershell
   .\venv\Scripts\python.exe -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
   ```
2. Open Chrome and navigate to the target website normally (e.g., `https://www.meesho.com/`).
3. Click the **DarkShield AI** icon in the Chrome toolbar.
4. Click **"Analyze Current Page"**.
5. The extension will:
   - Extract the rendered DOM and interactive elements.
   - Capture a screenshot of the visible tab.
   - Dispatch the payload to `http://127.0.0.1:8000/scan/capture`.
   - Display the Deceptive Risk Score (e.g., 62/100, High Risk) and detected patterns.
6. Click **"Open in DarkShield Dashboard"** or **"Download PDF Report"** to view the full audit.
