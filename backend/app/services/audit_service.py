import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from app.database import get_collection

logger = logging.getLogger("investigation.audit")

# Brand Design Colors for PDF Report
COLOR_BRAND = colors.HexColor("#C8102E")       # Shiny Royal Red
COLOR_BRAND_DEEP = colors.HexColor("#A50F26")  # Deep Royal Red
COLOR_BRAND_SOFT = colors.HexColor("#FFF1F2")  # Soft Red Background
COLOR_TEXT_MAIN = colors.HexColor("#1F2937")   # Dark Slate Main Text
COLOR_TEXT_MUTED = colors.HexColor("#6B7280")  # Secondary Text
COLOR_BORDER = colors.HexColor("#E5E7EB")      # Borders
COLOR_BG_SUBTLE = colors.HexColor("#F8FAFC")   # Neutral Background
COLOR_SUCCESS = colors.HexColor("#059669")     # Accessible Green
COLOR_WARNING = colors.HexColor("#D97706")     # Accessible Amber
COLOR_ERROR = colors.HexColor("#DC2626")       # Accessible Red


class AuditReportNumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas for dynamic total page count and professional audit header/footer.
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
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count: int):
        self.saveState()

        # Running Header on page 2 and beyond
        if self._pageNumber > 1:
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(COLOR_BRAND)
            self.drawString(36, 762, "AI CYBER INVESTIGATION ASSISTANT - INVESTIGATOR ACTIVITY AUDIT REPORT")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(COLOR_TEXT_MUTED)
            self.drawRightString(576, 762, "OFFICIAL USE ONLY // CHAIN OF CUSTODY VERIFIED")
            self.setStrokeColor(COLOR_BORDER)
            self.setLineWidth(0.6)
            self.line(36, 756, 576, 756)

        # Running Footer on every page
        self.setStrokeColor(COLOR_BORDER)
        self.setLineWidth(0.6)
        self.line(36, 36, 576, 36)

        self.setFont("Helvetica-Bold", 7)
        self.setFillColor(COLOR_BRAND)
        self.drawString(36, 25, "OFFICIAL AUDIT TRAIL")
        self.setFont("Helvetica", 7)
        self.setFillColor(COLOR_TEXT_MUTED)
        self.drawString(140, 25, "- Server-Verified Immutable Security Log")

        self.setFont("Helvetica-Bold", 7.5)
        self.setFillColor(COLOR_TEXT_MAIN)
        self.drawRightString(576, 25, f"Page {self._pageNumber} of {page_count}")

        self.restoreState()


