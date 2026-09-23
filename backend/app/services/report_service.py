import io
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Color Palette matching the Digital Forensic Workspace
COLOR_NAVY = colors.HexColor("#111d36")
COLOR_TEAL = colors.HexColor("#0d9488")
COLOR_SLATE_BG = colors.HexColor("#f8fafc")
COLOR_TEXT_MAIN = colors.HexColor("#0f172a")
COLOR_TEXT_MUTED = colors.HexColor("#475569")
COLOR_ROSE = colors.HexColor("#be123c")
COLOR_AMBER = colors.HexColor("#b45309")

def build_pdf_report(case_data: Dict[str, Any], evidence_list: List[Dict[str, Any]], dashboard_data: Dict[str, Any]) -> io.BytesIO:
    """
    Generates a formal, defensible digital forensics investigation report in PDF format.
    Explicitly distinguishes verified extracted evidence from AI assistive hypotheses.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.5 * inch,
        rightMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()

    # Custom typography
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=COLOR_NAVY,
        spaceAfter=4
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT_MUTED,
        spaceAfter=12
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=COLOR_NAVY,
        spaceBefore=10,
        spaceAfter=6
    )
    subheading = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=COLOR_TEAL,
        spaceBefore=6,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_TEXT_MAIN
    )
    badge_style = ParagraphStyle(
        'BadgeText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white
    )
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT_MUTED
    )

    elements = []

    # 1. Header Banner
    elements.append(Paragraph("AI CYBER INVESTIGATION ASSISTANT", title_style))
    elements.append(Paragraph("OFFICIAL DIGITAL EVIDENCE INVESTIGATION DOSSIER", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_TEAL, spaceBefore=0, spaceAfter=8))

    # 2. Case Overview Table
    case_id = case_data.get("case_id", "N/A")
    title = case_data.get("title", "Untitled Investigation")
    investigator = case_data.get("investigator", "Primary Forensics Unit")
    status = case_data.get("status", "ACTIVE")
    report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")

    meta_table_data = [
        [
            Paragraph("<b>Case Identifier:</b>", body_style), Paragraph(case_id, body_style),
            Paragraph("<b>Generated:</b>", body_style), Paragraph(report_timestamp, body_style)
        ],
        [
            Paragraph("<b>Case Title:</b>", body_style), Paragraph(title, body_style),
            Paragraph("<b>Investigator:</b>", body_style), Paragraph(investigator, body_style)
        ],
        [
            Paragraph("<b>Investigation Status:</b>", body_style), Paragraph(status, body_style),
            Paragraph("<b>Total Evidence Files:</b>", body_style), Paragraph(str(len(evidence_list)), body_style)
        ]
    ]

    meta_table = Table(meta_table_data, colWidths=[1.3*inch, 2.4*inch, 1.3*inch, 2.5*inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_SLATE_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 12))

    # 3. Chain of Custody & Evidence Vault Hashing
    elements.append(Paragraph("1. CHAIN OF CUSTODY & EVIDENCE VAULT INTEGRITY", section_heading))
    elements.append(Paragraph("Cryptographic SHA-256 verification hashes calculated upon evidence ingestion:", disclaimer_style))
    elements.append(Spacer(1, 4))

    custody_data = [["Evidence ID", "Original Filename", "File Type", "Size (Bytes)", "SHA-256 Hash"]]
    for ev in evidence_list:
        sha_formatted = ev.get("sha256_hash", "")
        # Shorten display if needed or keep full in smaller text
        custody_data.append([
            ev.get("evidence_id", ""),
            ev.get("original_filename", "")[:25],
            ev.get("file_type", ""),
            str(ev.get("file_size", 0)),
            Paragraph(f"<font size=6>{sha_formatted}</font>", body_style)
        ])

    if len(custody_data) == 1:
        custody_data.append(["-", "No evidence ingested", "-", "-", "-"])

    custody_table = Table(custody_data, colWidths=[1.1*inch, 1.8*inch, 0.9*inch, 0.9*inch, 2.8*inch])
    custody_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
    ]))
    elements.append(custody_table)
    elements.append(Spacer(1, 12))

    # 4. Extracted Entities
    elements.append(Paragraph("2. EXTRACTED FORENSIC ENTITIES (NLP & REGEX)", section_heading))
    entity_groups = dashboard_data.get("entity_groups", [])
    entity_rows = [["Entity Category", "Extracted Items"]]
    for grp in entity_groups:
        items_str = ", ".join(grp.get("items", [])) or "None identified"
        entity_rows.append([grp.get("title", ""), Paragraph(items_str, body_style)])

    if len(entity_rows) == 1:
        entity_rows.append(["Entities", "No entities extracted."])

    ent_table = Table(entity_rows, colWidths=[1.8*inch, 5.7*inch])
    ent_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_TEAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(ent_table)
    elements.append(Spacer(1, 12))

    # 5. Suspicious Keywords
    elements.append(Paragraph("3. DETECTED SUSPICIOUS KEYWORDS & TAXONOMY", section_heading))
    keywords = dashboard_data.get("keywords", [])
    kw_rows = [["Keyword", "Category", "Severity", "Matches", "Contextual Snippet"]]
    for kw in keywords[:10]:
        snippet = kw.get("snippets", [""])[0] if kw.get("snippets") else "-"
        kw_rows.append([
            kw.get("keyword", ""),
            kw.get("category", ""),
            kw.get("severity", "").upper(),
            str(kw.get("count", 1)),
            Paragraph(snippet[:90], body_style)
        ])

    if len(kw_rows) == 1:
        kw_rows.append(["-", "None detected", "-", "-", "-"])

    kw_table = Table(kw_rows, colWidths=[1.2*inch, 1.4*inch, 0.8*inch, 0.7*inch, 3.4*inch])
    kw_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(kw_table)
    elements.append(Spacer(1, 12))

    # 6. Timeline of Events
    elements.append(Paragraph("4. CHRONOLOGICAL TIMELINE OF EVENTS", section_heading))
    timeline_events = dashboard_data.get("timeline", [])
    timeline_rows = [["Timestamp", "Event Classification", "Source File", "Evidence Context"]]
    for evt in timeline_events[:15]:
        timeline_rows.append([
            evt.get("time", ""),
            evt.get("title", ""),
            evt.get("source_evidence", "")[:20],
            Paragraph(evt.get("detail", ""), body_style)
        ])

    if len(timeline_rows) == 1:
        timeline_rows.append(["-", "No temporal events parsed", "-", "-"])

    time_table = Table(timeline_rows, colWidths=[1.2*inch, 1.6*inch, 1.4*inch, 3.3*inch])
    time_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_TEAL),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(time_table)
    elements.append(Spacer(1, 12))

    # 7. Cross-Evidence Correlation
    elements.append(Paragraph("5. CROSS-EVIDENCE RELATIONSHIP MAPPING", section_heading))
    correlations = dashboard_data.get("correlations", [])
    corr_rows = [["Correlated Entity", "Type", "Observed Sources", "Occurrences"]]
    for corr in correlations:
        corr_rows.append([
            corr.get("entity_value", ""),
            corr.get("entity_type", ""),
            Paragraph(", ".join(corr.get("evidence_names", [])), body_style),
            str(corr.get("occurrences", 1))
        ])

    if len(corr_rows) == 1:
        corr_rows.append(["-", "-", "No cross-evidence correlations observed", "-"])

    corr_table = Table(corr_rows, colWidths=[1.8*inch, 1.2*inch, 3.5*inch, 1.0*inch])
    corr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(corr_table)
    elements.append(Spacer(1, 12))

    # 8. AI Assistive Investigation Insights
    elements.append(KeepTogether([
        Paragraph("6. AI ASSISTIVE INVESTIGATION INSIGHTS (GROQ ENGINE)", section_heading),
        Paragraph("<b>NOTICE:</b> The following sections represent AI-generated assistive analysis based strictly on the uploaded evidence. They are intended as investigative leads and require formal investigator verification.", disclaimer_style),
        Spacer(1, 6)
    ]))

    ai_data = dashboard_data.get("ai_insights", {})
    ai_summary = ai_data.get("summary", "AI synthesis unavailable.")
    elements.append(Paragraph("<b>Executive Synthesis:</b>", subheading))
    elements.append(Paragraph(ai_summary, body_style))
    elements.append(Spacer(1, 6))

    findings = ai_data.get("findings", [])
    if findings:
        elements.append(Paragraph("<b>Key Correlated Observations:</b>", subheading))
        for f in findings:
            elements.append(Paragraph(f"• {f}", body_style))
        elements.append(Spacer(1, 6))

    leads = ai_data.get("leads", [])
    if leads:
        elements.append(Paragraph("<b>Recommended Investigative Follow-Ups:</b>", subheading))
        for ld in leads:
            elements.append(Paragraph(f"• {ld}", body_style))
        elements.append(Spacer(1, 8))

    # 9. Signatures Block
    sig_data = [
        [
            Paragraph("<b>Investigator Signature:</b> ___________________________", body_style),
            Paragraph("<b>Supervisor Verification:</b> ___________________________", body_style)
        ],
        [
            Paragraph(f"Name: {investigator}", body_style),
            Paragraph("Department: AI & Cyber Forensics Unit", body_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.75*inch, 3.75*inch])
    sig_table.setStyle(TableStyle([
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(Spacer(1, 16))
    elements.append(KeepTogether(sig_table))

    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer
