"""
DarkShield AI - Website-Wide Deception Analysis & Summary Aggregator
=====================================================================

Aggregates page-by-page audits into a comprehensive, transparent website-wide summary.

Principles:
1. Clear Distinction:
   - Page Risk Score = Assessed deception level of a specific rendered page DOM.
   - Website Risk Summary = Engineering indicator synthesizing prevalence, peak severity,
     and category breadth across the sampled pages actually inspected.
2. No False Safety Verdicts:
   - A score of 0 or zero findings across sampled pages does NOT claim the entire website
     is completely safe. The sampled coverage limitation is explicitly recorded.
3. Transparent Aggregation:
   - Accounts for incomplete coverage and blocked pages.
   - Deduplicates findings across multi-page occurrences without double-counting.
"""

from typing import List, Dict, Any, Optional


def build_website_scan_summary(
    base_url: str,
    scan_id: str,
    pages_scanned: List[Dict[str, Any]],
    total_discovered: int,
    scan_status: str = "completed",
    duration_seconds: float = 0.0,
    limit_reached: bool = False,
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Computes statistical aggregation, unique findings rollup, risk distribution,
    and website-level engineering risk indicator across scanned pages.
    """
    config = config or {}
    total_scanned = len(pages_scanned)

    # 1. Page status tallies
    successful_pages = [p for p in pages_scanned if p.get("status") in ("complete", "completed") and not p.get("access_blocked")]
    blocked_pages = [p for p in pages_scanned if p.get("access_blocked") or p.get("status") == "blocked"]
    partial_pages = [p for p in pages_scanned if p.get("status") == "partial" or p.get("capture_quality") == "partial"]
    timed_out_pages = [p for p in pages_scanned if p.get("status") == "timed_out"]
    failed_pages = [p for p in pages_scanned if p.get("status") == "failed"]

    clean_pages = [p for p in successful_pages if (p.get("risk_score") == 0 or p.get("findings_count", 0) == 0)]
    pages_with_patterns = [p for p in successful_pages if (p.get("risk_score") or 0) > 0 and p.get("findings_count", 0) > 0]

    coverage_pct = round((total_scanned / max(1, total_discovered)) * 100, 1)
    pages_unassessed = max(0, total_discovered - total_scanned)

    # 2. Risk distribution across scanned pages
    risk_distribution = {
        "none": len(clean_pages),
        "low": sum(1 for p in successful_pages if 1 <= (p.get("risk_score") or 0) < 30),
        "medium": sum(1 for p in successful_pages if 30 <= (p.get("risk_score") or 0) < 60),
        "high": sum(1 for p in successful_pages if 60 <= (p.get("risk_score") or 0) < 80),
        "very_high": sum(1 for p in successful_pages if (p.get("risk_score") or 0) >= 80),
        "withheld": len(blocked_pages) + len(partial_pages) + len(timed_out_pages) + len(failed_pages)
    }

    # 3. Deduplicate findings across all pages
    # Key: pattern::evidence_summary
    unique_findings_map = {}
    category_counts = {}
    severity_counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0, "Info": 0}

    for p in pages_scanned:
        page_url = p.get("url", "")
        for f in p.get("findings", []):
            pat = f.get("pattern", "Unknown Pattern")
            ev_list = f.get("evidence", [])
            ev_summary = ""
            if isinstance(ev_list, list) and ev_list:
                ev_summary = str(ev_list[0])[:80].strip()
            elif isinstance(ev_list, str):
                ev_summary = ev_list[:80].strip()

            dedupe_key = f"{pat.lower()}::{ev_summary.lower()}"

            if dedupe_key not in unique_findings_map:
                finding_copy = dict(f)
                finding_copy["occurrences"] = [{"url": page_url, "title": p.get("title", "")}]
                finding_copy["occurrence_count"] = 1
                unique_findings_map[dedupe_key] = finding_copy

                # Tally category & severity
                category_counts[pat] = category_counts.get(pat, 0) + 1
                sev = f.get("severity", "Medium")
                if sev in severity_counts:
                    severity_counts[sev] += 1
                else:
                    severity_counts["Medium"] += 1
            else:
                # Add occurrence without duplicating the finding
                occ = unique_findings_map[dedupe_key]["occurrences"]
                if not any(o.get("url") == page_url for o in occ):
                    occ.append({"url": page_url, "title": p.get("title", "")})
                    unique_findings_map[dedupe_key]["occurrence_count"] = len(occ)

    unique_findings = list(unique_findings_map.values())

    # 4. Highest-risk pages
    pages_with_scores = [p for p in successful_pages if p.get("risk_score") is not None]
    highest_risk_pages = sorted(pages_with_scores, key=lambda x: x.get("risk_score", 0), reverse=True)[:10]

    # 5. Website-Wide Risk Indicator (Engineering Heuristic)
    # Blend: Peak Page Score (50%) + Avg Page Score (30%) + Category Diversity (20%)
    unsuccessful_count = len(blocked_pages) + len(timed_out_pages) + len(failed_pages)
    if len(successful_pages) == 0:
        website_risk_score = None
        website_risk_level = "Insufficient Data"
        methodology_note = (
            f"Insufficient data: None of the {total_scanned} scanned page(s) could be successfully analyzed "
            f"({len(blocked_pages)} blocked, {len(timed_out_pages)} timed out, {len(failed_pages)} failed). "
            "A deceptive design risk score cannot be determined."
        )
    elif not unique_findings and unsuccessful_count > 0 and len(successful_pages) < 2:
        website_risk_score = None
        website_risk_level = "Insufficient Data"
        methodology_note = (
            f"Insufficient data: Only {len(successful_pages)} page could be inspected while {unsuccessful_count} page(s) "
            f"failed, timed out, or blocked access ({coverage_pct}% coverage). "
            "A representative website-wide risk score cannot be certified from this limited sample."
        )
    elif not unique_findings:
        website_risk_score = 0
        website_risk_level = "None"
        methodology_note = (
            f"No deceptive design patterns were detected across the {len(successful_pages)} successfully "
            f"inspected sample page(s) ({coverage_pct}% of {total_discovered} discovered pages). "
            "This assessment represents a sampled research audit and does not guarantee that uninspected pages are free of dark patterns."
        )
    else:
        scores_list = [p.get("risk_score", 0) for p in pages_with_scores]
        max_score = max(scores_list) if scores_list else 0
        avg_score = (sum(scores_list) / len(scores_list)) if scores_list else 0
        cat_count = len(category_counts)
        cat_score = min(100.0, cat_count * 20.0)

        raw_index = 0.50 * max_score + 0.30 * avg_score + 0.20 * cat_score
        website_risk_score = int(min(100, max(0, round(raw_index))))

        if website_risk_score == 0 and not unique_findings:
            website_risk_level = "None"
        elif website_risk_score < 30:
            website_risk_level = "Low"
        elif website_risk_score < 60:
            website_risk_level = "Medium"
        elif website_risk_score < 80:
            website_risk_level = "High"
        else:
            website_risk_level = "Very High"

        methodology_note = (
            f"Website-wide deceptive design risk is an engineering indicator derived from "
            f"{len(successful_pages)} inspected page(s) ({coverage_pct}% coverage): "
            f"50% Peak Page Risk ({max_score}) + 30% Average Page Risk ({avg_score:.1f}) + "
            f"20% Category Diversity ({cat_score:.1f} from {cat_count} categories) = "
            f"{website_risk_score}/100 ({website_risk_level} Risk). Evaluated {len(unique_findings)} unique pattern instance(s)."
        )

    target_5s_achieved = bool(duration_seconds <= 5.00)
    target_10s_achieved = bool(duration_seconds <= 10.00)
    perf_status_5s = "ACHIEVED" if target_5s_achieved else "EXCEEDED"
    methodology_note += f" [5-Second Target: {perf_status_5s} ({duration_seconds:.2f}s elapsed).]"

    if pages_unassessed > 0:
        methodology_note += f" [Coverage Limitation: {pages_unassessed} discovered page(s) were NOT assessed and cannot be assumed safe.]"

    incomplete_within_target = bool(not target_5s_achieved and (total_scanned < total_discovered or limit_reached))
    if incomplete_within_target:
        methodology_note += " [Incomplete Coverage Within 5s Target: Crawl exceeded 5-second target before auditing all discovered pages. Unscanned pages were NOT assessed and cannot be assumed clean.]"
    elif limit_reached:
        methodology_note += f" [Note: Crawl stopped at configured limit of {config.get('max_pages', 100)} pages with additional discovered pages remaining unscanned.]"

    is_partial_scan = bool(
        total_scanned < total_discovered
        or scan_status in ("cancelled", "incomplete")
        or len(timed_out_pages) > 0
        or len(failed_pages) > 0
        or len(blocked_pages) > 0
    )

    return {
        "scan_id": scan_id,
        "base_url": base_url,
        "scan_status": scan_status,
        "scan_mode": "whole_website",
        "duration_seconds": round(duration_seconds, 2),
        "target_seconds": 5.0,
        "target_5s_achieved": target_5s_achieved,
        "target_10s_achieved": target_10s_achieved,
        "incomplete_within_target": incomplete_within_target,
        "is_partial_scan": is_partial_scan,
        "total_pages_discovered": total_discovered,
        "pages_scanned": total_scanned,
        "pages_successful": len(successful_pages),
        "pages_blocked": len(blocked_pages),
        "pages_partial": len(partial_pages),
        "pages_timed_out": len(timed_out_pages),
        "pages_failed": len(failed_pages),
        "pages_clean": len(clean_pages),
        "pages_with_dark_patterns": len(pages_with_patterns),
        "coverage_percentage": coverage_pct,
        "pages_unassessed": pages_unassessed,
        "limit_reached": limit_reached,
        "website_risk_score": website_risk_score,
        "website_risk_level": website_risk_level,
        "total_unique_findings": len(unique_findings),
        "total_finding_occurrences": sum(f.get("occurrence_count", 1) for f in unique_findings),
        "categories_detected": list(category_counts.keys()),
        "category_counts": category_counts,
        "severity_counts": severity_counts,
        "risk_distribution": risk_distribution,
        "highest_risk_pages": [
            {
                "url": p.get("url"),
                "title": p.get("title"),
                "risk_score": p.get("risk_score"),
                "risk_level": p.get("risk_level"),
                "findings_count": p.get("findings_count", 0),
                "depth": p.get("depth", 0),
                "top_patterns": [f.get("pattern") for f in p.get("findings", [])[:3]]
            }
            for p in highest_risk_pages
        ],
        "unique_findings": unique_findings,
        "methodology": methodology_note,
        "config": {
            "max_pages": config.get("max_pages", 20),
            "max_depth": config.get("max_depth", 2),
            "concurrency": config.get("concurrency", 3),
            "allow_subdomains": config.get("allow_subdomains", False)
        }
    }
