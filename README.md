# DarkShield AI — Security Audit & AI Dark Pattern Detection Platform

DarkShield AI is an intelligent web security and deceptive design (dark pattern) analysis platform. It pairs automated browser instrumentation (Playwright + Microsoft Edge) with a two-stage supervised machine learning engine, heuristic rule corroboration, explainable risk scoring, and provider-agnostic LLM contextual interpretation.

---

## 1. System Architecture

```
                      React Dashboard (Vite + React)
                                    ↓  POST /scan
                      FastAPI Backend Engine (app.py)
                                    ↓
                     Playwright + Microsoft Edge
                                    ↓
        ┌───────────────────────────┴───────────────────────────┐
        ↓                                                       ↓
Security Analyzer (10 Checks)                       DOM & Content Extraction
(SSL, CSP, HSTS, X-Frame, Forms)              (Headings, Buttons, Links, Banners, Text)
        ↓                                                       ↓
Security Score & Risk Level                   Hybrid Dark Pattern Decision Engine
                                              ├── Rule-Based Supporting Signals (5 Checks)
                                              └── Supervised ML Pipeline (Calibrated SVM)
                                                      ├── Stage 1: Binary Classification
                                                      └── Stage 2: Multiclass Categorization
                                                                ↓
                                              Explainable Risk Scorer (0 - 100)
                                                                ↓
                                              LLM Contextual Analysis Layer
                                              (Gemini / OpenAI / Grounded Fallback)
                                                                ↓
                                    Consolidated JSON Report
                                    (Security Findings + Dark Patterns + Evidence + Recommendations)
```

---

## 2. Dataset & Leak-Free Preprocessing

### Dataset Overview (EC-DarkPattern)
- **Source File:** `backend/ai/data/raw/dataset.tsv`
- **Total Rows:** 2,356 samples (0 missing values, 0 duplicate rows)
- **Binary Distribution:** 50.0% Not Dark Pattern (1,178) vs. 50.0% Dark Pattern (1,178)
- **Multiclass Categories (7 Dark Pattern Classes):**
  - Scarcity (418)
  - Social Proof (312)
  - Urgency (210)
  - Misdirection (195)
  - Obstruction (27)
  - Sneaking (12)
  - Forced Action (4)
  - Not Dark Pattern (1,178)

### Leak-Free Group-Based Splitting
In raw e-commerce data, multiple snippets often originate from the same website page (`page_id`). Random splitting causes data leakage between train and test sets.
- **Method:** `StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42)` grouped strictly on `page_id`.
- **Integrity Guarantee:** **0 overlapping `page_id`s** across splits.
  - **Train:** 1,649 samples (70.0%) | 874 unique pages | 50.03% positive
  - **Validation:** 352 samples (14.9%) | 187 unique pages | 50.00% positive
  - **Test:** 355 samples (15.1%) | 187 unique pages | 49.86% positive

---

## 3. Supervised Machine Learning Pipeline

### Feature Extraction
- Word unigrams and bigrams via `TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)`
- Punctuation and negation cues (e.g., "only", "no thanks", "don't") are preserved as critical deceptive signals.

### Model Comparison (Held-out Validation Split)

| Classifier | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Calibrated Linear SVM** (Selected) | **96.59%** | **96.59%** | **96.59%** | **0.9659** | **0.9898** |
| Logistic Regression | 96.31% | 97.66% | 94.89% | 0.9625 | 0.9887 |
| Random Forest | 92.90% | 96.89% | 88.64% | 0.9258 | 0.9853 |
| Multinomial Naive Bayes | 78.98% | 71.79% | 95.45% | 0.8195 | 0.9755 |

### Unbiased Test Set Evaluation (Calibrated Linear SVM)
- **Test Accuracy:** **95.21%**
- **Test Precision:** **95.45%**
- **Test Recall:** **94.92%**
- **Test F1-Score:** **0.9518**
- **Test ROC-AUC:** **0.9858**
- **Stage 2 Multiclass Categorization Accuracy:** **93.79%**

---

## 4. Hybrid Decision Fusion Engine

