"""
DarkShield AI - Controlled Real-World & Test-Site Validation Procedure
======================================================================

Executes end-to-end scanning across reference pages:
1. Local Test Site (contains designed deceptive UX patterns)
2. Public Benchmark Pages (e.g., example.com, w3.org)

For each target, logs:
- Target URL
- Timestamp (UTC)
- Security Score & Risk Level
- Dark Pattern Risk Score & Risk Level
- Potential Dark Patterns Detected
- Calibrated Confidence & Evidence
- Detection Method (Hybrid, AI Model, Rule-Based)
- Evidence Snippets & Element Types
"""

import os
import sys
import json
from datetime import datetime, timezone

from backend.scraper.browser import scrape_website
from backend.analyzer import analyze_website


VALIDATION_TARGETS = [
    # 1. Local controlled test site (contains simulated dark patterns)
    f"file:///{os.path.abspath('test_site/index.html').replace(os.sep, '/')}",
    # 2. Public clean benchmark site
    "https://example.com"
]


def run_validation():
    print("============================================================")
    print("  DarkShield AI — Controlled Validation Procedure")
    print("============================================================")

    results = []

    for target in VALIDATION_TARGETS:
        print(f"\n[Scanning] {target}")
        start_time = datetime.now(timezone.utc).isoformat()

        try:
            scraped = scrape_website(target)
            analysis = analyze_website(scraped)

            dp_analysis = analysis.get("dark_pattern_analysis", {})
            findings = dp_analysis.get("findings", [])

            record = {
                "url": target,
                "timestamp": start_time,
                "security": {
                    "score": analysis.get("security_score"),
                    "risk_level": analysis.get("risk_level"),
                    "findings_count": analysis.get("total_findings", 0)
                },
                "dark_patterns": {
                    "risk_score": dp_analysis.get("risk_score", 0),
                    "risk_level": dp_analysis.get("risk_level", "None"),
                    "patterns_count": len(findings),
                    "detected_patterns": [
                        {
                            "pattern": f.get("pattern"),
                            "severity": f.get("severity"),
                            "confidence": f.get("confidence"),
                            "detection_method": f.get("detection_method"),
                            "element_type": f.get("element_type"),
                            "evidence": f.get("evidence"),
                            "potential_classification": f"Potential {f.get('pattern')} detected"
                        }
                        for f in findings
                    ]
                }
            }

            print(f"  ✓ Security Score: {record['security']['score']} ({record['security']['risk_level']})")
            print(f"  ✓ Dark Pattern Score: {record['dark_patterns']['risk_score']} ({record['dark_patterns']['risk_level']})")
            print(f"  ✓ Patterns Detected: {record['dark_patterns']['patterns_count']}")
            for p in record['dark_patterns']['detected_patterns']:
                print(f"     - [{p['detection_method']}] {p['pattern']} ({p['element_type']}, conf: {p['confidence']})")
                print(f"       Evidence: {p['evidence'][:2]}")

            results.append(record)

        except Exception as e:
            print(f"  ⚠ Scan failed for {target}: {e}")
            results.append({
                "url": target,
                "timestamp": start_time,
                "error": str(e)
            })

    # Save to disk
    out_path = os.path.join(os.path.dirname(__file__), "validation_results.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\n✓ Validation records written to: {out_path}")
    print("============================================================")
    print("  VALIDATION COMPLETED")
    print("============================================================")
    return results


if __name__ == "__main__":
    run_validation()
