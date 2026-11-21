# DarkShield AI – Production Deployment Guide

A step-by-step production deployment manual for **DarkShield AI – Deceptive Design & Dark Pattern Detection System**.

---

## Architecture Overview

```
                      ┌───────────────────────────────────────┐
                      │            Client Layer               │
                      │                                       │
                      │   Vercel Deployed Frontend (React)    │
                      │   Chrome Extension (Manifest V3)      │
                      └──────────────────┬────────────────────┘
                                         │  HTTPS REST API
                                         ▼
                      ┌───────────────────────────────────────┐
                      │    Cloud Container (Render / Railway) │
                      │                                       │
                      │   FastAPI (Python 3.12 + Uvicorn)     │
                      │   Playwright Headless Chromium        │
                      │   Calibrated Linear SVM Engine (v2)   │
                      │   ReportLab PDF Generator             │
                      │   Persistent Storage (/app/data)      │
                      └──────────────────┬────────────────────┘
                                         │  Optional AI Fallback
                                         ▼
                      ┌───────────────────────────────────────┐
                      │        Gemini 1.5 / OpenAI APIs       │
                      │  (System operates 100% offline if     │
                      │   keys are omitted)                   │
                      └───────────────────────────────────────┘
```

---

## Hosting Platform Evaluation & Strategy

| Layer | Recommended Host | Cost | Why this platform? |
| :--- | :--- | :--- | :--- |
| **Frontend** | **Vercel** | **Free ($0)** | Fast edge CDN, automated GitHub deployments, custom domain, automatic SSL, SPA routing via `vercel.json`. |
| **Backend** | **Render (Web Service)** | **Free ($0)** or **$7/mo** | Native Docker support with Playwright Chromium. Zero-cost deployment option. |
| **Backend (Alternative)** | **Railway** | **$5 trial / $5/mo** | 8 GB shared RAM (no container spin-down), faster execution during multi-page crawling. |

---

## Prerequisites Before Deployment

