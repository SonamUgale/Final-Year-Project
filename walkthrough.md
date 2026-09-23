# DarkShield AI — AI Dark Pattern Detection Walkthrough

## Overview

We have successfully advanced **DarkShield AI** from a basic rule-based scraper into a full-fledged, AI-powered hybrid dark-pattern detection platform.

```
React Dashboard (Frontend)
    ↓  POST /scan
FastAPI Backend (app.py)
    ↓
Playwright + Microsoft Edge
    ↓  (DOM, Text, Inputs, Buttons, Headers)
Security Analyzer (10 Security Checks)
    +
Hybrid Dark Pattern Engine
    ├── Rule-Based Detector (5 DOM & Regex Checks)
    └── AI Inference Engine (Calibrated SVM + TF-IDF)
            ├── Stage 1: Binary Classification (Dark vs Non-Dark)
            └── Stage 2: Multiclass Pattern Categorization
    ↓
Enriched Scan Results (Pattern + Severity + Confidence + Evidence + Detection Method)
```

---

## What Was Completed

### Phase 1: Dataset Inspection & Risk Analysis
- Analyzed the **EC-DarkPattern** dataset ([`dataset.tsv`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/backend/ai/data/raw/dataset.tsv)):
  - **Total Samples:** 2,356 rows, 4 columns
  - **Class Balance:** Perfectly balanced 50/50 (1,178 dark patterns, 1,178 non-dark patterns)
  - **Multiclass Categories:** 8 categories (Scarcity: 418, Social Proof: 312, Urgency: 210, Misdirection: 195, Obstruction: 27, Sneaking: 12, Forced Action: 4, Not Dark Pattern: 1,178)
  - **Missing Values & Duplicates:** 0 missing values, 0 duplicate rows
  - **Leakage Risk Identified:** 1,248 unique `page_id`s, with 122 pages containing both dark and non-dark samples. Naive random splitting would cause severe data leakage across train and test sets.

### Phase 2: Data Preprocessing & Leak-Free Group Splitting
- Implemented [`backend/ai/preprocessing.py`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/backend/ai/preprocessing.py):
  - Normalized unicode artifacts, unescaped HTML entities, and collapsed whitespace.
  - Used `StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=42)` on `page_id`.
  - **Strict Zero-Leakage Guarantee:** `0` overlapping `page_id`s across all splits:
    - **Train:** 1,649 samples (70.0%) | 874 pages | 50.03% positive
    - **Validation:** 352 samples (14.9%) | 187 pages | 50.00% positive
    - **Test:** 355 samples (15.1%) | 187 pages | 49.86% positive
  - Output files saved to `backend/ai/data/processed/` (`train.csv`, `val.csv`, `test.csv`, `split_info.json`).

### Phase 3: Baseline ML Model Training & Comparison
- Implemented [`backend/ai/train.py`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/backend/ai/train.py):
  - Extracted word unigrams and bigrams via `TfidfVectorizer` (sublinear term frequency, `min_df=2`, keeping negation and trigger cues).
  - Evaluated 4 candidate classifiers on the held-out validation set:

| Model | Accuracy | Precision | Recall | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Calibrated Linear SVM** | **96.59%** | **96.59%** | **96.59%** | **0.9659** | **0.9898** |
| Logistic Regression | 96.31% | 97.66% | 94.89% | 0.9625 | 0.9887 |
| Random Forest | 92.90% | 96.89% | 88.64% | 0.9258 | 0.9853 |
| Multinomial Naive Bayes | 78.98% | 71.79% | 95.45% | 0.8195 | 0.9755 |

- **Unbiased Test Set Evaluation (Winner: Calibrated Linear SVM):**
  - **Accuracy:** **95.21%**
  - **Precision:** **95.45%**
  - **Recall:** **94.92%**
  - **F1-Score:** **0.9518**
  - **ROC-AUC:** **0.9858**

- **Stage 2 Multiclass Classifier:**
  - Trained to classify specific dark-pattern types across 7 categories.
  - Validation Accuracy: **92.05%**.
  - All models, encoders, and vectorizers exported with `joblib` into `backend/ai/models/`.

### Phase 4: Inference Engine & Hybrid System Integration
- Implemented [`backend/ai/detector.py`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/backend/ai/detector.py):
  - In-memory singleton with text segmentation (extracting candidates from page body, buttons, and placeholders).
  - Two-stage classification returning confidence scores and category labels.
- Enhanced [`backend/detectors/dark_patterns.py`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/backend/detectors/dark_patterns.py):
  - Fuses rule-based detections with AI model detections.
  - Generates unified findings with `detection_method` ("Hybrid (Rules + AI)", "AI Model", or "Rule-Based").
- Updated [`backend/app.py`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/backend/app.py):
  - Added AI readiness status to `GET /`.
  - Exposes `dark_pattern_analysis` at top level and inside `security_analysis` for 100% backward compatibility.
- Updated Frontend [`App.jsx`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/frontend/src/App.jsx) and [`App.css`](file:///c:/Users/Amruta%20Tarage/OneDrive/Documents/projects/Final-Year-Project/frontend/src/App.css):
  - Added visual pills for detection method (`🤖 Hybrid (Rules + AI)`) and calibrated confidence (`🎯 100% Conf`).

---

## Verification Results

1. **Model Training & Accuracy**:
   - Validation F1: `0.9659` | Test F1: `0.9518` | Test ROC-AUC: `0.9858`.
2. **End-to-End Hybrid Detection**:
   - Verified on local test site data: detected 4 distinct patterns including Urgency, Scarcity, Confirmshaming, and Forced Registration with calibrated probabilities up to 99.9%.
3. **Frontend Build**:
   - `npm run build` completed cleanly in 532ms with zero errors.
