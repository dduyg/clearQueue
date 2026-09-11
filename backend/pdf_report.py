"""
PDF export: a one-page explanation per case, and a work-queue summary
report. Built with reportlab (Platypus), matching the same information
already shown in the UI so the PDF is never the "more honest" version.
"""
from __future__ import annotations
import io

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable,
)

HIGH_HEX, MEDIUM_HEX, LOW_HEX = "b8412f", "b07a1e", "357a5b"
BRAND = colors.HexColor("#1a2a4a")
HIGH = colors.HexColor(f"#{HIGH_HEX}")
MEDIUM = colors.HexColor(f"#{MEDIUM_HEX}")
LOW = colors.HexColor(f"#{LOW_HEX}")
MUTED = colors.HexColor("#5c6070")


def _priority_color(score: int):
    if score >= 75:
        return HIGH
    if score >= 50:
        return MEDIUM
    return LOW


def _priority_hex(score: int) -> str:
    if score >= 75:
        return HIGH_HEX
    if score >= 50:
        return MEDIUM_HEX
    return LOW_HEX


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CQTitle", fontSize=20, leading=24, textColor=BRAND, spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="CQSubtitle", fontSize=10, textColor=MUTED, spaceAfter=14))
    styles.add(ParagraphStyle(name="CQSection", fontSize=12, textColor=BRAND, spaceBefore=14, spaceAfter=6, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="CQBody", fontSize=10, leading=14, textColor=colors.black))
    styles.add(ParagraphStyle(name="CQMuted", fontSize=9, leading=12, textColor=MUTED))
    return styles


def build_case_pdf(case: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    styles = _styles()
    story = []

    priority = case.get("priority", {})
    score = priority.get("score", 0)
    color_hex = _priority_hex(score)

    story.append(Paragraph("ClearQueue — Case Report", styles["CQTitle"]))
    story.append(Paragraph("Explainable case prioritization", styles["CQSubtitle"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=1))
    story.append(Spacer(1, 12))

    header_table = Table(
        [[
            Paragraph(f"<b>{case.get('case_id', '')}</b><br/><font color='#5c6070' size=9>{case.get('category', 'Uncategorized')}</font>", styles["CQBody"]),
            Paragraph(f"<font color='#{color_hex}' size=28><b>{score}</b></font><br/><font color='#5c6070' size=9>{priority.get('recommended_action', '')}</font>", styles["CQBody"]),
        ]],
        colWidths=[10 * cm, 6 * cm],
    )
    header_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(header_table)
    story.append(Spacer(1, 16))

    story.append(Paragraph("Score breakdown", styles["CQSection"]))
    factor_rows = [["Factor", "Points", "Why"]]
    for f in priority.get("factors", []):
        pts = f"+{f['points']}" if f.get("available", True) else "n/a"
        factor_rows.append([f["label"], f"{pts} / {f['max_points']}", f["detail"]])
    factor_table = Table(factor_rows, colWidths=[4.2 * cm, 2.8 * cm, 9 * cm])
    factor_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1d26")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f5f5")]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(factor_table)
    story.append(Spacer(1, 14))

    story.append(Paragraph("What would reduce this score", styles["CQSection"]))
    for s in priority.get("reduction_suggestions", []):
        story.append(Paragraph(f"• {s}", styles["CQBody"]))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "This score is a prioritization recommendation for human review, not an automated "
        "decision. Model type: rule-based. Explainability: 100%.",
        styles["CQMuted"],
    ))

    doc.build(story)
    return buf.getvalue()


def build_queue_pdf(cases: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, topMargin=2 * cm, bottomMargin=2 * cm, leftMargin=2 * cm, rightMargin=2 * cm)
    styles = _styles()
    story = []

    sorted_cases = sorted(cases, key=lambda c: c.get("priority", {}).get("score", 0), reverse=True)
    n = len(sorted_cases)
    high = sum(1 for c in sorted_cases if c.get("priority", {}).get("score", 0) >= 75)
    medium = sum(1 for c in sorted_cases if 50 <= c.get("priority", {}).get("score", 0) < 75)
    low = n - high - medium

    story.append(Paragraph("ClearQueue — Work Queue Report", styles["CQTitle"]))
    story.append(Paragraph(f"{n} cases · {high} high priority · {medium} medium · {low} low", styles["CQSubtitle"]))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=1))
    story.append(Spacer(1, 14))

    rows = [["Case ID", "Category", "Score", "Recommended action"]]
    for c in sorted_cases:
        p = c.get("priority", {})
        rows.append([c.get("case_id", ""), c.get("category", "") or "—", str(p.get("score", "")), p.get("recommended_action", "")])

    table = Table(rows, colWidths=[3.5 * cm, 4.5 * cm, 2 * cm, 6 * cm], repeatRows=1)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1d26")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for i, c in enumerate(sorted_cases, start=1):
        score = c.get("priority", {}).get("score", 0)
        style_cmds.append(("TEXTCOLOR", (2, i), (2, i), _priority_color(score)))
        style_cmds.append(("FONTNAME", (2, i), (2, i), "Helvetica-Bold"))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", color=colors.HexColor("#dddddd"), thickness=1))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Scores are prioritization recommendations for human review, not automated "
        "decisions. Model type: rule-based. Explainability: 100%.",
        styles["CQMuted"],
    ))

    doc.build(story)
    return buf.getvalue()
