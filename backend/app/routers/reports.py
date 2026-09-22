from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.database import get_collection
from app.services.report_service import build_pdf_report
from app.routers.analysis import get_case_dashboard

router = APIRouter(prefix="/api/cases/{case_id}/report", tags=["Reports"])

@router.get("/pdf")
async def download_case_pdf(case_id: str):
    cases_col = get_collection("cases")
    evidence_col = get_collection("evidence")

    case = await cases_col.find_one({"case_id": case_id})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    evidence_cursor = evidence_col.find({"case_id": case_id})
    evidence_list = await evidence_cursor.to_list(length=200)

    # Get or generate dashboard data
    dashboard_res = await get_case_dashboard(case_id)
    dashboard_data = dashboard_res.model_dump()

    # Generate PDF via ReportLab
    pdf_buffer = build_pdf_report(case, evidence_list, dashboard_data)

    safe_filename = f"Investigation_Report_{case_id}.pdf"

    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"'
        }
    )
