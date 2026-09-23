"""
DarkShield AI - Baseline ML Model Training & Comparison Pipeline
================================================================

Trains and systematically compares baseline ML classifiers on the
EC-DarkPattern dataset using TF-IDF feature representations.

Models Evaluated:
1. Multinomial Naive Bayes (MultinomialNB)
2. Logistic Regression (L2 regularization, balanced weights)
3. Calibrated Linear Support Vector Machine (LinearSVC + Platt Calibration)
4. Random Forest Classifier

Architecture:
- Two-Stage Detection:
  Stage 1: Binary Classifier (Dark Pattern vs. Not Dark Pattern)
  Stage 2: Multiclass Category Classifier (Scarcity, Social Proof, Urgency, etc.)
- Strict evaluation on Validation split for model selection.
- Final unbiased evaluation of the winning model on unseen Test split.
- Artifact serialization with joblib into `backend/ai/models/`.
"""

import os
import sys
import json
import joblib
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
)

from backend.ai.preprocessing import load_processed_splits, clean_text

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# -------------------------------------------------
# PATHS
# -------------------------------------------------

AI_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(AI_DIR, "models")
METRICS_PATH = os.path.join(MODELS_DIR, "evaluation_metrics.json")


# -------------------------------------------------
# MODEL EVALUATION HELPERS
# -------------------------------------------------

