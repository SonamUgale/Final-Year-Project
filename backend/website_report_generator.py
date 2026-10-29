"""
DarkShield AI - Whole Website Executive PDF Audit Report Generator
===================================================================

Generates a publication-ready PDF report summarizing a whole-website crawl,
including multi-page deception statistics, engineering risk indicators,
page risk distribution, highest-risk pages, and category-grouped findings.
"""

import os
import io
from datetime import datetime, timezone
from typing import Dict, Any, List

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from backend.website_history import get_snapshot_path

# Brand colors matching DarkShield AI
PRIMARY_COLOR = colors.HexColor("#0f172a")      # Slate 900
BRAND_BLUE = colors.HexColor("#3b82f6")         # Blue 500
BRAND_PURPLE = colors.HexColor("#8b5cf6")       # Purple 500
SEV_CRITICAL = colors.HexColor("#ef4444")       # Red 500
SEV_HIGH = colors.HexColor("#f97316")           # Orange 500
SEV_MEDIUM = colors.HexColor("#eab308")         # Yellow 500
SEV_LOW = colors.HexColor("#10b981")            # Green 500
BG_LIGHT = colors.HexColor("#f8fafc")           # Slate 50
TEXT_DARK = colors.HexColor("#1e293b")          # Slate 800
TEXT_MUTED = colors.HexColor("#64748b")         # Slate 500
BORDER_COLOR = colors.HexColor("#e2e8f0")       # Slate 200
CALLOUT_BG = colors.HexColor("#f1f5f9")         # Slate 100


def get_risk_badge_color(level: str):
    lvl = (level or "").lower()
    if lvl in ("very high", "critical"):
        return SEV_CRITICAL
    elif lvl == "high":
        return SEV_HIGH
    elif lvl == "medium":
        return SEV_MEDIUM
    elif lvl in ("low", "none"):
        return SEV_LOW
    return TEXT_MUTED