async def record_audit_event(
    actor_user_id: str,
    actor_role: str,
    action_type: str,
    action_label: str,
    case_id: Optional[str] = None,
    details: str = "",
    status: str = "success",
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Records a real server-side audit event to the dedicated MongoDB 'audit_events' collection.
    Derives actor identity strictly from the authenticated server-side context.
    Never exposes passwords, tokens, API keys, or raw evidence contents.
    """
    now = datetime.now(timezone.utc)
    event_id = f"AUD-{int(now.timestamp())}-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "event_id": event_id,
        "timestamp": now.isoformat(),
        "actor_user_id": actor_user_id.strip().lower(),
        "actor_role": actor_role.strip().lower(),
        "action_type": action_type.strip(),
        "action_label": action_label.strip(),
        "case_id": case_id.strip() if case_id else None,
        "details": details.strip(),
        "status": "success" if status == "success" else "failure",
        "metadata": metadata or {}
    }

    try:
        col = get_collection("audit_events")
        await col.insert_one(doc)
        logger.info(f"Audit event recorded: [{event_id}] {doc['actor_user_id']} ({doc['actor_role']}) -> {doc['action_type']} [{doc['status']}]")
    except Exception as e:
        logger.error(f"Failed to write audit event [{event_id}]: {e}", exc_info=True)

    return doc


async def query_audit_events(
    investigator_id: Optional[str] = None,
    action_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    case_id: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 50
) -> Dict[str, Any]:
    """
    Queries audit events with optional filters, search, and pagination.
    Returns events in reverse chronological order (newest first).
    """
    col = get_collection("audit_events")
    query: Dict[str, Any] = {}

    if investigator_id and investigator_id.strip():
        norm_id = investigator_id.strip().lower()
        if norm_id != "all":
            query["actor_user_id"] = norm_id

    if action_type and action_type.strip() and action_type.strip() != "all":
        query["action_type"] = action_type.strip()

    if case_id and case_id.strip():
        query["case_id"] = case_id.strip()

    # Date range filters (ISO format strings)
    date_filter: Dict[str, str] = {}
    if start_date and start_date.strip():
        date_filter["$gte"] = start_date.strip()
    if end_date and end_date.strip():
        date_filter["$lte"] = end_date.strip()
    if date_filter:
        query["timestamp"] = date_filter

    # Keyword search across details, action_label, actor_user_id, case_id
    if search and search.strip():
        s = search.strip()
        query["$or"] = [
            {"details": {"$regex": s, "$options": "i"}},
            {"action_label": {"$regex": s, "$options": "i"}},
            {"actor_user_id": {"$regex": s, "$options": "i"}},
            {"case_id": {"$regex": s, "$options": "i"}},
            {"event_id": {"$regex": s, "$options": "i"}}
        ]

    # Enforce bounds on pagination
    page = max(1, int(page))
    limit = max(1, min(200, int(limit)))
    skip_count = (page - 1) * limit

    total_count = await col.count_documents(query)

    cursor = col.find(query).sort("timestamp", -1).skip(skip_count).limit(limit)
    raw_docs = await cursor.to_list(length=limit)

    events = []
    for d in raw_docs:
        events.append({
            "event_id": d.get("event_id"),
            "timestamp": d.get("timestamp"),
            "actor_user_id": d.get("actor_user_id"),
            "actor_role": d.get("actor_role"),
            "action_type": d.get("action_type"),
            "action_label": d.get("action_label"),
            "case_id": d.get("case_id"),
            "details": d.get("details", ""),
            "status": d.get("status", "success"),
            "metadata": d.get("metadata", {})
        })

    total_pages = max(1, (total_count + limit - 1) // limit)

    return {
        "events": events,
        "total_count": total_count,
        "page": page,
        "limit": limit,
        "total_pages": total_pages
    }


async def compute_audit_summary(
    investigator_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Computes factual summary counts directly from the recorded audit events collection.
    """
    col = get_collection("audit_events")
    query: Dict[str, Any] = {}

    if investigator_id and investigator_id.strip():
        norm_id = investigator_id.strip().lower()
        if norm_id != "all":
            query["actor_user_id"] = norm_id

    date_filter: Dict[str, str] = {}
    if start_date and start_date.strip():
        date_filter["$gte"] = start_date.strip()
    if end_date and end_date.strip():
        date_filter["$lte"] = end_date.strip()
    if date_filter:
        query["timestamp"] = date_filter

    total_activities = await col.count_documents(query)

    # Count specific action categories
    q_create = dict(query, action_type="investigation_created")
    investigations_created = await col.count_documents(q_create)

    q_upload = dict(query, action_type="evidence_uploaded")
    evidence_uploaded = await col.count_documents(q_upload)

    q_analysis = dict(query, action_type="analysis_completed")
    analysis_runs = await col.count_documents(q_analysis)

    q_report = dict(query, action_type="report_downloaded")
    reports_downloaded = await col.count_documents(q_report)

    q_account = dict(query, action_type={"$in": ["user_created", "user_updated", "password_reset", "investigation_reassigned"]})
    account_changes = await col.count_documents(q_account)

    q_failed = dict(query, status="failure")
    failed_operations = await col.count_documents(q_failed)

    return {
        "total_activities": total_activities,
        "investigations_created": investigations_created,
        "evidence_uploaded": evidence_uploaded,
        "analysis_runs": analysis_runs,
        "reports_downloaded": reports_downloaded,
        "account_changes": account_changes,
        "failed_operations": failed_operations,
        "period_start": start_date,
        "period_end": end_date,
        "investigator_id": investigator_id or "all"
    }


def generate_audit_pdf_report(
    summary: Dict[str, Any],
    events: List[Dict[str, Any]],
    investigator_info: Optional[Dict[str, Any]] = None,
    filter_label: str = "All Time"
) -> io.BytesIO:
    """
    Generates a readable, formal PDF audit report using ReportLab with the project's
    Pure White + Shiny Royal Red visual identity.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        "AuditTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=COLOR_BRAND
    )
    subtitle_style = ParagraphStyle(
        "AuditSubtitle",
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT_MUTED
    )
    h2_style = ParagraphStyle(
        "AuditH2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=COLOR_BRAND_DEEP,
        spaceBefore=10,
        spaceAfter=4
    )
    body_style = ParagraphStyle(
        "AuditBody",
        fontName="Helvetica",
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT_MAIN
    )
    bold_style = ParagraphStyle(
        "AuditBold",
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=11,
        textColor=COLOR_TEXT_MAIN
    )
    mono_style = ParagraphStyle(
        "AuditMono",
        fontName="Courier",
        fontSize=7,
        leading=9,
        textColor=COLOR_TEXT_MUTED
    )
    th_style = ParagraphStyle(
        "AuditTH",
        fontName="Helvetica-Bold",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )
    td_style = ParagraphStyle(
        "AuditTD",
        fontName="Helvetica",
        fontSize=7,
        leading=9,
        textColor=COLOR_TEXT_MAIN
    )
    td_bold = ParagraphStyle(
        "AuditTDBold",
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=9,
        textColor=COLOR_TEXT_MAIN
    )

    story = []

    # Title & Header
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph("AI CYBER INVESTIGATION ASSISTANT", title_style))
    story.append(Paragraph(f"OFFICIAL INVESTIGATOR ACTIVITY AUDIT REPORT &bull; GENERATED: {gen_time}", subtitle_style))
    story.append(Spacer(1, 10))

    # Top Scope Banner Table
    scope_target = "All Investigators (Organisation-wide)"
    if investigator_info:
        status_label = "Active" if investigator_info.get("is_active", True) else "Disabled"
        role_label = investigator_info.get("role", "investigator").capitalize()
        scope_target = f"{investigator_info.get('display_name', investigator_info['user_id'])} (@{investigator_info['user_id']}) &bull; {role_label} &bull; Status: {status_label}"

    scope_data = [
        [
            Paragraph("<b>Target Scope:</b>", bold_style),
            Paragraph(scope_target, body_style),
            Paragraph("<b>Reporting Period:</b>", bold_style),
            Paragraph(filter_label, body_style)
        ],
        [
            Paragraph("<b>Report ID:</b>", bold_style),
            Paragraph(f"AUD-RPT-{int(datetime.now().timestamp())}", mono_style),
            Paragraph("<b>Total Logged Events:</b>", bold_style),
            Paragraph(str(summary.get("total_activities", 0)), bold_style)
        ]
    ]

    scope_table = Table(scope_data, colWidths=[90, 200, 95, 155])
    scope_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BRAND_SOFT),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor("#FECDD3")),
        ('INNERGRID', (0, 0), (-1, -1), 0.4, colors.HexColor("#FECDD3")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(scope_table)
    story.append(Spacer(1, 12))

    # Summary Metrics Cards
    story.append(Paragraph("1. Activity Summary Overview", h2_style))
    story.append(Paragraph("Counts calculated directly from server-verified cryptographic audit records.", subtitle_style))
    story.append(Spacer(1, 6))

    metrics_data = [
        [
            Paragraph("<b>Total Activities</b>", th_style),
            Paragraph("<b>Investigations Created</b>", th_style),
            Paragraph("<b>Evidence Files Uploaded</b>", th_style),
            Paragraph("<b>Analysis Runs</b>", th_style),
            Paragraph("<b>Reports Downloaded</b>", th_style),
            Paragraph("<b>Account & Access Changes</b>", th_style),
        ],
        [
            Paragraph(f"<font size='13'><b>{summary.get('total_activities', 0)}</b></font>", td_bold),
            Paragraph(f"<font size='13'><b>{summary.get('investigations_created', 0)}</b></font>", td_bold),
            Paragraph(f"<font size='13' color='#C8102E'><b>{summary.get('evidence_uploaded', 0)}</b></font>", td_bold),
            Paragraph(f"<font size='13'><b>{summary.get('analysis_runs', 0)}</b></font>", td_bold),
            Paragraph(f"<font size='13'><b>{summary.get('reports_downloaded', 0)}</b></font>", td_bold),
            Paragraph(f"<font size='13'><b>{summary.get('account_changes', 0)}</b></font>", td_bold),
        ]
    ]

    metrics_table = Table(metrics_data, colWidths=[90, 90, 90, 90, 90, 90])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_BRAND),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ('BACKGROUND', (0, 1), (-1, 1), COLOR_BG_SUBTLE),
        ('TOPPADDING', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 8),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # Chronological Activity History
    story.append(Paragraph(f"2. Chronological Activity Log ({len(events)} events shown)", h2_style))
    story.append(Paragraph("Complete chronological sequence of authenticated actions in reverse chronological order.", subtitle_style))
    story.append(Spacer(1, 6))

    if not events:
        story.append(Paragraph("<i>No audit events recorded for the specified criteria and time range.</i>", body_style))
    else:
        table_rows = [
            [
                Paragraph("<b>Timestamp (UTC)</b>", th_style),
                Paragraph("<b>Actor</b>", th_style),
                Paragraph("<b>Action</b>", th_style),
                Paragraph("<b>Investigation ID</b>", th_style),
                Paragraph("<b>Details</b>", th_style),
                Paragraph("<b>Result</b>", th_style),
            ]
        ]

        for ev in events:
            # Parse timestamp to clean format
            ts_str = ev.get("timestamp", "")
            try:
                dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                formatted_ts = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_ts = ts_str[:19]

            status_color = "#059669" if ev.get("status") == "success" else "#DC2626"
            status_text = "SUCCESS" if ev.get("status") == "success" else "FAILED"

            table_rows.append([
                Paragraph(formatted_ts, mono_style),
                Paragraph(f"<b>@{ev.get('actor_user_id', 'unknown')}</b><br/><font color='#6B7280' size='6'>({ev.get('actor_role', '')})</font>", td_style),
                Paragraph(f"<b>{ev.get('action_label', ev.get('action_type', 'Action'))}</b>", td_style),
                Paragraph(ev.get("case_id") or "—", mono_style),
                Paragraph(ev.get("details", "") or "—", td_style),
                Paragraph(f"<font color='{status_color}'><b>{status_text}</b></font>", td_bold),
            ])

        events_table = Table(table_rows, colWidths=[80, 65, 95, 80, 175, 45], repeatRows=1)
        events_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), COLOR_BRAND),
            ('GRID', (0, 0), (-1, -1), 0.4, COLOR_BORDER),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, COLOR_BG_SUBTLE]),
        ]))
        story.append(events_table)

    story.append(Spacer(1, 16))

    # Audit & Compliance Disclaimer Box
    notice_text = (
        "<b>DATA INTEGRITY & ACCOUNTABILITY NOTICE:</b> This document contains server-recorded audit events "
        "derived strictly from authenticated server-side sessions. All operations are logged in real-time "
        "with immutable timestamps. Passwords, session tokens, and confidential evidence payloads are excluded "
        "by policy. This report reflects recorded actions only; activities conducted outside this application "
        "or prior to audit logging initialization are not represented."
    )
    notice_p = Paragraph(notice_text, ParagraphStyle("NoticeStyle", fontName="Helvetica", fontSize=6.5, leading=9, textColor=COLOR_TEXT_MUTED))
    notice_box = Table([[notice_p]], colWidths=[540])
    notice_box.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_SUBTLE),
        ('BOX', (0, 0), (-1, -1), 0.6, COLOR_BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether(notice_box))

    doc.build(story, canvasmaker=AuditReportNumberedCanvas)
    buffer.seek(0)
    return buffer
