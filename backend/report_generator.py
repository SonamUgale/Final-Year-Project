"""
DarkShield AI - Executive PDF Audit Report Generator
====================================================

Generates a formatted, publication-ready PDF report of a website's
security audit and dark pattern deception analysis using ReportLab.
"""

import os
import io
import base64
import tempfile
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch


# Custom color palette matching DarkShield AI dark / professional theme
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


def get_severity_color(severity: str):
    s = (severity or "").lower()
    if s == "critical":
        return SEV_CRITICAL
    elif s == "high":
        return SEV_HIGH
    elif s == "medium":
        return SEV_MEDIUM
    elif s in ["low", "none"]:
        return SEV_LOW
    return TEXT_MUTED


def generate_pdf_report(scan_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a PDF report from scan_data and returns an in-memory BytesIO buffer.
    """
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

    # Custom typography styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY_COLOR,
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=13,
        textColor=TEXT_MUTED,
    )

    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=PRIMARY_COLOR,
        spaceAfter=6,
    )

    card_title_style = ParagraphStyle(
        "CardTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=TEXT_DARK,
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
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

    badge_style = ParagraphStyle(
        "BadgeText",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=colors.white,
    )

    story = []

    # Extract scan data
    website = scan_data.get("website", {})
    security = scan_data.get("security_analysis", {})
    dark_patterns_data = scan_data.get("dark_pattern_analysis", {})
    ai_data = scan_data.get("ai_analysis", dark_patterns_data.get("ai_analysis", {}))

    url = website.get("url", "N/A")
    title = website.get("title", "Untitled")
    scan_id = scan_data.get("scan_id", "N/A")
    timestamp_raw = scan_data.get("timestamp", datetime.now(timezone.utc).isoformat())
    try:
        dt = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        date_str = dt.strftime("%B %d, %Y at %H:%M:%S UTC")
    except Exception:
        date_str = str(timestamp_raw)

    security_score = security.get("security_score", 100)
    security_risk = security.get("risk_level", "Low")
    dark_risk_score = dark_patterns_data.get("risk_score", 0)
    dark_risk_level = dark_patterns_data.get("risk_level", "None")
    patterns = dark_patterns_data.get("findings", [])
    security_findings = security.get("findings", [])
    cookie_data = website.get("cookie_consent", dark_patterns_data.get("cookie_consent", {}))
    screenshot_b64 = website.get("screenshot_b64")
    visual_data = dark_patterns_data.get("visual_analysis") or scan_data.get("visual_analysis") or {}

    # 1. HEADER & BRANDING
    header_table = Table(
        [
            [
                Paragraph("<b>DarkShield AI</b>", title_style),
                Paragraph(f"<b>Audit Report</b><br/>ID: {scan_id}", ParagraphStyle("RightHeader", parent=subtitle_style, alignment=2)),
            ],
            [
                Paragraph("AI-Powered Deceptive Design & Security Intelligence", subtitle_style),
                Paragraph(f"Generated: {date_str}", ParagraphStyle("RightDate", parent=subtitle_style, alignment=2)),
            ],
        ],
        colWidths=[360, 180],
    )
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_BLUE, spaceAfter=12))

    # 2. TARGET WEBSITE DETAILS
    scan_mode_raw = scan_data.get("scan_mode") or website.get("scan_mode") or "automatic"
    if scan_mode_raw == "browser_capture":
        scan_mode_label = "Browser Capture (Active Chrome Extension)"
    else:
        scan_mode_label = "Automated Crawler (Playwright)"

    model_label = "Calibrated SVM V2 + Rules"
    if visual_data.get("available"):
        model_label += " & Vision AI"
    else:
        model_label += " (Vision AI Offline)"

    capture_quality_raw = (
        scan_data.get("capture_quality")
        or website.get("capture_quality")
        or ("blocked" if scan_data.get("access_blocked") else ("partial" if scan_data.get("status") == "partial" else "complete"))
    )
    if capture_quality_raw == "complete":
        quality_display = "<font color='#10b981'><b>Complete (Verified DOM)</b></font>"
    elif capture_quality_raw == "partial":
        quality_display = "<font color='#d97706'><b>Partial (Score Withheld)</b></font>"
    else:
        quality_display = "<font color='#ef4444'><b>Blocked (Restricted)</b></font>"

    meta_data = [
        [
            Paragraph("<b>Target URL:</b>", body_style),
            Paragraph(f"<font color='#2563eb'>{url}</font>", body_style),
            Paragraph("<b>Page Title:</b>", body_style),
            Paragraph(title[:45] if title else "N/A", body_style),
        ],
        [
            Paragraph("<b>Scan Mode:</b>", body_style),
            Paragraph(f"<b>{scan_mode_label}</b>", body_style),
            Paragraph("<b>Quality:</b>", body_style),
            Paragraph(quality_display, body_style),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[70, 240, 65, 165])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Check for blocked access or scan failure
    is_blocked = (
        scan_data.get("access_blocked")
        or scan_data.get("status") == "blocked"
        or scan_data.get("scan_status") == "blocked"
        or dark_patterns_data.get("status") == "blocked"
        or dark_patterns_data.get("access_blocked")
        or website.get("access_blocked")
        or website.get("status") == "blocked"
    )

    if is_blocked:
        block_provider = (
            scan_data.get("block_provider")
            or dark_patterns_data.get("block_provider")
            or website.get("block_provider")
            or "Automated Access Barrier"
        )
        block_info = (
            scan_data.get("block_info")
            or dark_patterns_data.get("block_info")
            or website.get("block_info")
            or {}
        )
        block_reason = (
            scan_data.get("message")
            or block_info.get("reason")
            or "Automated scanning access was blocked by the target server."
        )

        story.append(Paragraph("<b>Audit Status: Access Blocked / Automated Crawl Restricted</b>", section_heading))

        blocked_table_data = [
            [
                Paragraph("<b>Parameter</b>", card_title_style),
                Paragraph("<b>Details</b>", card_title_style),
            ],
            [
                Paragraph("<b>Scan Status</b>", body_style),
                Paragraph("<font color='#ef4444'><b>BLOCKED</b> (Access Denied / Bot Challenge)</font>", body_style),
            ],
            [
                Paragraph("<b>Security / WAF Provider</b>", body_style),
                Paragraph(f"<b>{block_provider}</b>", body_style),
            ],
            [
                Paragraph("<b>Block Reason</b>", body_style),
                Paragraph(str(block_reason), body_style),
            ],
            [
                Paragraph("<b>Deceptive Risk Score</b>", body_style),
                Paragraph("<b>N/A (Analysis Withheld)</b><br/><font color='#64748b'>No dark pattern score was computed because target website content could not be accessed.</font>", body_style),
            ],
            [
                Paragraph("<b>Recommended Next Step</b>", body_style),
                Paragraph("Use <b>DarkShield Browser Capture Mode</b> to export the authenticated or human-rendered DOM and screenshot directly into DarkShield for unified SVM, Rule-Based, and Vision AI analysis.", body_style),
            ],
        ]

        blocked_table = Table(blocked_table_data, colWidths=[160, 380])
        blocked_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fff5f5")),
            ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#ef4444")),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(blocked_table)
        story.append(Spacer(1, 14))

        temp_img_path = None
        if screenshot_b64:
            try:
                img_bytes = base64.b64decode(screenshot_b64)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(img_bytes)
                    temp_img_path = tmp.name

                story.append(Paragraph("<b>Access Barrier Snapshot Evidence</b>", section_heading))
                story.append(Image(temp_img_path, width=540, height=180))
                story.append(Spacer(1, 12))
            except Exception:
                pass

        footer_text = Paragraph(
            "<b>DarkShield AI Integrity Policy:</b> To prevent false positives and fabricated clean scores, "
            "DarkShield AI withholds deceptive pattern scoring when access-denied or bot-mitigation challenge pages are detected. "
            "Please use Browser Capture Mode to evaluate this site's interactive elements.",
            body_muted,
        )
        story.append(footer_text)

        try:
            doc.build(story)
        finally:
            if temp_img_path and os.path.exists(temp_img_path):
                try:
                    os.remove(temp_img_path)
                except Exception:
                    pass

        buffer.seek(0)
        return buffer

    # 3. EXECUTIVE SCORES SUMMARY
    vision_brief = visual_data.get("status", "Offline Fallback").split("(")[0].strip()
    is_partial_report = (
        not is_blocked and (
            capture_quality_raw == "partial"
            or scan_data.get("status") == "partial"
            or dark_patterns_data.get("status") == "partial"
            or dark_risk_score is None
        )
    )

    if is_partial_report or dark_risk_score is None:
        dark_score_cell = Paragraph(
            "<font size='16' color='#d97706'><b>N/A</b></font><br/><b>Withheld</b> (Incomplete DOM)",
            body_style
        )
        dark_bg = colors.HexColor("#fffbeb")
    else:
        dark_score_cell = Paragraph(
            f"<font size='18'><b>{dark_risk_score}</b></font>/100<br/><b>{dark_risk_level} Risk</b> ({len(patterns)} patterns)",
            body_style
        )
        dark_bg = colors.HexColor("#faf5ff") if dark_risk_score > 0 else colors.HexColor("#f0fdf4")

    scores_data = [
        [
            Paragraph("<b>Security Posture</b>", card_title_style),
            Paragraph("<b>Deceptive UX Risk (Dark Patterns)</b>", card_title_style),
            Paragraph("<b>AI Multi-Modal Engine</b>", card_title_style),
        ],
        [
            Paragraph(f"<font size='18'><b>{security_score}</b></font>/100<br/><b>{security_risk} Risk</b> ({len(security_findings)} findings)", body_style),
            dark_score_cell,
            Paragraph(
                f"<b>Model:</b> Calibrated Linear SVM V2<br/>"
                f"<b>Accuracy:</b> {round(ai_data.get('test_accuracy', 0.9689)*100, 2)}%<br/>"
                f"<b>Rules:</b> 12 Pattern Heuristics<br/>"
                f"<b>Avg Conf:</b> {round(ai_data.get('average_confidence', 0.95)*100, 1)}%",
                body_style,
            ),
        ],
    ]
    scores_table = Table(scores_data, colWidths=[180, 180, 180])
    scores_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0fdf4") if (security_score or 0) >= 80 else colors.HexColor("#fff7ed")),
        ("BACKGROUND", (1, 0), (1, -1), dark_bg),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(scores_table)
    story.append(Spacer(1, 10))

    if is_partial_report:
        partial_table_data = [
            [
                Paragraph("<b>Audit Notice: Incomplete Page Capture — Deceptive Risk Score Withheld</b>", card_title_style),
            ],
            [
                Paragraph(
                    "Automated crawling retrieved incomplete page structure or content. "
                    "In adherence to DarkShield AI integrity principles, deceptive design risk scoring was withheld to avoid a false clean (0/100) verdict. "
                    "Please use <b>Browser Capture Mode</b> to export the authenticated or human-rendered DOM directly from Chrome.",
                    body_style
                ),
            ],
        ]
        partial_table = Table(partial_table_data, colWidths=[540])
        partial_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fffbeb")),
            ("BOX", (0, 0), (-1, -1), 1.0, colors.HexColor("#f59e0b")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(partial_table)
        story.append(Spacer(1, 10))

    # 3b. 5-FACTOR DECEPTIVE RISK BREAKDOWN TABLE
    risk_breakdown = dark_patterns_data.get("risk_breakdown") or scan_data.get("combined_analysis", {}).get("risk_breakdown") or {}
    if risk_breakdown and any(risk_breakdown.values()):
        rb_sev = risk_breakdown.get("severity", 0.0)
        rb_conf = risk_breakdown.get("confidence", 0.0)
        rb_freq = risk_breakdown.get("frequency", 0.0)
        rb_imp = risk_breakdown.get("user_impact", 0.0)
        rb_bev = risk_breakdown.get("behavioral_evidence", 0.0)

        breakdown_data = [
            [
                Paragraph("<b>Factor</b>", card_title_style),
                Paragraph("<b>Weight</b>", card_title_style),
                Paragraph("<b>Factor Score</b>", card_title_style),
                Paragraph("<b>Evaluation Description</b>", card_title_style),
            ],
            [
                Paragraph("Severity", body_style),
                Paragraph("25%", body_style),
                Paragraph(f"<b>{rb_sev:.1f}</b>/100", body_style),
                Paragraph("Deception harm potential (blends peak & average severity)", body_muted),
            ],
            [
                Paragraph("Confidence", body_style),
                Paragraph("20%", body_style),
                Paragraph(f"<b>{rb_conf:.1f}</b>/100", body_style),
                Paragraph("Detection certainty across SVM, Rules, and Vision AI", body_muted),
            ],
            [
                Paragraph("Frequency", body_style),
                Paragraph("15%", body_style),
                Paragraph(f"<b>{rb_freq:.1f}</b>/100", body_style),
                Paragraph("Deduplicated density of manipulative elements on page", body_muted),
            ],
            [
                Paragraph("User Impact", body_style),
                Paragraph("25%", body_style),
                Paragraph(f"<b>{rb_imp:.1f}</b>/100", body_style),
                Paragraph("Potential to coerce user choices & degrade decision autonomy", body_muted),
            ],
            [
                Paragraph("Behavioral Evidence", body_style),
                Paragraph("15%", body_style),
                Paragraph(f"<b>{rb_bev:.1f}</b>/100", body_style),
                Paragraph("Observable defaults (pre-checked tracking, absent opt-out)", body_muted),
            ],
        ]
        breakdown_table = Table(breakdown_data, colWidths=[110, 55, 80, 295])
        breakdown_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(Paragraph("<b>Website-Level Deceptive Risk Breakdown</b>", section_heading))
        story.append(breakdown_table)
        story.append(Spacer(1, 12))

    # 4. WEBSITE VISUAL EVIDENCE (SCREENSHOT)
    temp_img_path = None
    if screenshot_b64:
        try:
            img_bytes = base64.b64decode(screenshot_b64)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(img_bytes)
                temp_img_path = tmp.name

            story.append(Paragraph("<b>Website Visual Snapshot</b>", section_heading))
            # Fit thumbnail into 540 width, max 180 height
            story.append(Image(temp_img_path, width=540, height=180))
            story.append(Spacer(1, 12))
        except Exception as img_err:
            pass

    # 4b. VISUAL AI & LAYOUT ANALYSIS
    visual_patterns = visual_data.get("patterns", [])
    if visual_data.get("available") or visual_patterns:
        story.append(Paragraph("<b>Visual Layout & Screenshot AI Analysis</b>", section_heading))
        vis_risk = visual_data.get("visual_risk_score", 0)
        vis_level = visual_data.get("visual_risk_level", "None")
        vis_status = visual_data.get("status", "Active")
        vis_summary = (
            f"<b>Status:</b> {vis_status} | "
            f"<b>Visual Risk:</b> {vis_risk}/100 ({vis_level}) | "
            f"<b>Visual Patterns:</b> {len(visual_patterns)}"
        )
        story.append(Paragraph(vis_summary, body_muted))
        story.append(Spacer(1, 6))

        if visual_patterns:
            vis_rows = [
                [
                    Paragraph("<b>Visual Deceptive Pattern</b>", card_title_style),
                    Paragraph("<b>Visual Evidence / Layout Details</b>", card_title_style),
                    Paragraph("<b>Recommendation</b>", card_title_style),
                ]
            ]
            for vp in visual_patterns:
                vis_rows.append([
                    Paragraph(f"<b>{vp.get('name', 'Pattern')}</b><br/><font color='#64748b'>Severity: {vp.get('severity', 'Medium')} | Conf: {int(float(vp.get('confidence', 0.85))*100)}%</font>", body_style),
                    Paragraph(f"{vp.get('visual_details') or vp.get('evidence') or 'Visual presentation anomaly'}", body_muted),
                    Paragraph(f"{vp.get('recommendation', 'Evaluate interface options with scrutiny.')}", body_muted),
                ])
            vis_table = Table(vis_rows, colWidths=[160, 210, 170])
            vis_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]))
            story.append(KeepTogether(vis_table))
            story.append(Spacer(1, 10))

    # 5. PRIVACY & COOKIE CONSENT ANALYSIS
    if cookie_data and cookie_data.get("banner_detected"):
        story.append(Paragraph("<b>Privacy & Cookie Consent Evaluation</b>", section_heading))
        cookie_rows = [
            [Paragraph("<b>Cookie Banner Detected</b>", body_style), Paragraph("Yes (Modal / Fixed Container Identified)", body_style)],
            [Paragraph("<b>'Accept All' Option</b>", body_style), Paragraph(cookie_data.get("accept_button") or "None directly visible", body_style)],
            [Paragraph("<b>'Reject All' Option</b>", body_style), Paragraph(cookie_data.get("reject_button") or "<font color='#ef4444'><b>Absent or Obscured</b></font>", body_style)],
            [Paragraph("<b>Preferences / Customization</b>", body_style), Paragraph(cookie_data.get("manage_button") or "None", body_style)],
        ]
        preselected = cookie_data.get("preselected_checkboxes", [])
        if preselected:
            labels = ", ".join([cb.get("label", "") for cb in preselected])
            cookie_rows.append([Paragraph("<b>Pre-selected Checkboxes</b>", body_style), Paragraph(f"<font color='#f97316'>{labels}</font>", body_style)])

        cookie_table = Table(cookie_rows, colWidths=[180, 360])
        cookie_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(cookie_table)
        story.append(Spacer(1, 14))

    # 6. DARK PATTERN FINDINGS
    story.append(Paragraph(f"<b>Detected Deceptive Design Patterns ({len(patterns)})</b>", section_heading))

    if patterns:
        for idx, p in enumerate(patterns, 1):
            pat_name = p.get("pattern", "Unknown Pattern")
            severity = p.get("severity", "Medium")
            method = p.get("detection_method", "AI Model")
            conf = p.get("confidence", 0.0)
            element = p.get("element_type", "DOM")
            evidence = p.get("evidence", [])
            explanation = p.get("explanation", p.get("description", ""))
            why_it_matters = p.get("why_it_matters", "")
            recommendation = p.get("recommendation", "")

            evidence_bullets = "<br/>".join([f"• &ldquo;<i>{ev}</i>&rdquo;" for ev in evidence[:3]]) if evidence else "None listed"

            card_content = [
                [
                    Paragraph(f"<b>#{idx}. {pat_name}</b>", card_title_style),
                    Paragraph(f"<b>{severity}</b> | {method} | Conf: {round(conf*100, 1)}% | Tag: {element}", ParagraphStyle("Sub", parent=body_muted, alignment=2)),
                ],
                [
                    Paragraph(f"<b>Grounded Evidence:</b><br/>{evidence_bullets}", body_style),
                    Paragraph(f"<b>AI Explanation:</b><br/>{explanation}<br/><br/><b>Recommendation:</b><br/>{recommendation}", body_style),
                ],
            ]
            pattern_box = Table(card_content, colWidths=[240, 300])
            pattern_box.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#faf5ff")),
                ("BOX", (0, 0), (-1, -1), 0.5, BRAND_PURPLE),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#e9d5ff")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]))
            story.append(KeepTogether(pattern_box))
            story.append(Spacer(1, 8))
    else:
        clean_note = Paragraph("<i>No deceptive dark patterns detected on this website.</i>", body_style)
        story.append(clean_note)

    story.append(Spacer(1, 10))

    # 7. SECURITY FINDINGS
    story.append(Paragraph(f"<b>Technical Security Findings ({len(security_findings)})</b>", section_heading))
    if security_findings:
        sec_rows = [
            [
                Paragraph("<b>Vulnerability / Configuration Issue</b>", card_title_style),
                Paragraph("<b>Severity</b>", card_title_style),
                Paragraph("<b>Description</b>", card_title_style),
            ]
        ]
        for sf in security_findings:
            sec_rows.append([
                Paragraph(sf.get("issue", "Issue"), body_style),
                Paragraph(f"<b>{sf.get('severity', 'Info')}</b>", body_style),
                Paragraph(sf.get("description", ""), body_muted),
            ])
        sec_table = Table(sec_rows, colWidths=[180, 80, 280])
        sec_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BG_LIGHT),
            ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(KeepTogether(sec_table))
    else:
        story.append(Paragraph("<i>No security vulnerabilities identified.</i>", body_style))

    story.append(Spacer(1, 16))

    # 8. FOOTER / METHODOLOGY
    ai_meta = scan_data.get("ai_analysis") or scan_data.get("dark_pattern_analysis", {}).get("ai_analysis", {})
    m_name = ai_meta.get("model_name", "Calibrated Linear SVM V2")
    m_ver = ai_meta.get("model_version", "v2").upper()
    m_acc = ai_meta.get("test_accuracy", 0.9689)
    m_f1 = ai_meta.get("f1_score", 0.9691)
    acc_str = f"{m_acc * 100:.2f}%"

    footer_text = Paragraph(
        f"<b>DarkShield AI Methodology:</b> Classification performed using {m_name} ({m_ver}, "
        f"{acc_str} test accuracy, {m_f1:.4f} F1-score) corroborated with contextual DOM heuristics and Playwright rendering. "
        "This audit is an automated research assessment.",
        body_muted,
    )
    story.append(footer_text)

    # Build PDF document
    try:
        doc.build(story)
    finally:
        if temp_img_path and os.path.exists(temp_img_path):
            try:
                os.remove(temp_img_path)
            except Exception:
                pass

    buffer.seek(0)
    return buffer
