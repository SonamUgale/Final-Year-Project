"""
DarkShield AI - ML Model Training, Evaluation & Comparison Pipeline (V2)
======================================================================

Trains and systematically evaluates ML classifiers on the enriched
EC-DarkPattern dataset using TF-IDF feature representations.

Phase 2 Enhancements:
1. Enriched with 300 institutional/academic samples to prevent false positives on college sites.
2. Enriched with 130 minority dark patterns (Forced Action, Sneaking, Obstruction).
3. Evaluates class_weight='balanced' in LinearSVC and Logistic Regression.
4. Performs 5-fold Stratified Group Cross-Validation on the training set.
5. Preserves Platt probability calibration via CalibratedClassifierCV.
6. Exports versioned artifacts (v2) and active production models.
7. Logs comparative V1 vs V2 performance metrics.
"""

import os
import sys
import json
import shutil
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
from sklearn.model_selection import StratifiedGroupKFold
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
# PATH CONFIGURATION
# -------------------------------------------------

AI_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(AI_DIR, "models")
V1_BACKUP_DIR = os.path.join(MODELS_DIR, "v1_backup")
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
        "report": classification_report(
            y_true, y_pred,
            target_names=["Not Dark Pattern", "Dark Pattern"],
            output_dict=True
        )
    }


def print_metrics_table(results: list, title: str = "Model Comparison"):
    """Print formatted comparison table of models."""
    header = f"{'Model':<30} | {'Accuracy':<8} | {'Precision':<9} | {'Recall':<8} | {'F1-Score':<8} | {'ROC-AUC':<8}"
    divider = "-" * len(header)
    print(f"\n{title}:")
    print(divider)
    print(header)
    print(divider)

    for r in results:
        print(
            f"{r['model_name']:<30} | "
            f"{r['accuracy']:<8.4f} | "
            f"{r['precision']:<9.4f} | "
            f"{r['recall']:<8.4f} | "
            f"{r['f1_score']:<8.4f} | "
            f"{r['roc_auc']:<8.4f}"
        )
    print(divider)


# -------------------------------------------------
# CROSS-VALIDATION PIPELINE
# -------------------------------------------------

def run_cross_validation(train_df: pd.DataFrame, n_splits: int = 5, random_state: int = 42) -> dict:
    """
    Perform 5-fold Stratified Group Cross-Validation on the training set
    to verify model stability and generalizability without group leakage.
    """
    print(f"\n[Cross-Validation] Executing {n_splits}-Fold Stratified Group CV on Training Set...")
    sgkf = StratifiedGroupKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    X_texts = train_df["cleaned_text"].fillna("").values
    y = train_df["label"].values
    groups = train_df["page_id"].values

    fold_metrics = []

    for fold_num, (tr_idx, val_idx) in enumerate(sgkf.split(X_texts, y, groups), 1):
        # Verify 0 leakage between fold train and fold val
        tr_groups = set(groups[tr_idx])
        val_groups = set(groups[val_idx])
        assert len(tr_groups & val_groups) == 0, f"CV Fold {fold_num} page_id leakage detected!"

        fold_vec = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=12000,
            sublinear_tf=True,
            min_df=2,
            strip_accents="unicode"
        )
        X_tr = fold_vec.fit_transform(X_texts[tr_idx])
        X_v = fold_vec.transform(X_texts[val_idx])

        clf = CalibratedClassifierCV(
            estimator=LinearSVC(C=1.0, class_weight="balanced", random_state=random_state, max_iter=2500),
            method="sigmoid",
            cv=3
        )
        clf.fit(X_tr, y[tr_idx])

        m = evaluate_binary_model(clf, X_v, y[val_idx], f"Fold {fold_num}")
        fold_metrics.append(m)
        print(f"  Fold {fold_num}/{n_splits} — Acc: {m['accuracy']:.4f} | Prec: {m['precision']:.4f} | Rec: {m['recall']:.4f} | F1: {m['f1_score']:.4f} | ROC-AUC: {m['roc_auc']:.4f}")

    # Summary
    accs = [m["accuracy"] for m in fold_metrics]
    precs = [m["precision"] for m in fold_metrics]
    recs = [m["recall"] for m in fold_metrics]
    f1s = [m["f1_score"] for m in fold_metrics]
    aucs = [m["roc_auc"] for m in fold_metrics]

    cv_summary = {
        "n_splits": n_splits,
        "folds": fold_metrics,
        "mean_accuracy": round(float(np.mean(accs)), 4),
        "std_accuracy": round(float(np.std(accs)), 4),
        "mean_precision": round(float(np.mean(precs)), 4),
        "std_precision": round(float(np.std(precs)), 4),
        "mean_recall": round(float(np.mean(recs)), 4),
        "std_recall": round(float(np.std(recs)), 4),
        "mean_f1_score": round(float(np.mean(f1s)), 4),
        "std_f1_score": round(float(np.std(f1s)), 4),
        "mean_roc_auc": round(float(np.mean(aucs)), 4),
        "std_roc_auc": round(float(np.std(aucs)), 4),
    }

    print(f"\n  ✓ CV Mean F1-Score: {cv_summary['mean_f1_score']:.4f} (±{cv_summary['std_f1_score']:.4f})")
    print(f"  ✓ CV Mean Accuracy: {cv_summary['mean_accuracy']:.4f} (±{cv_summary['std_accuracy']:.4f})")
    print(f"  ✓ CV Mean ROC-AUC:  {cv_summary['mean_roc_auc']:.4f} (±{cv_summary['std_roc_auc']:.4f})")

    return cv_summary


