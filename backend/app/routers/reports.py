import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from app.database import get_collection
from app.dependencies import get_current_user, verify_case_access
from app.services.report_service import build_pdf_report
from app.services.audit_service import record_audit_event
from app.routers.analysis import get_case_dashboard, run_case_analysis

logger = logging.getLogger("investigation.reports")
router = APIRouter(prefix="/api/cases/{case_id}/report", tags=["Reports"])

@router.get("/pdf")
async def download_case_pdf(
    case_id: str,
    current_user: dict = Depends(get_current_user)
):
    case = await verify_case_access(case_id, current_user)
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")

    evidence_cursor = evidence_col.find({"case_id": case_id})
    evidence_list = await evidence_cursor.to_list(length=200)

    # Get or generate dashboard data
    dashboard_res = await get_case_dashboard(case_id, current_user)

    # Requirement 14: Data Consistency Verification
    # Ensure the PDF uses the genuine, complete analysis data matching the application.
    # If the case has evidence files in the vault, but the cached dashboard has fewer
    # analyzed documents or zero extracted entities despite files being present,
    # re-run case analysis dynamically to populate all entities, timeline, keywords, and correlations.
    ev_count = len(evidence_list)
    if ev_count > 0:
        docs_analyzed = dashboard_res.stats.documents
        key_entities = dashboard_res.stats.key_entities
        if docs_analyzed < ev_count or (key_entities == 0 and any(ev.get("extracted_text") for ev in evidence_list)):
            logger.info(f"Re-running case analysis for PDF generation to guarantee data consistency (case {case_id})...")
            try:
                dashboard_res = await run_case_analysis(case_id, current_user)
            except Exception as e:
                logger.warning(f"Dynamic analysis refresh before PDF export failed ({e}); using existing dashboard data.")

    dashboard_data = dashboard_res.model_dump()

    # Generate PDF via ReportLab
    pdf_buffer = build_pdf_report(case, evidence_list, dashboard_data)

    safe_filename = f"Investigation_Report_{case_id}.pdf"

    # Record report generation / download audit event
    await record_audit_event(
        actor_user_id=current_user["user_id"],
        actor_role=current_user.get("role", "investigator"),
        action_type="report_downloaded",
        action_label="Generated investigation report",
        case_id=case_id,
        details=f"Downloaded formal PDF investigation report for '{case_id}'",
        metadata={"filename": safe_filename},
        status="success"
    )

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        }
    )