1. A **GitHub account** with access to push your repository.
2. A **Vercel account** ([vercel.com](https://vercel.com)) connected to your GitHub.
3. A **Render account** ([render.com](https://render.com)) or **Railway account** ([railway.app](https://railway.app)).
4. *(Optional)* A Google Gemini API Key or OpenAI API Key if you want LLM narrative explanations and visual UI screenshots analysis. If omitted, DarkShield operates in **calibrated offline mode**.

---

## Step 1: Deploying the Backend on Render (Free Tier)

### 1.1 Create Web Service
1. Sign in to your **Render Dashboard** ([dashboard.render.com](https://dashboard.render.com/)).
2. Click **New +** and select **Web Service**.
3. Choose **Build and deploy from a Git repository**.
4. Select your `Final-Year-Project` repository (or connect your GitHub account if prompted).
5. Specify the following configuration settings:

| Setting | Value |
| :--- | :--- |
| **Name** | `darkshield-ai-backend` (or your preferred name) |
| **Region** | Choose the closest region (e.g., Singapore, Frankfurt, Oregon) |
| **Branch** | `development` (or `main`) |
| **Root Directory** | *(Leave blank - uses repository root)* |
| **Runtime / Environment** | **Docker** (Render detects the root `Dockerfile` automatically) |
| **Instance Type** | **Free** (512 MB RAM, 0.1 CPU) or **Starter** ($7/mo, 512 MB RAM dedicated) |

### 1.2 Configure Environment Variables in Render
In the **Environment Variables** section of the Render service creation form, add the following keys:

| Environment Variable | Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | Render injects this dynamically, but setting 8000 as default is recommended |
| `ALLOWED_ORIGINS` | `*` | Or set to your Vercel URL once frontend is deployed (e.g. `https://darkshield-ai.vercel.app`) |
| `MAX_SCAN_CONCURRENCY` | `2` | Caps concurrent Playwright tabs to avoid memory pressure on 512MB RAM |
| `SCAN_HEADLESS` | `true` | Ensures Chromium runs in headless server mode |
| `DARKSHIELD_ALLOW_LOCAL_TEST` | `false` | Blocks scans directed at loopback addresses (SSRF protection) |
| `GEMINI_API_KEY` | *(Optional)* | Your Google Gemini API key if using Vision AI / LLM explanations |
| `VISION_PROVIDER` | `gemini` | Vision provider (`gemini` or `openai`) |

### 1.3 Deploy and Verify Backend
1. Click **Create Web Service**.
2. Render will build the Docker container:
   - Installing Python 3.12 packages
   - Installing Playwright Chromium and Debian OS libraries
   - Copying trained SVM models and starting Uvicorn
3. Once the build finishes, Render will display a public URL:
   `https://darkshield-ai-backend.onrender.com`
4. Test the health endpoint in your browser or terminal:
   ```bash
   curl https://your-backend-name.onrender.com/health
   ```
   **Expected Response:**
   ```json
   {
     "status": "healthy",
     "service": "DarkShield AI Backend",
     "version": "2.4.0",
     "ai_engine_ready": true,
     "model_version": "v2",
     "timestamp": "2026-11-21T..."
   }
   ```

> [!NOTE]
> **Render Free-Tier Spin Down:**
> Render's free tier puts the web service to sleep after 15 minutes of inactivity. When a new scan request arrives, the service wakes up in ~45–60 seconds. For presentations or viva evaluations, make a request to `/health` 2 minutes prior so the container is warmed up.

---

## Step 2: Deploying the Frontend on Vercel

### 2.1 Import Project to Vercel
1. Log in to [vercel.com](https://vercel.com) and click **Add New...** -> **Project**.
2. Select your `Final-Year-Project` repository from the GitHub list.
3. Configure the Project Settings:
   - **Framework Preset**: `Vite` (automatically detected)
   - **Root Directory**: Click `Edit` and select `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`

### 2.2 Configure Frontend Environment Variables
In the **Environment Variables** panel in Vercel, add:

| Key | Value |
| :--- | :--- |
| `VITE_API_URL` | `https://your-backend-name.onrender.com` *(use your actual backend URL from Step 1, without trailing slash)* |

### 2.3 Deploy
1. Click **Deploy**.
2. Vercel will install dependencies, build the Vite production bundle, and deploy to their global CDN in ~30 seconds.
3. Once complete, you will receive a public URL such as:
   `https://final-year-project-alpha.vercel.app`
4. Open the URL. The sidebar status in the lower left corner will show:
   **Backend Connected** (Green dot) • **FastAPI Online**

---

## Step 3: Configuring the Chrome Extension for Production

The DarkShield AI browser extension is designed to seamlessly work with both your local machine and your deployed production backend without requiring code edits.

### 3.1 Load Extension in Developer Mode
1. Open Google Chrome and navigate to `chrome://extensions/`.
2. Enable the **Developer mode** toggle in the top-right corner.
3. Click **Load unpacked** in the top-left corner.
4. Select the `browser_extension` folder from this repository:
   `D:\VSCode\final_year_project\Final-Year-Project\browser_extension`

### 3.2 Point Extension to Deployed Backend
1. Click the **DarkShield AI** puzzle icon in your Chrome toolbar to open the popup.
2. In the top-right corner of the popup, notice the status pill (`Checking...` or `Offline`).
3. **Click directly on the status pill**.
4. An interactive prompt will appear:
   ```text
   Enter DarkShield Backend API URL (e.g., https://your-backend.onrender.com or http://127.0.0.1:8000):
   ```
5. Paste your deployed Render/Railway backend URL:
   `https://your-backend-name.onrender.com`
6. Click **OK**.
7. The status will immediately turn green: **Online**.
8. The extension is now inspecting webpages and sending data directly to your cloud production backend!

---

## Step 4: Verification & Smoke Test Checklist

Once both services are deployed, perform the following verification tests:

| Test Item | Verification Procedure | Expected Outcome |
| :--- | :--- | :--- |
| **Backend Health** | Open `https://<backend-url>/health` | Status `healthy`, `ai_engine_ready: true`, model `v2` |
| **Model Info** | Open `https://<backend-url>/model-info` | Returns verified accuracy metrics (96.89%, precision, recall) |
| **Frontend Connectivity** | Open `https://<frontend-url>/` | Dashboard loads, status indicator displays "Backend Connected" |
| **Single Page Scan** | Enter `https://example.com` and click "Start Deep Scan" | Scrapes content, runs SVM classification, shows radial risk gauge |
| **PDF Generation** | Click "Download PDF Report" on any scan result | Generates and downloads `DarkShield_Report_<scan_id>.pdf` |
| **Access Block Handling** | Test with a protected site (e.g., `https://amazon.com`) | Detects bot barrier (Akamai/Cloudflare) and displays user guidance |
| **SSRF Safeguard** | Test `http://169.254.169.254` | Blocked with security warning: "Access to cloud metadata endpoints is strictly prohibited" |
| **Browser Extension** | Click "Analyze Current Page" on any tab | DOM extraction and instant score card rendered in extension popup |

---

## Troubleshooting Guide

### 1. Backend shows "Offline" in Frontend
- **Cause**: Render free tier may be sleeping or cold-starting.
- **Fix**: Open the backend URL `https://your-backend.onrender.com/health` in a browser tab. Wait 45 seconds for the container to start. Once it returns `{"status":"healthy"}`, refresh the frontend.

### 2. CORS Error in Browser Console (`Access-Control-Allow-Origin`)
- **Cause**: Backend `ALLOWED_ORIGINS` does not match the frontend domain.
- **Fix**: In the Render Dashboard under **Environment Variables**, ensure `ALLOWED_ORIGINS` is set to `*` or includes your exact Vercel URL (e.g., `https://your-app.vercel.app`).

### 3. Website Scan Times Out on Free Tier
- **Cause**: 512 MB memory constraint when opening multiple tabs on dynamic client-side applications.
- **Fix**: In the Whole Website Scan settings, select **5 Pages (Quick Scan)** or **10 Pages** with **Concurrency: 1 or 2**. The system will crawl sequentially without overloading RAM.

### 4. Optional Cloud AI Not Running
- **Cause**: No Gemini or OpenAI API keys are configured.
- **Fix**: This is expected and normal. The application automatically engages its deterministic rule engine and Calibrated Linear SVM model (96.89% test accuracy) for offline detection.
