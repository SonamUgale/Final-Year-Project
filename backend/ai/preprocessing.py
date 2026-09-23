"""
DarkShield AI - Data Preprocessing & Splitting Pipeline
======================================================

Handles data cleaning, text normalization, and leak-free
group-based train/validation/test splitting for the EC-DarkPattern dataset.

Strategy:
- Cleans and normalizes text (whitespace, HTML entities, unicode artifacts).
- Performs Stratified Group splitting on `page_id` to prevent data leakage:
  all samples from the same website page stay in the same split.
- Ratios: ~70% Train, ~15% Validation, ~15% Test.
- Preserves balanced 50/50 binary class distribution.
- Exports processed datasets to `backend/ai/data/processed/` with `split_info.json`.
"""

import os
import sys
import re
import html
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# -------------------------------------------------
# PATH CONFIGURATION
# -------------------------------------------------

AI_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DIR = os.path.join(AI_DIR, "data", "raw")
RAW_DATASET_PATH = os.path.join(RAW_DIR, "dataset.tsv")
PROCESSED_DIR = os.path.join(AI_DIR, "data", "processed")

TRAIN_PATH = os.path.join(PROCESSED_DIR, "train.csv")
VAL_PATH = os.path.join(PROCESSED_DIR, "val.csv")
TEST_PATH = os.path.join(PROCESSED_DIR, "test.csv")
SPLIT_INFO_PATH = os.path.join(PROCESSED_DIR, "split_info.json")

RANDOM_SEED = 42


# -------------------------------------------------
# TEXT CLEANING
# -------------------------------------------------

def clean_text(text: str) -> str:
    """
    Clean and normalize input text for NLP modeling.
    
    1. Unescape HTML entities (&amp;, &nbsp;, etc.)
    2. Normalize whitespace (tabs, newlines, multiple spaces -> single space)
    3. Strip surrounding whitespace
    """
    if not isinstance(text, str):
        return ""
    
    # Unescape HTML entities
    text = html.unescape(text)
    
    # Replace non-breaking spaces and other unicode spaces
    text = text.replace("\u00a0", " ").replace("\u200b", "")
    
    # Normalize multiple whitespace characters into single space
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()


# -------------------------------------------------
# DATA LOADING & SPLITTING
# -------------------------------------------------

def load_raw_dataset(path: str = RAW_DATASET_PATH) -> pd.DataFrame:
    """Load the raw TSV dataset."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Raw dataset not found at: {path}")
    
    df = pd.read_csv(path, sep="\t")
    return df


def preprocess_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean text column while preserving original fields."""
    df_clean = df.copy()
    
    # Ensure text is string and clean it
    df_clean["cleaned_text"] = df_clean["text"].astype(str).apply(clean_text)
    
    # Ensure label is int
    df_clean["label"] = df_clean["label"].astype(int)
    
    # Standardize column types
    df_clean["page_id"] = df_clean["page_id"].astype(int)
    df_clean["Pattern Category"] = df_clean["Pattern Category"].astype(str).str.strip()
    
    return df_clean


def perform_group_split(df: pd.DataFrame, random_state: int = RANDOM_SEED):
    """
    Split dataset into Train (70%), Val (15%), Test (15%) using
    StratifiedGroupKFold on `page_id` to prevent data leakage.
    """
    # 20 folds gives 5% chunks:
    # Folds 0..2  (3 folds) = 15% Test
    # Folds 3..5  (3 folds) = 15% Val
    # Folds 6..19 (14 folds) = 70% Train
    sgkf = StratifiedGroupKFold(n_splits=20, shuffle=True, random_state=random_state)
    folds = list(sgkf.split(df, df["label"], df["page_id"]))
    
    test_idx = []
    for i in range(3):
        test_idx.extend(folds[i][1])
        
    val_idx = []
    for i in range(3, 6):
        val_idx.extend(folds[i][1])
        
    train_idx = []
    for i in range(6, 20):
        train_idx.extend(folds[i][1])
        
    train_df = df.iloc[train_idx].copy().reset_index(drop=True)
    val_df = df.iloc[val_idx].copy().reset_index(drop=True)
    test_df = df.iloc[test_idx].copy().reset_index(drop=True)
    
    # Verify strict zero leakage between page_ids
    train_pages = set(train_df["page_id"])
    val_pages = set(val_df["page_id"])
    test_pages = set(test_df["page_id"])
    
    leakage_train_val = train_pages & val_pages
    leakage_train_test = train_pages & test_pages
    leakage_val_test = val_pages & test_pages
    
    if leakage_train_val or leakage_train_test or leakage_val_test:
        raise ValueError(
            f"DATA LEAKAGE DETECTED! "
            f"train/val overlap: {len(leakage_train_val)}, "
            f"train/test overlap: {len(leakage_train_test)}, "
            f"val/test overlap: {len(leakage_val_test)}"
        )
        
    return train_df, val_df, test_df


