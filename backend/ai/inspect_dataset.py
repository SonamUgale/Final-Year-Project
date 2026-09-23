"""
DarkShield AI - Dataset Inspection Script
==========================================

Inspects the EC-DarkPattern dataset (dataset.tsv) and produces
a comprehensive summary report including:

- Shape and columns
- Column data types
- Label distribution (binary)
- Pattern Category distribution (multiclass)
- Missing values
- Duplicate analysis
- page_id distribution (data leakage risk)
- Text length statistics
- Sample examples per category

Usage:
    python -m backend.ai.inspect_dataset
"""

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import numpy as np


# -------------------------------------------------
# PATHS
# -------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_DATA_DIR = os.path.join(SCRIPT_DIR, "data", "raw")
DATASET_PATH = os.path.join(RAW_DATA_DIR, "dataset.tsv")


def load_dataset():
    """Load the raw TSV dataset."""
    if not os.path.exists(DATASET_PATH):
        print(f"ERROR: Dataset not found at {DATASET_PATH}")
        sys.exit(1)

    df = pd.read_csv(DATASET_PATH, sep="\t")
    return df


def print_separator(title=""):
    """Print a visual separator."""
    print()
    print("=" * 60)
    if title:
        print(f"  {title}")
        print("=" * 60)
    print()


def inspect_basic_info(df):
    """Inspect basic dataset information."""
    print_separator("1. BASIC INFORMATION")

    print(f"Total rows:    {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Columns:       {list(df.columns)}")
    print()

    print("Column data types:")
    for col in df.columns:
        print(f"  {col:20s} → {df[col].dtype}")

    print()
    print("First 5 rows:")
    print(df.head().to_string(index=False))


def inspect_missing_values(df):
    """Inspect missing values."""
    print_separator("2. MISSING VALUES")

    missing = df.isnull().sum()
    total = len(df)

    for col in df.columns:
        count = missing[col]
        pct = (count / total) * 100
        print(f"  {col:20s} → {count:5d} missing ({pct:.2f}%)")

    # Also check for empty strings in text column
    if "text" in df.columns:
        empty_text = (df["text"].astype(str).str.strip() == "").sum()
        print(f"\n  Empty/whitespace-only 'text' rows: {empty_text}")


def inspect_labels(df):
    """Inspect the binary label distribution."""
    print_separator("3. BINARY LABEL DISTRIBUTION")

    if "label" not in df.columns:
        print("  WARNING: 'label' column not found!")
        return

    label_counts = df["label"].value_counts().sort_index()
    total = len(df)

    print(f"  Unique label values: {sorted(df['label'].unique())}")
    print()

    for label_val, count in label_counts.items():
        pct = (count / total) * 100
        label_name = "Dark Pattern" if label_val == 1 else "Not Dark Pattern"
        print(f"  Label {label_val} ({label_name:18s}): {count:5d}  ({pct:.1f}%)")

    print()
    ratio = label_counts.min() / label_counts.max()
    print(f"  Minority/Majority ratio: {ratio:.3f}")

    if ratio < 0.5:
        print("  ⚠ Dataset is moderately imbalanced.")
    elif ratio < 0.25:
        print("  ⚠ Dataset is significantly imbalanced!")
    else:
        print("  ✓ Dataset is reasonably balanced.")


def inspect_categories(df):
    """Inspect the Pattern Category distribution."""
    print_separator("4. PATTERN CATEGORY DISTRIBUTION (MULTICLASS)")

    if "Pattern Category" not in df.columns:
        print("  WARNING: 'Pattern Category' column not found!")
        return

    cat_counts = df["Pattern Category"].value_counts()
    total = len(df)

    print(f"  Unique categories: {len(cat_counts)}")
    print()

    for category, count in cat_counts.items():
        pct = (count / total) * 100
        print(f"  {category:30s}: {count:5d}  ({pct:.1f}%)")

    # Show categories that are dark patterns only
    if "label" in df.columns:
        dark_cats = df[df["label"] == 1]["Pattern Category"].value_counts()
        print()
        print("  Dark-pattern categories only (label=1):")
        for category, count in dark_cats.items():
            pct = (count / total) * 100
            print(f"    {category:28s}: {count:5d}  ({pct:.1f}%)")


def inspect_duplicates(df):
    """Inspect duplicate rows."""
    print_separator("5. DUPLICATE ANALYSIS")

    # Full row duplicates
    full_dupes = df.duplicated().sum()
    print(f"  Exact duplicate rows:       {full_dupes}")

    # Text-only duplicates
    if "text" in df.columns:
        text_dupes = df.duplicated(subset=["text"]).sum()
        print(f"  Duplicate 'text' values:    {text_dupes}")

        # Text + label duplicates
        if "label" in df.columns:
            text_label_dupes = df.duplicated(
                subset=["text", "label"]
            ).sum()
            print(f"  Duplicate text+label pairs: {text_label_dupes}")

        # Contradictory labels (same text, different label)
        if "label" in df.columns:
            text_groups = df.groupby("text")["label"].nunique()
            contradictions = (text_groups > 1).sum()
            print(f"  Contradictory labels (same text, different label): {contradictions}")

            if contradictions > 0:
                print("\n  ⚠ Examples of contradictory labels:")
                contradictory_texts = text_groups[text_groups > 1].index[:5]
                for txt in contradictory_texts:
                    subset = df[df["text"] == txt][["text", "label", "Pattern Category"]]
                    print(f"    Text: \"{txt[:80]}...\"")
                    for _, row in subset.iterrows():
                        print(f"      label={row['label']}, category={row['Pattern Category']}")


def inspect_page_ids(df):
    """Inspect page_id distribution for data leakage analysis."""
    print_separator("6. PAGE_ID DISTRIBUTION (DATA LEAKAGE RISK)")

    if "page_id" not in df.columns:
        print("  WARNING: 'page_id' column not found!")
        return

    unique_pages = df["page_id"].nunique()
    total_rows = len(df)

    print(f"  Total rows:        {total_rows}")
    print(f"  Unique page_ids:   {unique_pages}")
    print(f"  Avg samples/page:  {total_rows / unique_pages:.2f}")

    page_counts = df["page_id"].value_counts()

    print(f"\n  Page_id sample count distribution:")
    print(f"    Min samples per page:    {page_counts.min()}")
    print(f"    Max samples per page:    {page_counts.max()}")
    print(f"    Median samples per page: {page_counts.median():.1f}")
    print(f"    Mean samples per page:   {page_counts.mean():.2f}")

    # Distribution of pages by number of samples
    bins = [1, 2, 3, 5, 10, 20, 50, 100]
    print(f"\n  Pages by sample count:")
    for i in range(len(bins)):
        if i == 0:
            count = (page_counts == bins[i]).sum()
            print(f"    Exactly {bins[i]:3d} sample:    {count:4d} pages")
        else:
            count = ((page_counts > bins[i-1]) & (page_counts <= bins[i])).sum()
            print(f"    {bins[i-1]+1:3d} - {bins[i]:3d} samples:  {count:4d} pages")
    count = (page_counts > bins[-1]).sum()
    print(f"    > {bins[-1]:3d} samples:     {count:4d} pages")

    # Pages that span both labels
    if "label" in df.columns:
        page_label_diversity = df.groupby("page_id")["label"].nunique()
        mixed_pages = (page_label_diversity > 1).sum()
        single_pages = (page_label_diversity == 1).sum()

        print(f"\n  DATA LEAKAGE ANALYSIS:")
        print(f"    Pages with ONLY dark or ONLY non-dark samples: {single_pages}")
        print(f"    Pages with BOTH dark and non-dark samples:     {mixed_pages}")
        print()
        print(f"  ⚠ If page_id groups are split randomly across train/test,")
        print(f"    samples from the SAME page could appear in both sets,")
        print(f"    causing data leakage. A GROUP-BASED SPLIT on page_id")
        print(f"    is recommended.")


def inspect_text_statistics(df):
    """Inspect text length and content statistics."""
    print_separator("7. TEXT STATISTICS")

    if "text" not in df.columns:
        print("  WARNING: 'text' column not found!")
        return

    texts = df["text"].astype(str)
    lengths = texts.str.len()
    word_counts = texts.str.split().str.len()

    print(f"  Character length statistics:")
    print(f"    Min:    {lengths.min():8d}")
    print(f"    Max:    {lengths.max():8d}")
    print(f"    Mean:   {lengths.mean():8.1f}")
    print(f"    Median: {lengths.median():8.1f}")
    print(f"    Std:    {lengths.std():8.1f}")

    print(f"\n  Word count statistics:")
    print(f"    Min:    {word_counts.min():8d}")
    print(f"    Max:    {word_counts.max():8d}")
    print(f"    Mean:   {word_counts.mean():8.1f}")
    print(f"    Median: {word_counts.median():8.1f}")
    print(f"    Std:    {word_counts.std():8.1f}")

    # By label
    if "label" in df.columns:
        print(f"\n  Text length by label:")
        for label_val in sorted(df["label"].unique()):
            subset = df[df["label"] == label_val]
            subset_lengths = subset["text"].astype(str).str.len()
            label_name = "Dark Pattern" if label_val == 1 else "Not Dark Pattern"
            print(
                f"    Label {label_val} ({label_name}): "
                f"mean={subset_lengths.mean():.1f}, "
                f"median={subset_lengths.median():.1f}, "
                f"std={subset_lengths.std():.1f}"
            )


def inspect_sample_examples(df):
    """Show sample examples from each category."""
    print_separator("8. SAMPLE EXAMPLES PER CATEGORY")

    if "Pattern Category" not in df.columns:
        print("  WARNING: 'Pattern Category' column not found!")
        return

    categories = df["Pattern Category"].unique()

    for category in sorted(categories):
        subset = df[df["Pattern Category"] == category]
        sample = subset.sample(n=min(3, len(subset)), random_state=42)

        print(f"\n  [{category}] ({len(subset)} samples)")
        for _, row in sample.iterrows():
            text_preview = str(row["text"])[:100]
            print(f"    → \"{text_preview}\"")


def inspect_splitting_recommendation(df):
    """Provide a recommended splitting strategy."""
    print_separator("9. RECOMMENDED TRAIN/VAL/TEST SPLIT STRATEGY")

    if "page_id" not in df.columns:
        print("  Cannot recommend strategy without 'page_id' column.")
        return

    unique_pages = df["page_id"].nunique()
    total_rows = len(df)

    print(f"  Total samples: {total_rows}")
    print(f"  Unique pages:  {unique_pages}")
    print()
    print("  RECOMMENDATION: GroupShuffleSplit by page_id")
    print()
    print("  Strategy:")
    print("    1. Split page_ids (not individual samples) into groups.")
    print("    2. All samples from a given page_id stay in the SAME split.")
    print("    3. This prevents data leakage from related samples.")
    print()
    print("  Suggested split ratios:")
    print("    Train:      70% of page_ids")
    print("    Validation: 15% of page_ids")
    print("    Test:       15% of page_ids")
    print()
    print("  Use sklearn.model_selection.GroupShuffleSplit")
    print("  with groups=page_id for scientifically defensible splits.")
    print()
    print("  Stratification:")
    print("    Since some pages may have only dark or only non-dark samples,")
    print("    use StratifiedGroupKFold or manual stratified group split")
    print("    to maintain approximate class balance across splits.")


def main():
    """Run the full dataset inspection."""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║        DarkShield AI — Dataset Inspection Report        ║")
    print("╚══════════════════════════════════════════════════════════╝")

    print(f"\nDataset path: {DATASET_PATH}")

    df = load_dataset()

    inspect_basic_info(df)
    inspect_missing_values(df)
    inspect_labels(df)
    inspect_categories(df)
    inspect_duplicates(df)
    inspect_page_ids(df)
    inspect_text_statistics(df)
    inspect_sample_examples(df)
    inspect_splitting_recommendation(df)

    print_separator("INSPECTION COMPLETE")
    print("  Dataset inspection finished successfully.")
    print("  Use this report to guide preprocessing and model training.")
    print()


if __name__ == "__main__":
    main()
