"""
DarkShield AI - Master Retraining & Verification Orchestrator (Phase 2)
======================================================================

Orchestrates the complete Phase 2 end-to-end workflow:
1. Dataset Enrichment (institutional benign + minority dark patterns)
2. Leak-Free Preprocessing & Stratified Group Splitting (StratifiedGroupKFold on page_id)
3. 5-Fold Stratified Group Cross-Validation & Model Training (Balanced LinearSVC + Platt Calibration)
4. Model Artifact Serialization (versioned v2 and production artifacts)
5. Comprehensive Test Suite Execution (zero-leakage, institutional FP prevention, minority classes)
6. Multi-Site Real-World Validation (Local test site, example.com, kkwagh.edu.in)

Usage:
    python -m backend.ai.run_retraining
"""

import os
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from backend.ai.enrich_dataset import enrich_dataset
from backend.ai.preprocessing import run_pipeline as run_preprocessing
from backend.ai.train import train_and_evaluate


def execute_full_phase2_workflow(run_live_scrapes: bool = True):
    """Execute complete Phase 2 pipeline."""
    print("=" * 70)
    print("  DARKSHIELD AI — PHASE 2 MODEL RETRAINING & VALIDATION PIPELINE")
    print("=" * 70)

    # 1. Dataset Enrichment
    print("\n>>> [STEP 1/5] Executing Dataset Enrichment...")
    enriched_df = enrich_dataset()

    # 2. Preprocessing & Group Splitting
    print("\n>>> [STEP 2/5] Executing Leak-Free Preprocessing & Splitting...")
    run_preprocessing()

    # 3. Model Training & 5-Fold Cross-Validation
    print("\n>>> [STEP 3/5] Executing 5-Fold CV & Model Retraining...")
    report = train_and_evaluate()

    # 4. Run Test Suite
    print("\n>>> [STEP 4/5] Running System & Retraining Verification Tests...")
    loader = unittest.TestLoader()
    suite = loader.discover("backend/tests", pattern="test_all.py")
    runner = unittest.TextTestRunner(verbosity=2)
    test_res = runner.run(suite)

    if not test_res.wasSuccessful():
        print("\n⚠ Some unit tests encountered issues. Review details above.")
    else:
        print("\n✓ All unit tests passed successfully!")

    # 5. Real-World Multi-Site Scrapes (Optional / on-demand)
    if run_live_scrapes:
        print("\n>>> [STEP 5/5] Running Real-World Validation (Local, example.com, KKWIEER)...")
        try:
            from backend.tests.validate_real_world import run_validation
            run_validation()
        except Exception as e:
            print(f"⚠ Live scraping validation encountered: {e}")
            print("Note: Browser scraping can also be run independently via:")
            print("  python -m backend.tests.validate_real_world")

    print("\n" + "=" * 70)
    print("  PHASE 2 WORKFLOW EXECUTION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    execute_full_phase2_workflow(run_live_scrapes=True)