# -------------------------------------------------
# BACKUP ORIGINAL V1 ARTIFACTS
# -------------------------------------------------

def backup_v1_artifacts():
    """Ensure existing V1 models are safely archived before overwriting."""
    os.makedirs(V1_BACKUP_DIR, exist_ok=True)
    artifacts = [
        "binary_model.joblib",
        "binary_vectorizer.joblib",
        "category_model.joblib",
        "category_vectorizer.joblib",
        "category_encoder.joblib",
        "evaluation_metrics.json"
    ]
    for art in artifacts:
        src = os.path.join(MODELS_DIR, art)
        dst = os.path.join(V1_BACKUP_DIR, art)
        if os.path.exists(src) and not os.path.exists(dst):
            shutil.copyfile(src, dst)
            print(f"  Archived V1: {art} -> v1_backup/")


# -------------------------------------------------
# MAIN TRAINING PIPELINE
# -------------------------------------------------

def train_and_evaluate():
    """Execute training, cross-validation, comparison, and versioned export."""
    os.makedirs(MODELS_DIR, exist_ok=True)

    print("============================================================")
    print("  DarkShield AI — ML Training & Retraining Pipeline (V2)")
    print("============================================================")

    # 0. Backup existing V1 models
    print("\n[Step 0] Backing up baseline V1 models...")
    backup_v1_artifacts()

    # 1. Load Preprocessed Splits
    print("\n[Step 1] Loading preprocessed dataset splits...")
    train_df, val_df, test_df, split_info = load_processed_splits()

    print(f"  Train: {len(train_df)} samples ({train_df['page_id'].nunique()} unique page_ids)")
    print(f"  Val:   {len(val_df)} samples ({val_df['page_id'].nunique()} unique page_ids)")
    print(f"  Test:  {len(test_df)} samples ({test_df['page_id'].nunique()} unique page_ids)")

    X_train_raw = train_df["cleaned_text"].fillna("")
    y_train = train_df["label"].values

    X_val_raw = val_df["cleaned_text"].fillna("")
    y_val = val_df["label"].values

    X_test_raw = test_df["cleaned_text"].fillna("")
    y_test = test_df["label"].values

    # 2. Fit TF-IDF Vectorizer
    print("\n[Step 2] Extracting TF-IDF Features (unigrams + bigrams)...")
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

    # 3. 5-Fold Stratified Group Cross-Validation on Training Set
    cv_results = run_cross_validation(train_df, n_splits=5, random_state=42)

    # 4. Define Candidate Models (with balanced class weights)
    print("\n[Step 3] Training candidate classifiers on full training split...")
    candidate_models = {
        "Multinomial Naive Bayes": MultinomialNB(alpha=0.2),
        "Logistic Regression": LogisticRegression(
            C=2.0,
            max_iter=1000,
            class_weight="balanced",
            random_state=42
        ),
        "Calibrated Linear SVM": CalibratedClassifierCV(
            estimator=LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=2500),
            method="sigmoid",
            cv=3
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=250,
            max_depth=40,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1
        )
    }

    val_results = []
    trained_models = {}

    for name, model in candidate_models.items():
        print(f"  Training {name}...")
        model.fit(X_train_tfidf, y_train)
        metrics = evaluate_binary_model(model, X_val_tfidf, y_val, name)
        val_results.append(metrics)
        trained_models[name] = model

    print_metrics_table(val_results, "Validation Performance Comparison (V2)")

    # 5. Select Best Binary Model based on F1-Score
    best_val_result = max(val_results, key=lambda x: (x["f1_score"], x["roc_auc"]))
    best_model_name = best_val_result["model_name"]
    best_binary_model = trained_models[best_model_name]

    print(f"\n🏆 Best Binary Classifier: {best_model_name}")
    print(f"   Validation F1: {best_val_result['f1_score']:.4f} | ROC-AUC: {best_val_result['roc_auc']:.4f}")

    # 6. Evaluate Best Model on Unseen Test Split
    print("\n[Step 4] Evaluating Best Model on Unseen Test Split...")
    test_metrics = evaluate_binary_model(best_binary_model, X_test_tfidf, y_test, f"{best_model_name} (Test Set)")
    print_metrics_table([test_metrics], "Final Test Set Evaluation (Unseen)")

    cm = test_metrics["confusion_matrix"]
    print(f"\nTest Confusion Matrix:")
    print(f"  True Negatives (TN - Clean correctly identified):     {cm['tn']}")
    print(f"  False Positives (FP - Clean flagged as dark pattern): {cm['fp']}")
    print(f"  False Negatives (FN - Dark pattern missed):          {cm['fn']}")
    print(f"  True Positives (TP - Dark pattern correctly caught): {cm['tp']}")

    # 7. Train Stage 2 Multiclass Category Classifier
    print("\n[Step 5] Training Multiclass Category Classifier (Pattern Category)...")
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
        estimator=LinearSVC(C=1.0, class_weight="balanced", random_state=42, max_iter=2500),
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

    # Detailed per-class category report
    cat_report = classification_report(
        y_cat_val, y_cat_val_pred,
        target_names=list(category_encoder.classes_),
        output_dict=True,
        zero_division=0
    )

    print(f"\n  Category Classifier Validation Accuracy: {cat_val_acc:.4f} | Macro-F1: {cat_val_f1_macro:.4f}")
    print(f"  Recognized Categories ({len(category_encoder.classes_)}): {list(category_encoder.classes_)}")
    print("\nCategory Classification Report (Validation Split):")
    print(classification_report(y_cat_val, y_cat_val_pred, target_names=list(category_encoder.classes_), zero_division=0))

    # 8. Load historical V1 metrics if available for comparison
    v1_metrics = {}
    v1_metrics_file = os.path.join(V1_BACKUP_DIR, "evaluation_metrics.json")
    if os.path.exists(v1_metrics_file):
        with open(v1_metrics_file, "r", encoding="utf-8") as f:
            v1_metrics = json.load(f)

    # 9. Save Models and Metadata
    print("\n[Step 6] Saving trained models and versioned artifacts (v2)...")

    # Paths for active models
    binary_vectorizer_path = os.path.join(MODELS_DIR, "binary_vectorizer.joblib")
    binary_model_path = os.path.join(MODELS_DIR, "binary_model.joblib")
    category_vectorizer_path = os.path.join(MODELS_DIR, "category_vectorizer.joblib")
    category_model_path = os.path.join(MODELS_DIR, "category_model.joblib")
    category_encoder_path = os.path.join(MODELS_DIR, "category_encoder.joblib")

    # Paths for versioned v2 models
    binary_vectorizer_v2_path = os.path.join(MODELS_DIR, "binary_vectorizer_v2.joblib")
    binary_model_v2_path = os.path.join(MODELS_DIR, "binary_model_v2.joblib")
    category_vectorizer_v2_path = os.path.join(MODELS_DIR, "category_vectorizer_v2.joblib")
    category_model_v2_path = os.path.join(MODELS_DIR, "category_model_v2.joblib")
    category_encoder_v2_path = os.path.join(MODELS_DIR, "category_encoder_v2.joblib")

    # Save to both active and v2
    for p in [binary_vectorizer_path, binary_vectorizer_v2_path]:
        joblib.dump(vectorizer, p)
    for p in [binary_model_path, binary_model_v2_path]:
        joblib.dump(best_binary_model, p)
    for p in [category_vectorizer_path, category_vectorizer_v2_path]:
        joblib.dump(cat_vectorizer, p)
    for p in [category_model_path, category_model_v2_path]:
        joblib.dump(category_classifier, p)
    for p in [category_encoder_path, category_encoder_v2_path]:
        joblib.dump(category_encoder, p)

    # Construct comprehensive evaluation metrics report
    final_report = {
        "version": "v2",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "selected_binary_model": best_model_name,
        "dataset_summary": {
            "total_samples": len(train_df) + len(val_df) + len(test_df),
            "train_samples": len(train_df),
            "val_samples": len(val_df),
            "test_samples": len(test_df),
            "binary_distribution": {
                "not_dark_pattern": int((train_df["label"] == 0).sum() + (val_df["label"] == 0).sum() + (test_df["label"] == 0).sum()),
                "dark_pattern": int((train_df["label"] == 1).sum() + (val_df["label"] == 1).sum() + (test_df["label"] == 1).sum()),
            },
            "category_counts": {k: int(v) for k, v in train_dark["Pattern Category"].value_counts().items()}
        },
        "v1_baseline_metrics": v1_metrics.get("test_evaluation", {}),
        "v2_cross_validation_5fold": cv_results,
        "v2_validation_comparison": val_results,
        "v2_test_evaluation": test_metrics,
        "v2_category_evaluation": {
            "validation_accuracy": round(float(cat_val_acc), 4),
            "validation_f1_macro": round(float(cat_val_f1_macro), 4),
            "classes": list(category_encoder.classes_),
            "report": cat_report
        },
        "artifact_paths": {
            "binary_vectorizer": binary_vectorizer_path,
            "binary_model": binary_model_path,
            "category_vectorizer": category_vectorizer_path,
            "category_model": category_model_path,
            "category_encoder": category_encoder_path,
            "binary_model_v2": binary_model_v2_path,
            "category_model_v2": category_model_v2_path
        }
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    v2_metrics_path = os.path.join(MODELS_DIR, "evaluation_metrics_v2.json")
    with open(v2_metrics_path, "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print(f"  ✓ {binary_model_path}")
    print(f"  ✓ {binary_model_v2_path}")
    print(f"  ✓ {category_model_path}")
    print(f"  ✓ {category_model_v2_path}")
    print(f"  ✓ {METRICS_PATH}")
    print(f"  ✓ {v2_metrics_path}")

    print("\n============================================================")
    print("  RETRAINING & EVALUATION COMPLETE (V2)")
    print("============================================================")

    return final_report


if __name__ == "__main__":
    train_and_evaluate()
