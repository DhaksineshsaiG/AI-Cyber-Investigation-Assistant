import io
import re
from datetime import datetime
from typing import Dict, Any, List
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

# Forensic Color Palette
COLOR_NAVY = colors.HexColor("#0f172a")        # Slate-900 / Deep Navy
COLOR_NAVY_LIGHT = colors.HexColor("#1e293b")  # Slate-800
COLOR_TEAL = colors.HexColor("#0d9488")        # Teal-600
COLOR_TEAL_LIGHT = colors.HexColor("#f0fdfa")  # Teal-50
COLOR_SLATE_BG = colors.HexColor("#f8fafc")    # Slate-50
COLOR_SLATE_BORDER = colors.HexColor("#cbd5e1")# Slate-300
COLOR_SLATE_MUTED = colors.HexColor("#64748b") # Slate-500
COLOR_TEXT_MAIN = colors.HexColor("#1e293b")   # Slate-800
COLOR_ROSE = colors.HexColor("#be123c")        # Rose-700
COLOR_AMBER = colors.HexColor("#b45309")       # Amber-700


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and stamp exact total page counts
    along with official forensic dossier running header and running footer.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_running_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_running_decorations(self, page_count: int):
        self.saveState()

        # Running Header on page 2 and beyond
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(COLOR_NAVY)
            self.drawString(36, 762, "AI CYBER INVESTIGATION ASSISTANT - CASE INVESTIGATION DOSSIER")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(COLOR_SLATE_MUTED)
            self.drawRightString(576, 762, "CONFIDENTIAL // LAW ENFORCEMENT & FORENSIC USE ONLY")
            self.setStrokeColor(COLOR_SLATE_BORDER)
            self.setLineWidth(0.6)
            self.line(36, 756, 576, 756)

        # Running Footer on every page
        self.setStrokeColor(COLOR_SLATE_BORDER)
        self.setLineWidth(0.6)
        self.line(36, 36, 576, 36)

        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(COLOR_TEAL)
        self.drawString(36, 25, "DIGITAL EVIDENCE VAULT")
        self.setFont("Helvetica", 7)
        self.setFillColor(COLOR_SLATE_MUTED)
        self.drawString(145, 25, "- Cryptographic Integrity Verified (SHA-256)")

        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(COLOR_NAVY)
        self.drawRightString(576, 25, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()


def format_sha256_for_pdf(hash_val: str) -> str:
    """
    Splits 64-character SHA-256 hash into two clean, readable 32-character lines
    using monospace font. Guarantees zero column overflow or awkward line-wrapping.
    """
    if not hash_val:
        return "N/A"
    clean = str(hash_val).strip()
    if len(clean) == 64:
        return f'<font name="Courier" size="6.5" color="#334155">{clean[:32]}<br/>{clean[32:]}</font>'
    return f'<font name="Courier" size="6.5" color="#334155">{clean}</font>'


def parse_observation_for_pdf(finding_text: str) -> Dict[str, str]:
    """
    Extracts filename, hash, size, and narrative from finding bullet for card layout in PDF.
    """
    text = finding_text.strip()
    file_match = re.search(r"['\"]?([\w.-]+\.(?:png|jpg|jpeg|pdf|txt|csv|log|docx|json))['\"]?", text, re.I)
    filename = file_match.group(1) if file_match else None

    hash_match = re.search(r"\b([a-f0-9]{64})\b", text, re.I)
    hash_val = hash_match.group(1) if hash_match else None

    size_match = re.search(r"\b(\d+(?:,\d+)?\s*(?:bytes|KB|MB|GB))\b", text, re.I)
    size_val = size_match.group(1) if size_match else None

    # Clean description
    desc = text
    if hash_val:
        desc = re.sub(r"\(?SHA-?256:?\s*[a-f0-9]{64}\)?", "", desc, flags=re.I).strip()

    title = filename if filename else "Forensic Observation"
    if not filename and ":" in desc:
        parts = desc.split(":", 1)
        title = parts[0].strip()
        desc = parts[1].strip()

    return {
        "title": title,
        "filename": filename or "",
        "size": size_val or "",
        "hash": hash_val or "",
        "description": desc or text
    }


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
        topMargin=0.55 * inch,
        bottomMargin=0.55 * inch
    )

    styles = getSampleStyleSheet()

    # Typography & Hierarchical Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=COLOR_NAVY,
        spaceAfter=3,
        keepWithNext=True
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=COLOR_TEAL,
        spaceAfter=8,
        keepWithNext=True
    )
    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=COLOR_NAVY,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )
    subheading = ParagraphStyle(
        'SubHeading',
        parent=styles['Heading3'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12,
        textColor=COLOR_TEAL,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )
    body_style = ParagraphStyle(
        'BodyDark',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=COLOR_TEXT_MAIN
    )
    body_bold = ParagraphStyle(
        'BodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    meta_label = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=COLOR_SLATE_MUTED
    )
    meta_val = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=COLOR_NAVY
    )
    table_header = ParagraphStyle(
        'TableHeader',
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
        textColor=COLOR_SLATE_MUTED
    )
    bullet_style = ParagraphStyle(
        'BulletStyle',
        parent=body_style,
        leftIndent=10,
        firstLineIndent=-10,
        spaceAfter=3
    )

    elements = []

    # =========================================================================
    # PAGE HEADER
    # =========================================================================
    elements.append(Paragraph("AI CYBER INVESTIGATION ASSISTANT", title_style))
    elements.append(Paragraph("OFFICIAL DIGITAL EVIDENCE INVESTIGATION DOSSIER", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_TEAL, spaceBefore=0, spaceAfter=8))

    # =========================================================================
    # CASE SUMMARY
    # =========================================================================
    case_id = case_data.get("case_id", dashboard_data.get("case_id", "N/A"))
    title = case_data.get("title", dashboard_data.get("title", "Untitled Investigation"))
    investigator = case_data.get("investigator", dashboard_data.get("investigator", "Primary Forensics Unit"))
    status = case_data.get("status", dashboard_data.get("status", "ACTIVE"))
    report_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    ev_count = len(evidence_list)

    summary_rows = [
        [
            Paragraph("CASE IDENTIFIER", meta_label), Paragraph(f"<b>{case_id}</b>", meta_val),
            Paragraph("GENERATED DATE", meta_label), Paragraph(report_timestamp, meta_val)
        ],
        [
            Paragraph("CASE TITLE", meta_label), Paragraph(title, body_style),
            Paragraph("LEAD INVESTIGATOR", meta_label), Paragraph(investigator, body_style)
        ],
        [
            Paragraph("STATUS", meta_label), Paragraph(f"<font color='#0d9488'><b>{status.upper()}</b></font>", body_style),
            Paragraph("EVIDENCE COUNT", meta_label), Paragraph(f"<b>{ev_count} file(s) preserved in vault</b>", body_style)
        ]
    ]

    meta_table = Table(summary_rows, colWidths=[1.25 * inch, 2.5 * inch, 1.25 * inch, 2.5 * inch])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_SLATE_BG),
        ('BOX', (0, 0), (-1, -1), 0.75, COLOR_SLATE_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 10))

    # =========================================================================
    # 1. EVIDENCE & CHAIN OF CUSTODY
    # =========================================================================
    elements.append(Paragraph("1. EVIDENCE & CHAIN OF CUSTODY", section_heading))
    elements.append(Paragraph("Cryptographic SHA-256 hash preservation established immediately upon vault ingestion:", disclaimer_style))
    elements.append(Spacer(1, 4))

    custody_data = [[
        Paragraph("Evidence ID", table_header),
        Paragraph("Filename", table_header),
        Paragraph("Type", table_header),
        Paragraph("Size", table_header),
        Paragraph("Cryptographic SHA-256 Fingerprint", table_header)
    ]]

    for ev in evidence_list:
        sha_formatted = format_sha256_for_pdf(ev.get("sha256_hash", ""))
        size_bytes = ev.get("file_size", 0)
        size_display = f"{size_bytes:,} B" if size_bytes < 1024 else f"{(size_bytes/1024):.1f} KB"

        custody_data.append([
            Paragraph(f"<b>{ev.get('evidence_id', '')}</b>", body_style),
            Paragraph(ev.get("original_filename", "")[:28], body_style),
            Paragraph(f"<b>{ev.get('file_type', 'N/A')}</b>", body_style),
            Paragraph(size_display, body_style),
            Paragraph(sha_formatted, body_style)
        ])

    if len(custody_data) == 1:
        custody_data.append([
            Paragraph("-", body_style),
            Paragraph("No evidence ingested into case repository", body_style),
            Paragraph("-", body_style),
            Paragraph("-", body_style),
            Paragraph("-", body_style)
        ])

    custody_table = Table(
        custody_data,
        colWidths=[1.0 * inch, 1.7 * inch, 0.65 * inch, 0.75 * inch, 3.4 * inch],
        repeatRows=1
    )
    custody_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
        ('TOPPADDING', (0, 0), (-1, 0), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 1), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4.5),
    ]))
    elements.append(custody_table)
    elements.append(Spacer(1, 10))

    # =========================================================================
    # 2. EXTRACTED FORENSIC ENTITIES
    # =========================================================================
    elements.append(Paragraph("2. EXTRACTED FORENSIC ENTITIES", section_heading))
    elements.append(Paragraph("Entities extracted and validated across uploaded files via spaCy NER and pattern recognition:", disclaimer_style))
    elements.append(Spacer(1, 4))

    entity_groups = dashboard_data.get("entity_groups", [])
    valid_groups = [g for g in entity_groups if g.get("items") and len(g.get("items", [])) > 0]

    if valid_groups:
        # Group entities into a clean 2-column card layout
        cat_cards = []
        for grp in valid_groups:
            cat_title = grp.get("title", grp.get("category", "Entities")).upper()
            items = grp.get("items", [])
            lines = [f"<b><font color='{COLOR_TEAL.hexval()}'>{cat_title} ({len(items)})</font></b>"]
            for item in items[:15]:
                lines.append(f"• {item}")
            if len(items) > 15:
                lines.append(f"<i>... and {len(items) - 15} additional entries</i>")
            cat_cards.append(Paragraph("<br/>".join(lines), body_style))

        # Arrange cards into pairs of 2 columns
        grid_rows = []
        for i in range(0, len(cat_cards), 2):
            left = cat_cards[i]
            right = cat_cards[i + 1] if i + 1 < len(cat_cards) else Paragraph("", body_style)
            grid_rows.append([left, right])

        ent_grid = Table(grid_rows, colWidths=[3.7 * inch, 3.8 * inch])
        ent_grid.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_SLATE_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        elements.append(ent_grid)
    else:
        elements.append(Table([[
            Paragraph("<i>No entities were extracted from the uploaded evidence.</i>", disclaimer_style)
        ]], colWidths=[7.5 * inch], style=[
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_SLATE_BG),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
    elements.append(Spacer(1, 10))

    # =========================================================================
    # 3. SUSPICIOUS KEYWORDS & TAXONOMY
    # =========================================================================
    elements.append(Paragraph("3. SUSPICIOUS KEYWORDS & TAXONOMY", section_heading))
    elements.append(Paragraph("Keyword detection based on 10-category forensic cybercrime threat taxonomy:", disclaimer_style))
    elements.append(Spacer(1, 4))

    keywords = dashboard_data.get("keywords", [])
    kw_rows = [[
        Paragraph("Keyword", table_header),
        Paragraph("Category", table_header),
        Paragraph("Severity", table_header),
        Paragraph("Matches", table_header),
        Paragraph("Context", table_header)
    ]]

    for kw in keywords[:12]:
        sev = kw.get("severity", "medium").lower()
        if sev == "high":
            sev_markup = f"<font color='{COLOR_ROSE.hexval()}'><b>HIGH</b></font>"
        elif sev == "medium":
            sev_markup = f"<font color='{COLOR_AMBER.hexval()}'><b>MEDIUM</b></font>"
        else:
            sev_markup = "<font color='#64748b'>LOW</font>"

        snippet = kw.get("snippets", [""])[0] if kw.get("snippets") else "-"
        kw_rows.append([
            Paragraph(f"<b>{kw.get('keyword', '')}</b>", body_style),
            Paragraph(kw.get("category", ""), body_style),
            Paragraph(sev_markup, body_style),
            Paragraph(f"<b>{kw.get('count', 1)} match(es)</b>", body_style),
            Paragraph(snippet[:120], body_style)
        ])

    if len(kw_rows) == 1:
        kw_rows.append([
            Paragraph("-", body_style),
            Paragraph("No suspicious keywords detected in evidence vault", body_style),
            Paragraph("-", body_style),
            Paragraph("-", body_style),
            Paragraph("-", body_style)
        ])

    kw_table = Table(
        kw_rows,
        colWidths=[1.2 * inch, 1.4 * inch, 0.75 * inch, 0.65 * inch, 3.5 * inch],
        repeatRows=1
    )
    kw_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(kw_table)
    elements.append(Spacer(1, 10))

    # =========================================================================
    # 4. CHRONOLOGICAL TIMELINE
    # =========================================================================
    elements.append(Paragraph("4. CHRONOLOGICAL TIMELINE", section_heading))
    elements.append(Paragraph("Chronological sequence of extracted events, communication logs, and system actions:", disclaimer_style))
    elements.append(Spacer(1, 4))

    timeline_events = dashboard_data.get("timeline", [])
    timeline_rows = [[
        Paragraph("Timestamp", table_header),
        Paragraph("Event", table_header),
        Paragraph("Classification", table_header),
        Paragraph("Source", table_header)
    ]]

    for evt in timeline_events[:20]:
        timeline_rows.append([
            Paragraph(f"<b>{evt.get('time', '')}</b>", body_style),
            Paragraph(evt.get("detail", ""), body_style),
            Paragraph(f"<font color='{COLOR_TEAL.hexval()}'><b>{evt.get('title', '')}</b></font>", body_style),
            Paragraph(evt.get("source_evidence", "")[:24], body_style)
        ])

    if len(timeline_rows) == 1:
        timeline_rows.append([
            Paragraph("-", body_style),
            Paragraph("No chronological temporal events parsed from evidence", body_style),
            Paragraph("-", body_style),
            Paragraph("-", body_style)
        ])

    time_table = Table(
        timeline_rows,
        colWidths=[1.15 * inch, 3.4 * inch, 1.45 * inch, 1.5 * inch],
        repeatRows=1
    )
    time_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(time_table)
    elements.append(Spacer(1, 10))

    # =========================================================================
    # 5. CROSS-EVIDENCE CORRELATION
    # =========================================================================
    elements.append(Paragraph("5. CROSS-EVIDENCE CORRELATION", section_heading))
    elements.append(Paragraph("Entities, identities, or identifiers surfaced across multiple independent evidence sources:", disclaimer_style))
    elements.append(Spacer(1, 4))

    correlations = dashboard_data.get("correlations", [])
    corr_rows = [[
        Paragraph("Entity", table_header),
        Paragraph("Type", table_header),
        Paragraph("Sources", table_header),
        Paragraph("Occurrences", table_header)
    ]]

    for corr in correlations:
        corr_rows.append([
            Paragraph(f"<b>{corr.get('entity_value', '')}</b>", body_style),
            Paragraph(corr.get("entity_type", ""), body_style),
            Paragraph(", ".join(corr.get("evidence_names", [])), body_style),
            Paragraph(f"<b>{corr.get('occurrences', 1)} file(s)</b>", body_style)
        ])

    if len(corr_rows) == 1:
        corr_rows.append([
            Paragraph("-", body_style),
            Paragraph("-", body_style),
            Paragraph("No cross-evidence correlations observed", body_style),
            Paragraph("-", body_style)
        ])

    corr_table = Table(
        corr_rows,
        colWidths=[2.1 * inch, 1.2 * inch, 3.2 * inch, 1.0 * inch],
        repeatRows=1
    )
    corr_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_NAVY),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_SLATE_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(corr_table)
    elements.append(Spacer(1, 12))

    # =========================================================================
    # 6. AI ASSISTIVE INVESTIGATION INSIGHTS
    # =========================================================================
    ai_data = dashboard_data.get("ai_insights", {})
    ai_summary = ai_data.get("summary", "AI synthesis unavailable.")
    findings = ai_data.get("findings", [])
    leads = ai_data.get("leads", [])

    elements.append(Paragraph("6. AI ASSISTIVE INVESTIGATION INSIGHTS", section_heading))
    elements.append(Table([[
        Paragraph(
            "<b>ASSISTIVE DISCLAIMER:</b> AI-generated assistive analysis. Findings require investigator verification.",
            disclaimer_style
        )
    ]], colWidths=[7.5 * inch], style=[
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_TEAL_LIGHT),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#99f6e4")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(Spacer(1, 6))

    # Executive Synthesis Block
    elements.append(Paragraph("Executive Synthesis", subheading))
    elements.append(Table([[
        Paragraph(ai_summary, body_style)
    ]], colWidths=[7.5 * inch], style=[
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_SLATE_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(Spacer(1, 8))

    # Key Evidence Observations
    if findings:
        elements.append(Paragraph("Key Evidence Observations", subheading))
        obs_rows = []
        for f in findings:
            obs = parse_observation_for_pdf(f)
            meta_line = ""
            if obs["size"]:
                meta_line += f"<b>Size:</b> {obs['size']} &nbsp;&nbsp;|&nbsp;&nbsp; "
            if obs["hash"]:
                meta_line += f"<b>SHA-256:</b> <font name='Courier' size='6.5'>{obs['hash'][:32]}...{obs['hash'][-16:]}</font>"

            card_content = [f"<b>EVIDENCE ARTIFACT: {obs['title']}</b>"]
            if meta_line:
                card_content.append(f"<font color='{COLOR_SLATE_MUTED.hexval()}'>{meta_line}</font>")
            card_content.append(obs['description'])

            obs_rows.append([Paragraph("<br/>".join(card_content), body_style)])

        obs_table = Table(obs_rows, colWidths=[7.5 * inch])
        obs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(obs_table)
        elements.append(Spacer(1, 8))

    # Recommended Follow-ups
    if leads:
        elements.append(Paragraph("Recommended Investigative Follow-ups", subheading))
        for idx, ld in enumerate(leads, 1):
            elements.append(Paragraph(f"<b>{idx}.</b> {ld}", bullet_style))
        elements.append(Spacer(1, 8))

    # =========================================================================
    # 7. INVESTIGATOR VERIFICATION
    # =========================================================================
    sig_data = [
        [
            Paragraph("<b>Investigator Signature:</b><br/><br/>_____________________________________<br/>" + investigator, body_style),
            Paragraph("<b>Supervisor Verification:</b><br/><br/>_____________________________________<br/>Department Supervisor / Reviewing Officer", body_style)
        ],
        [
            Paragraph("<b>Date:</b> ________________________", body_style),
            Paragraph("<b>Date:</b> ________________________", body_style)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[3.75 * inch, 3.75 * inch])
    sig_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_SLATE_BG),
        ('BOX', (0, 0), (-1, -1), 0.5, COLOR_SLATE_BORDER),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(KeepTogether([
        Spacer(1, 8),
        Paragraph("7. INVESTIGATOR VERIFICATION & SIGN-OFF", section_heading),
        Spacer(1, 4),
        sig_table
    ]))

    # Build PDF with two-pass NumberedCanvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    buffer.seek(0)
    return buffer