The hybrid engine evaluates candidate DOM elements (headings, buttons, links, banners, paragraphs) and combines ML probabilities with heuristic signals:

1. **Dual Confirmation (`Hybrid (Rules + AI)`):** When both rules and ML flag a pattern (e.g. Urgency or Confirmshaming), evidence is consolidated, and confidence is boosted ($1 - (1 - c_{\text{rule}})(1 - c_{\text{ml}})$).
2. **AI-Discovered (`AI Model`):** Complex linguistic patterns (Social Proof, Sneaking, Obstruction) detected by ML with calibrated probabilities.
3. **DOM-Structural (`Rule-Based`):** Architectural signals such as forced account creation forms with password fields or excessive external redirect links.

---

## 5. Explainable Risk Scoring Methodology

DarkShield AI strictly separates **Security Posture** from **Dark Pattern Deception**:

### Security Score (0 to 100)
- Starts at 100 points and deducts points for missing HTTPS (-30), password fields over HTTP (-40), missing CSP (-10), missing X-Frame-Options (-10), missing HSTS (-10), or suspicious links (-15).
- Higher is more secure.

### Dark Pattern Risk Score (0 to 100)
Measures deceptive intensity using an explainable formula:
$$\text{Contribution}_i = \text{Base Weight}_i \times \text{Confidence}_i \times \text{Method Multiplier}_i$$
$$\text{Dark Pattern Risk Score} = \min(100, \text{round}(\sum \text{Contribution}_i))$$

- **Base Weights:** Critical (30 pts), High (22 pts), Medium (14 pts), Low (7 pts).
- **Multipliers:** Hybrid confirmation (1.15x), AI Model (1.00x), Rule-Based (0.90x).
- **Risk Levels:**
  - 0: `None`
  - 1 – 24: `Low`
  - 25 – 59: `Medium`
  - 60 – 100: `High`

---

## 6. LLM Contextual Interpretation Layer

The LLM does **NOT** act as the primary classifier; the supervised ML model performs classification. The LLM generates grounded contextual interpretation:
- `explanation`: Contextual analysis of how the specific phrase functions deceptively.
- `why_it_matters`: Psychological impact on consumer decision autonomy.
- `recommendation`: Actionable guidance for the consumer.

### Provider Abstraction & Fallback
- Supports **Google Gemini** (`GEMINI_API_KEY`) and **OpenAI** (`OPENAI_API_KEY`).
- When no API keys are present, the system defaults to the `FallbackGroundedExplainer`, guaranteeing uninterrupted operation with `llm_status: "LLM unavailable (API key not configured)"`.

---

## 7. API Specification

### `POST /scan`
**Request:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "website": {
    "url": "https://example.com",
    "title": "Example Domain",
    "dom_elements": [...]
  },
  "security_analysis": {
    "security_score": 65,
    "risk_level": "Medium",
    "total_findings": 3,
    "findings": [...]
  },
  "dark_pattern_analysis": {
    "risk_score": 58,
    "risk_level": "Medium",
    "total_dark_patterns": 4,
    "findings": [
      {
        "pattern": "Urgency or Scarcity",
        "severity": "Medium",
        "detection_method": "Hybrid (Rules + AI)",
        "confidence": 0.999,
        "element_type": "heading",
        "evidence": ["Only 2 left in stock!"],
        "explanation": "...",
        "why_it_matters": "...",
        "recommendation": "..."
      }
    ]
  },
  "ai_analysis": {
    "model": "Calibrated Linear SVM + TF-IDF (EC-DarkPattern)",
    "average_confidence": 0.949,
    "llm_status": "Active: Google Gemini"
  }
}
```

---

## 8. Installation & Verification

### Prerequisites
- Python 3.12+ (or Python 3.14 virtual environment)
- Node.js 18+
- Microsoft Edge installed (Windows)

### Backend Setup
```bash
# Activate virtual environment
.\venv\Scripts\activate

# Run test suite
python -m unittest backend.tests.test_all

# Run controlled validation
python -m backend.tests.validate_real_world

# Start API server
uvicorn backend.app:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev     # Dev server on http://localhost:5173
npm run build   # Production bundle verification
```
