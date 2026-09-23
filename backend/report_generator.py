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
    meta_data = [
        [
            Paragraph("<b>Target URL:</b>", body_style),
            Paragraph(f"<font color='#2563eb'>{url}</font>", body_style),
            Paragraph("<b>Page Title:</b>", body_style),
            Paragraph(title[:45] if title else "N/A", body_style),
        ]
    ]
    meta_table = Table(meta_data, colWidths=[70, 240, 65, 165])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BG_LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # 3. EXECUTIVE SCORES SUMMARY
    scores_data = [
        [
            Paragraph("<b>Security Posture</b>", card_title_style),
            Paragraph("<b>Deceptive UX Risk (Dark Patterns)</b>", card_title_style),
            Paragraph("<b>AI Hybrid Engine</b>", card_title_style),
        ],
        [
            Paragraph(f"<font size='18'><b>{security_score}</b></font>/100<br/><b>{security_risk} Risk</b> ({len(security_findings)} findings)", body_style),
            Paragraph(f"<font size='18'><b>{dark_risk_score}</b></font>/100<br/><b>{dark_risk_level} Risk</b> ({len(patterns)} patterns)", body_style),
            Paragraph(
                f"<b>Model:</b> Calibrated Linear SVM<br/>"
                f"<b>Avg Conf:</b> {round(ai_data.get('average_confidence', 0.95)*100, 1)}%<br/>"
                f"<b>Dataset:</b> EC-DarkPattern",
                body_style,
            ),
        ],
    ]
    scores_table = Table(scores_data, colWidths=[180, 180, 180])
    scores_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f0fdf4") if security_score >= 80 else colors.HexColor("#fff7ed")),
        ("BACKGROUND", (1, 0), (1, -1), colors.HexColor("#faf5ff") if dark_risk_score > 0 else colors.HexColor("#f0fdf4")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(scores_table)
    story.append(Spacer(1, 14))

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
    footer_text = Paragraph(
        "<b>DarkShield AI Methodology:</b> Classification performed using Calibrated Linear SVM (trained on EC-DarkPattern "
        "corpus, 95.21% test accuracy) corroborated with contextual DOM heuristics and Playwright rendering. "
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