def compute_split_stats(df: pd.DataFrame, name: str) -> dict:
    """Compute summary statistics for a dataset split."""
    total = len(df)
    label_counts = df["label"].value_counts().to_dict()
    category_counts = df["Pattern Category"].value_counts().to_dict()
    unique_pages = int(df["page_id"].nunique())
    
    label_0_count = int(label_counts.get(0, 0))
    label_1_count = int(label_counts.get(1, 0))
    
    return {
        "name": name,
        "total_samples": total,
        "unique_pages": unique_pages,
        "label_distribution": {
            "not_dark_pattern_0": label_0_count,
            "dark_pattern_1": label_1_count,
            "dark_pattern_ratio": round(label_1_count / total, 4) if total > 0 else 0
        },
        "category_distribution": {k: int(v) for k, v in category_counts.items()}
    }


def save_processed_data(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    out_dir: str = PROCESSED_DIR
) -> dict:
    """Save processed splits to CSV and write split_info.json."""
    os.makedirs(out_dir, exist_ok=True)
    
    train_df.to_csv(TRAIN_PATH, index=False, encoding="utf-8")
    val_df.to_csv(VAL_PATH, index=False, encoding="utf-8")
    test_df.to_csv(TEST_PATH, index=False, encoding="utf-8")
    
    stats_train = compute_split_stats(train_df, "train")
    stats_val = compute_split_stats(val_df, "validation")
    stats_test = compute_split_stats(test_df, "test")
    
    split_info = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "method": "StratifiedGroupKFold(n_splits=20, shuffle=True) on page_id",
        "leakage_verification": "PASSED (0 overlapping page_ids across all splits)",
        "total_samples": len(train_df) + len(val_df) + len(test_df),
        "splits": {
            "train": stats_train,
            "validation": stats_val,
            "test": stats_test
        }
    }
    
    with open(SPLIT_INFO_PATH, "w", encoding="utf-8") as f:
        json.dump(split_info, f, indent=2)
        
    return split_info


def load_processed_splits(processed_dir: str = PROCESSED_DIR):
    """
    Load preprocessed Train, Validation, and Test splits.
    
    Returns:
        tuple: (train_df, val_df, test_df, split_info)
    """
    train_p = os.path.join(processed_dir, "train.csv")
    val_p = os.path.join(processed_dir, "val.csv")
    test_p = os.path.join(processed_dir, "test.csv")
    info_p = os.path.join(processed_dir, "split_info.json")
    
    if not (os.path.exists(train_p) and os.path.exists(val_p) and os.path.exists(test_p)):
        raise FileNotFoundError("Processed splits not found. Run preprocessing.py first.")
        
    train_df = pd.read_csv(train_p)
    val_df = pd.read_csv(val_p)
    test_df = pd.read_csv(test_p)
    
    split_info = {}
    if os.path.exists(info_p):
        with open(info_p, "r", encoding="utf-8") as f:
            split_info = json.load(f)
            
    return train_df, val_df, test_df, split_info


# -------------------------------------------------
# CLI RUNNER
# -------------------------------------------------

def run_pipeline():
    """Execute the full preprocessing and splitting pipeline."""
    print("============================================================")
    print("  DarkShield AI — Data Preprocessing Pipeline")
    print("============================================================")
    print(f"Loading raw dataset from: {RAW_DATASET_PATH}")
    
    df_raw = load_raw_dataset()
    print(f"Raw dataset loaded: {len(df_raw)} rows, {len(df_raw.columns)} columns.")
    
    print("\nApplying text cleaning and normalization...")
    df_clean = preprocess_dataframe(df_raw)
    
    print("\nPerforming leak-free Stratified Group split on 'page_id'...")
    train_df, val_df, test_df = perform_group_split(df_clean, random_state=RANDOM_SEED)
    
    print("\nSplit Sizes:")
    print(f"  Train:      {len(train_df):5d} samples ({len(train_df)/len(df_clean)*100:.1f}%) | {train_df['page_id'].nunique()} unique page_ids")
    print(f"  Validation: {len(val_df):5d} samples ({len(val_df)/len(df_clean)*100:.1f}%) | {val_df['page_id'].nunique()} unique page_ids")
    print(f"  Test:       {len(test_df):5d} samples ({len(test_df)/len(df_clean)*100:.1f}%) | {test_df['page_id'].nunique()} unique page_ids")
    
    print("\nClass Balance (Label 1 - Dark Pattern ratio):")
    print(f"  Train:      {train_df['label'].mean()*100:.2f}%")
    print(f"  Validation: {val_df['label'].mean()*100:.2f}%")
    print(f"  Test:       {test_df['label'].mean()*100:.2f}%")
    
    print("\nSaving splits to disk...")
    info = save_processed_data(train_df, val_df, test_df)
    
    print(f"  ✓ {TRAIN_PATH}")
    print(f"  ✓ {VAL_PATH}")
    print(f"  ✓ {TEST_PATH}")
    print(f"  ✓ {SPLIT_INFO_PATH}")
    
    print("\n============================================================")
    print("  PREPROCESSING COMPLETED SUCCESSFULLY (Zero Leakage)")
    print("============================================================")


if __name__ == "__main__":
    run_pipeline()