def generate_website_pdf_report(website_scan_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a comprehensive PDF report from a whole website scan record.
    Accepts either the combined record {'summary': ..., 'pages': ...} or direct summary dictionary.
    """
    summary = website_scan_data.get("summary", website_scan_data)
    pages = website_scan_data.get("pages", [])

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=PRIMARY_COLOR,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=TEXT_MUTED,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
    )

    card_title_style = ParagraphStyle(
        "CardTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=TEXT_DARK,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=TEXT_DARK,
    )

    body_muted = ParagraphStyle(
        "BodyMuted",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=TEXT_MUTED,
    )

    callout_style = ParagraphStyle(
        "CalloutText",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=TEXT_DARK,
    )

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    story = []

    # Metadata extraction
    base_url = summary.get("base_url", "N/A")
    scan_id = summary.get("scan_id", "N/A")
    timestamp_raw = summary.get("timestamp", datetime.now(timezone.utc).isoformat())
    try:
        dt = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        date_str = dt.strftime("%B %d, %Y at %H:%M:%S UTC")
    except Exception:
        date_str = str(timestamp_raw)

    risk_score = summary.get("website_risk_score", 0)
    risk_level = summary.get("website_risk_level", "None")
    total_discovered = summary.get("total_pages_discovered", 0)
    pages_scanned = summary.get("pages_scanned", len(pages))
    pages_successful = summary.get("pages_successful", 0)
    pages_blocked = summary.get("pages_blocked", 0)
    pages_clean = summary.get("pages_clean", 0)
    pages_with_dp = summary.get("pages_with_dark_patterns", 0)
    coverage_pct = summary.get("coverage_percentage", 0.0)
    duration = summary.get("duration_seconds", 0.0)
    unique_findings = summary.get("unique_findings", [])
    highest_risk_pages = summary.get("highest_risk_pages", [])
    risk_dist = summary.get("risk_distribution", {})
    cfg = summary.get("config", {})

    # 1. HEADER & BRANDING
    header_table = Table(
        [
            [
                Paragraph("<b>DarkShield AI</b>", title_style),
                Paragraph(f"<b>Whole Website Audit</b><br/>Scan ID: {scan_id}", ParagraphStyle("RightHeader", parent=subtitle_style, alignment=2)),
            ],
            [
                Paragraph("Website-Wide Deceptive Design & Dark Pattern Audit", subtitle_style),
                Paragraph(f"Generated: {date_str}", ParagraphStyle("RightDate", parent=subtitle_style, alignment=2)),
            ],
        ],
        colWidths=[350, 190],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_BLUE, spaceAfter=10))

    # 2. TARGET CONFIGURATION & SCOPE
    meta_data = [
        [
            Paragraph("<b>Target Base URL:</b>", body_style),
            Paragraph(f"<font color='#2563eb'>{base_url}</font>", body_style),
            Paragraph("<b>Scan Status:</b>", body_style),
            Paragraph(f"<b>{summary.get('scan_status', 'completed').upper()}</b>", body_style),
        ],
        [
            Paragraph("<b>Max Depth:</b>", body_style),
            Paragraph(str(cfg.get("max_depth", 2)), body_style),
            Paragraph("<b>Max Pages Cap:</b>", body_style),
            Paragraph(str(cfg.get("max_pages", 20)), body_style),
        ],
        [
            Paragraph("<b>Pages Discovered:</b>", body_style),
            Paragraph(str(total_discovered), body_style),
            Paragraph("<b>Crawl Duration:</b>", body_style),
            Paragraph(f"{duration:.1f}s", body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[100, 170, 110, 160])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # 3. EXECUTIVE SUMMARY CARDS
    badge_bg = get_risk_badge_color(risk_level)
    risk_display = f"{risk_score}/100" if risk_score is not None else "Withheld"

    summary_cards_data = [
        [
            Paragraph("<b>Website Risk Indicator</b>", card_title_style),
            Paragraph("<b>Crawl Coverage</b>", card_title_style),
            Paragraph("<b>Deceptive Findings</b>", card_title_style),
            Paragraph("<b>Page Tally</b>", card_title_style),
        ],
        [
            Paragraph(
                f"<font size='16' color='{badge_bg.hexval()}'><b>{risk_display}</b></font><br/>"
                f"<font size='8' color='{badge_bg.hexval()}'><b>{risk_level} Risk</b></font>",
                body_style
            ),
            Paragraph(
                f"<font size='14' color='#0f172a'><b>{coverage_pct}%</b></font><br/>"
                f"<font size='8' color='#64748b'>{pages_scanned} of {total_discovered} pages</font>",
                body_style
            ),
            Paragraph(
                f"<font size='14' color='#ef4444'><b>{len(unique_findings)}</b></font> unique<br/>"
                f"<font size='8' color='#64748b'>{summary.get('total_finding_occurrences', len(unique_findings))} occurrences</font>",
                body_style
            ),
            Paragraph(
                f"<font size='9'>Clean: <b>{pages_clean}</b> | Patterns: <b>{pages_with_dp}</b><br/>"
                f"Blocked: <b>{pages_blocked}</b> | Failed: <b>{summary.get('pages_failed', 0)}</b></font>",
                body_style
            ),
        ]
    ]
    summary_table = Table(summary_cards_data, colWidths=[135, 135, 135, 135])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 1), (-1, 1), "CENTER"),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))

    # 4. SAMPLING & SCOPE LIMITATION NOTICE
    methodology_text = summary.get("methodology") or (
        f"Sampling Disclosure: DarkShield AI performed a safe, bounded BFS inspection across "
        f"{pages_successful} accessible page(s). A clean score on sampled pages does NOT guarantee that "
        "uninspected pages, dynamic user journeys, or personalized states are free of deceptive design patterns."
    )
    callout_data = [
        [
            Paragraph(f"<b>Notice on Scope & Methodology:</b> {methodology_text}", callout_style)
        ]
    ]
    callout_table = Table(callout_data, colWidths=[540])
    callout_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CALLOUT_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(callout_table)
    story.append(Spacer(1, 12))

    # 5. RISK LEVEL DISTRIBUTION TABLE
    story.append(Paragraph("<b>Page Risk Distribution</b>", section_heading))
    dist_rows = [
        [
            Paragraph("<b>Risk Tier</b>", card_title_style),
            Paragraph("<b>Score Range</b>", card_title_style),
            Paragraph("<b>Inspected Pages</b>", card_title_style),
            Paragraph("<b>Percentage</b>", card_title_style),
        ],
        [
            Paragraph("<font color='#10b981'><b>None / Clean</b></font>", body_style),
            Paragraph("0 / 100", body_style),
            Paragraph(str(risk_dist.get("none", 0)), body_style),
            Paragraph(f"{(risk_dist.get('none', 0) / max(1, pages_scanned) * 100):.1f}%", body_style),
        ],
        [
            Paragraph("<font color='#10b981'><b>Low Risk</b></font>", body_style),
            Paragraph("1 – 29", body_style),
            Paragraph(str(risk_dist.get("low", 0)), body_style),
            Paragraph(f"{(risk_dist.get('low', 0) / max(1, pages_scanned) * 100):.1f}%", body_style),
        ],
        [
            Paragraph("<font color='#eab308'><b>Medium Risk</b></font>", body_style),
            Paragraph("30 – 59", body_style),
            Paragraph(str(risk_dist.get("medium", 0)), body_style),
            Paragraph(f"{(risk_dist.get('medium', 0) / max(1, pages_scanned) * 100):.1f}%", body_style),
        ],
        [
            Paragraph("<font color='#f97316'><b>High Risk</b></font>", body_style),
            Paragraph("60 – 79", body_style),
            Paragraph(str(risk_dist.get("high", 0)), body_style),
            Paragraph(f"{(risk_dist.get('high', 0) / max(1, pages_scanned) * 100):.1f}%", body_style),
        ],
        [
            Paragraph("<font color='#ef4444'><b>Very High Risk</b></font>", body_style),
            Paragraph("80 – 100", body_style),
            Paragraph(str(risk_dist.get("very_high", 0)), body_style),
            Paragraph(f"{(risk_dist.get('very_high', 0) / max(1, pages_scanned) * 100):.1f}%", body_style),
        ],
        [
            Paragraph("<font color='#64748b'><b>Withheld (Blocked/Incomplete)</b></font>", body_style),
            Paragraph("N/A", body_style),
            Paragraph(str(risk_dist.get("withheld", 0)), body_style),
            Paragraph(f"{(risk_dist.get('withheld', 0) / max(1, pages_scanned) * 100):.1f}%", body_style),
        ],
    ]
    dist_table = Table(dist_rows, colWidths=[160, 110, 130, 140])
    dist_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(dist_table)
    story.append(Spacer(1, 14))

    # 6. TOP DECEPTIVE PAGES TABLE
    story.append(Paragraph("<b>Top Deceptive Pages Identified</b>", section_heading))
    if highest_risk_pages and any((p.get("risk_score") or 0) > 0 for p in highest_risk_pages):
        page_rows = [
            [
                Paragraph("<b>Rank</b>", card_title_style),
                Paragraph("<b>Page URL / Title</b>", card_title_style),
                Paragraph("<b>Depth</b>", card_title_style),
                Paragraph("<b>Score</b>", card_title_style),
                Paragraph("<b>Findings</b>", card_title_style),
                Paragraph("<b>Top Detected Patterns</b>", card_title_style),
            ]
        ]
        rank = 1
        for hrp in highest_risk_pages:
            score = hrp.get("risk_score")
            if score is None or score == 0:
                continue
            sc_color = get_risk_badge_color(hrp.get("risk_level", "None")).hexval()
            p_url = hrp.get("url", "")
            p_title = hrp.get("title", "Untitled")
            patterns_str = ", ".join(hrp.get("top_patterns", [])) or "—"

            page_rows.append([
                Paragraph(f"#{rank}", body_style),
                Paragraph(f"<b>{p_title[:45]}</b><br/><font color='#64748b'>{p_url[:55]}</font>", body_style),
                Paragraph(str(hrp.get("depth", 0)), body_style),
                Paragraph(f"<font color='{sc_color}'><b>{score}</b></font>", body_style),
                Paragraph(str(hrp.get("findings_count", 0)), body_style),
                Paragraph(patterns_str[:60], body_muted),
            ])
            rank += 1

        top_pages_table = Table(page_rows, colWidths=[35, 205, 45, 45, 55, 155])
        top_pages_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(KeepTogether(top_pages_table))
    else:
        story.append(Paragraph("<i>No deceptive design patterns detected on any inspected pages.</i>", body_style))

    story.append(Spacer(1, 14))

    # 7. UNIQUE DECEPTIVE PATTERNS GROUPED BY CATEGORY
    story.append(Paragraph(f"<b>Unique Pattern Findings ({len(unique_findings)})</b>", section_heading))
    if unique_findings:
        finding_rows = [
            [
                Paragraph("<b>Pattern Category</b>", card_title_style),
                Paragraph("<b>Severity</b>", card_title_style),
                Paragraph("<b>Occurrences</b>", card_title_style),
                Paragraph("<b>Evidence & Affected Pages</b>", card_title_style),
            ]
        ]
        for uf in unique_findings[:15]:  # Show top 15 unique findings
            pat = uf.get("pattern", "Unknown")
            sev = uf.get("severity", "Medium")
            sev_color = get_risk_badge_color(sev).hexval()
            occ_count = uf.get("occurrence_count", 1)

            ev = uf.get("evidence", [])
            ev_str = ""
            if isinstance(ev, list) and ev:
                ev_str = str(ev[0])
            elif isinstance(ev, str):
                ev_str = ev
            ev_snippet = ev_str[:120].strip()

            occ_list = uf.get("occurrences", [])
            urls_snippet = ", ".join([o.get("url", "").split("//")[-1][:30] for o in occ_list[:3]])
            if len(occ_list) > 3:
                urls_snippet += f" (+{len(occ_list) - 3} more)"

            content_p = (
                f"<b>Evidence:</b> <i>\"{ev_snippet}\"</i><br/>"
                f"<font color='#64748b'><b>Locations:</b> {urls_snippet}</font>"
            )

            finding_rows.append([
                Paragraph(f"<b>{pat}</b>", body_style),
                Paragraph(f"<font color='{sev_color}'><b>{sev}</b></font>", body_style),
                Paragraph(str(occ_count), body_style),
                Paragraph(content_p, body_style),
            ])

        findings_table = Table(finding_rows, colWidths=[120, 65, 65, 290])
        findings_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(findings_table))
    else:
        story.append(Paragraph("<i>No pattern instances recorded.</i>", body_style))

    story.append(Spacer(1, 14))

    # 8. BLOCKED / INACCESSIBLE PAGES (IF ANY)
    blocked_list = [p for p in pages if p.get("access_blocked") or p.get("status") == "blocked"]
    if blocked_list:
        story.append(Paragraph(f"<b>Restricted / Blocked Pages ({len(blocked_list)})</b>", section_heading))
        blocked_rows = [
            [
                Paragraph("<b>URL</b>", card_title_style),
                Paragraph("<b>Block Provider / Defense</b>", card_title_style),
                Paragraph("<b>Status</b>", card_title_style),
            ]
        ]
        for bp in blocked_list[:10]:
            provider = bp.get("block_provider") or "WAF / Anti-Bot Protection"
            blocked_rows.append([
                Paragraph(bp.get("url", "")[:60], body_style),
                Paragraph(provider, body_muted),
                Paragraph("<font color='#ef4444'><b>Access Denied (Score Withheld)</b></font>", body_muted),
            ])
        blocked_table = Table(blocked_rows, colWidths=[240, 160, 140])
        blocked_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(blocked_table))
        story.append(Spacer(1, 14))

    # 8B. PAGE-BY-PAGE AUDIT & SNAPSHOT EVIDENCE
    if pages:
        story.append(Paragraph(f"<b>Page-by-Page Audit & Snapshot Evidence ({len(pages)} Pages)</b>", section_heading))
        scan_id = summary.get("scan_id", "")

        for p in pages[:20]:
            p_id = p.get("page_id", "")
            p_title = p.get("title") or "Untitled Webpage"
            p_url = p.get("url", "")
            p_score = p.get("risk_score")
            p_level = p.get("risk_level", "None")
            p_blocked = p.get("access_blocked") or p.get("status") == "blocked"
            p_findings = p.get("findings", [])

            # Check for snapshot file
            snap_img = None
            if scan_id and p_id:
                snap_path = get_snapshot_path(scan_id, p_id)
                if snap_path and os.path.exists(snap_path):
                    try:
                        from PIL import Image as PILImage
                        with PILImage.open(snap_path) as im:
                            im.verify()
                        snap_img = Image(snap_path, width=160, height=100)
                    except Exception:
                        snap_img = None

            # Left column: snapshot image or placeholder
            if snap_img:
                left_cell = snap_img
            else:
                left_cell = Paragraph(
                    f"<font color='#64748b'><b>Snapshot:</b><br/>"
                    f"{'⚠️ Blocked (WAF)' if p_blocked else 'Rendered DOM'}<br/>"
                    f"Links: {p.get('dom_stats', {}).get('links', 0)} | "
                    f"Buttons: {p.get('dom_stats', {}).get('buttons', 0)}<br/>"
                    f"Text: {p.get('dom_stats', {}).get('text_chars', 0)} chars</font>",
                    body_muted
                )

            # Right column: Page details and findings
            sc_color = get_risk_badge_color(p_level).hexval() if not p_blocked else "#ef4444"
            status_text = (
                f"<font color='{sc_color}'><b>Score: {p_score}/100 ({p_level})</b></font>"
                if not p_blocked and p_score is not None
                else "<font color='#ef4444'><b>Access Denied (Withheld)</b></font>"
            )

            header_text = (
                f"<b>{p_id.upper()}: {p_title[:45]}</b> — {status_text}<br/>"
                f"<font color='#64748b'>{p_url[:65]}</font><br/>"
            )

            if p_blocked:
                body_content = (
                    f"{header_text}"
                    f"<font color='#ef4444'>⚠️ <b>Scan Incomplete:</b> Access restricted by {p.get('block_provider') or 'WAF/Anti-Bot'}. "
                    f"Deception score was withheld to avoid a false clean assessment.</font>"
                )
            elif not p_findings:
                body_content = (
                    f"{header_text}"
                    f"<font color='#10b981'><b>✓ Clean Page:</b> No dark patterns detected on this captured page.</font>"
                )
            else:
                findings_lines = [header_text, f"<b>Findings ({len(p_findings)}):</b>"]
                for f in p_findings[:3]:
                    f_pat = f.get("pattern", "Deceptive Pattern")
                    f_sev = f.get("severity", "Medium")
                    f_sev_col = get_risk_badge_color(f_sev).hexval()
                    f_conf = round((f.get("confidence") or 0.85) * 100, 1)
                    f_type = f.get("evidence_type", "text")
                    f_text = f.get("exact_text") or (f.get("evidence")[0] if isinstance(f.get("evidence"), list) and f.get("evidence") else "")
                    f_text_str = str(f_text)[:80].strip()

                    findings_lines.append(
                        f"• <b>{f_pat}</b> (<font color='{f_sev_col}'>{f_sev}</font>, {f_conf}%) "
                        f"[{f_type}]<br/>"
                        f"&nbsp;&nbsp;<i>\"{f_text_str}\"</i>"
                    )
                if len(p_findings) > 3:
                    findings_lines.append(f"<font color='#64748b'><i>+{len(p_findings) - 3} more pattern(s)...</i></font>")
                body_content = "<br/>".join(findings_lines)

            page_box_table = Table(
                [[left_cell, Paragraph(body_content, body_style)]],
                colWidths=[170, 370]
            )
            page_box_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(KeepTogether([page_box_table, Spacer(1, 8)]))

        story.append(Spacer(1, 10))

    # 9. FOOTER & METHODOLOGY NOTE
    footer_text = Paragraph(
        "<b>DarkShield AI Methodology:</b> Whole website deceptive design auditing utilizes an autonomous "
        "BFS Playwright crawler combined with Calibrated Linear SVM V2 (96.89% test accuracy, 0.9691 F1-score) "
        "and rule-based cognitive pattern grounding. Website Deception Risk is an engineering synthesis of peak severity, "
        "mean page risk, and pattern category breadth across inspected pages.",
        body_muted,
    )
    story.append(footer_text)

    # Build document
    doc.build(story)
    buffer.seek(0)
    return buffer