def evaluate_binary_model(model, X_feat, y_true, model_name: str) -> dict:
    """Compute comprehensive binary classification metrics."""
    y_pred = model.predict(X_feat)
    
    if hasattr(model, "predict_proba"):
        y_prob = model.predict_proba(X_feat)[:, 1]
    elif hasattr(model, "decision_function"):
        df_vals = model.decision_function(X_feat)
        # Apply sigmoid to convert to pseudo-probabilities
        y_prob = 1 / (1 + np.exp(-df_vals))
    else:
        y_prob = y_pred.astype(float)
        
    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    
    try:
        roc_auc = float(roc_auc_score(y_true, y_prob))
    except Exception:
        roc_auc = 0.0
        
    try:
        pr_auc = float(average_precision_score(y_true, y_prob))
    except Exception:
        pr_auc = 0.0
        
    cm = confusion_matrix(y_true, y_pred).tolist()
    
    return {
        "model_name": model_name,
        "accuracy": round(acc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1_score": round(f1, 4),
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "confusion_matrix": {
            "tn": cm[0][0],
            "fp": cm[0][1],
            "fn": cm[1][0],
            "tp": cm[1][1],
        },
        "report": classification_report(y_true, y_pred, target_names=["Not Dark Pattern", "Dark Pattern"], output_dict=True)
    }


def print_metrics_table(results: list):
    """Print formatted comparison table of models."""
    header = f"{'Model':<28} | {'Accuracy':<8} | {'Precision':<9} | {'Recall':<8} | {'F1-Score':<8} | {'ROC-AUC':<8}"
    divider = "-" * len(header)
    print(divider)
    print(header)
    print(divider)
    
    for r in results:
        print(
            f"{r['model_name']:<28} | "
            f"{r['accuracy']:<8.4f} | "
            f"{r['precision']:<9.4f} | "
            f"{r['recall']:<8.4f} | "
            f"{r['f1_score']:<8.4f} | "
            f"{r['roc_auc']:<8.4f}"
        )
    print(divider)


# -------------------------------------------------
# MAIN TRAINING PIPELINE
# -------------------------------------------------

def train_and_evaluate():
    """Execute training, validation comparison, test evaluation, and model export."""
    os.makedirs(MODELS_DIR, exist_ok=True)
    
    print("============================================================")
    print("  DarkShield AI — ML Model Training & Comparison")
    print("============================================================")
    
    # 1. Load Preprocessed Splits
    print("\n[Step 1] Loading preprocessed dataset splits...")
    train_df, val_df, test_df, split_info = load_processed_splits()
    
    print(f"  Train: {len(train_df)} samples")
    print(f"  Val:   {len(val_df)} samples")
    print(f"  Test:  {len(test_df)} samples")
    
    X_train_raw = train_df["cleaned_text"].fillna("")
    y_train = train_df["label"].values
    
    X_val_raw = val_df["cleaned_text"].fillna("")
    y_val = val_df["label"].values
    
    X_test_raw = test_df["cleaned_text"].fillna("")
    y_test = test_df["label"].values
    
    # 2. Fit TF-IDF Vectorizer
    print("\n[Step 2] Extracting TF-IDF Features (unigrams + bigrams)...")
    # Retain function words and punctuation triggers (sublinear_tf=True, min_df=2)
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=12000,
        sublinear_tf=True,
        min_df=2,
        strip_accents="unicode"
    )
    
    X_train_tfidf = vectorizer.fit_transform(X_train_raw)
    X_val_tfidf = vectorizer.transform(X_val_raw)
    X_test_tfidf = vectorizer.transform(X_test_raw)
    
    print(f"  TF-IDF Feature vocabulary size: {len(vectorizer.vocabulary_)} n-grams")
    
    # 3. Define Candidate Models
    candidate_models = {
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.2),
        "Logistic Regression": LogisticRegression(
            C=2.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ),
        "Calibrated Linear SVM": CalibratedClassifierCV(
            estimator=LinearSVC(C=1.0, random_state=42, max_iter=2500),
            method="sigmoid",
            cv=3
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=250,
            max_depth=40,
            random_state=42,
            n_jobs=-1
        )
    }
    
    # 4. Train and Evaluate on Validation Split
    print("\n[Step 3] Training and evaluating candidate models on Validation split...")
    val_results = []
    trained_models = {}
    
    for name, model in candidate_models.items():
        print(f"  Training {name}...")
        model.fit(X_train_tfidf, y_train)
        metrics = evaluate_binary_model(model, X_val_tfidf, y_val, name)
        val_results.append(metrics)
        trained_models[name] = model
        
    print("\nValidation Performance Comparison:")
    print_metrics_table(val_results)
    
    # 5. Select Best Binary Model based on F1-Score
    best_val_result = max(val_results, key=lambda x: (x["f1_score"], x["roc_auc"]))
    best_model_name = best_val_result["model_name"]
    best_binary_model = trained_models[best_model_name]
    
    print(f"\n🏆 Best Binary Classifier: {best_model_name}")
    print(f"   Validation F1: {best_val_result['f1_score']:.4f} | ROC-AUC: {best_val_result['roc_auc']:.4f}")
    
    # 6. Evaluate Best Model on Unseen Test Split
    print("\n[Step 4] Evaluating Best Model on Unseen Test Split...")
    test_metrics = evaluate_binary_model(best_binary_model, X_test_tfidf, y_test, f"{best_model_name} (Test Set)")
    
    print_metrics_table([test_metrics])
    print("\nDetailed Test Classification Report:")
    test_rep = classification_report(y_test, best_binary_model.predict(X_test_tfidf), target_names=["Not Dark Pattern", "Dark Pattern"])
    print(test_rep)
    
    # 7. Train Stage 2 Multiclass Category Classifier
    print("\n[Step 5] Training Multiclass Category Classifier (Pattern Category)...")
    # Filter dark patterns only from training set for specialized category classifier
    train_dark = train_df[train_df["label"] == 1].copy()
    val_dark = val_df[val_df["label"] == 1].copy()
    test_dark = test_df[test_df["label"] == 1].copy()
    
    category_encoder = LabelEncoder()
    y_cat_train = category_encoder.fit_transform(train_dark["Pattern Category"])
    
    cat_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        max_features=8000,
        sublinear_tf=True,
        min_df=2
    )
    X_cat_train_tfidf = cat_vectorizer.fit_transform(train_dark["cleaned_text"])
    
    category_classifier = CalibratedClassifierCV(
        estimator=LinearSVC(C=1.0, random_state=42, max_iter=2500),
        method="sigmoid",
        cv=3
    )
    category_classifier.fit(X_cat_train_tfidf, y_cat_train)
    
    # Evaluate category classifier on validation dark patterns
    X_cat_val_tfidf = cat_vectorizer.transform(val_dark["cleaned_text"])
    y_cat_val = category_encoder.transform(val_dark["Pattern Category"])
    y_cat_val_pred = category_classifier.predict(X_cat_val_tfidf)
    cat_val_acc = accuracy_score(y_cat_val, y_cat_val_pred)
    cat_val_f1_macro = f1_score(y_cat_val, y_cat_val_pred, average="macro", zero_division=0)
    
    print(f"  Category Classifier Validation Accuracy: {cat_val_acc:.4f} | Macro-F1: {cat_val_f1_macro:.4f}")
    print(f"  Recognized Categories ({len(category_encoder.classes_)}): {list(category_encoder.classes_)}")
    
    # 8. Save Models and Metadata
    print("\n[Step 6] Saving trained models and artifacts to disk...")
    
    binary_vectorizer_path = os.path.join(MODELS_DIR, "binary_vectorizer.joblib")
    binary_model_path = os.path.join(MODELS_DIR, "binary_model.joblib")
    category_vectorizer_path = os.path.join(MODELS_DIR, "category_vectorizer.joblib")
    category_model_path = os.path.join(MODELS_DIR, "category_model.joblib")
    category_encoder_path = os.path.join(MODELS_DIR, "category_encoder.joblib")
    
    joblib.dump(vectorizer, binary_vectorizer_path)
    joblib.dump(best_binary_model, binary_model_path)
    joblib.dump(cat_vectorizer, category_vectorizer_path)
    joblib.dump(category_classifier, category_model_path)
    joblib.dump(category_encoder, category_encoder_path)
    
    # Metrics JSON
    final_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_binary_model": best_model_name,
        "validation_comparison": val_results,
        "test_evaluation": test_metrics,
        "category_evaluation": {
            "validation_accuracy": round(float(cat_val_acc), 4),
            "validation_f1_macro": round(float(cat_val_f1_macro), 4),
            "classes": list(category_encoder.classes_)
        },
        "artifact_paths": {
            "binary_vectorizer": binary_vectorizer_path,
            "binary_model": binary_model_path,
            "category_vectorizer": category_vectorizer_path,
            "category_model": category_model_path,
            "category_encoder": category_encoder_path
        }
    }
    
    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)
        
    print(f"  ✓ {binary_vectorizer_path}")
    print(f"  ✓ {binary_model_path}")
    print(f"  ✓ {category_vectorizer_path}")
    print(f"  ✓ {category_model_path}")
    print(f"  ✓ {category_encoder_path}")
    print(f"  ✓ {METRICS_PATH}")
    
    print("\n============================================================")
    print("  TRAINING & EVALUATION COMPLETE")
    print("============================================================")
    
    return final_report


if __name__ == "__main__":
    train_and_evaluate()
