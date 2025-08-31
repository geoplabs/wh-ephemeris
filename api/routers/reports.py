from fastapi import APIRouter, HTTPException
import uuid

from ..schemas import ComputeRequest, ReportCreateResponse, ReportStatusResponse
from ..report_queue import queue, reports

router = APIRouter(prefix="/v1/reports", tags=["reports"])

@router.post("", response_model=ReportCreateResponse)
def create_report(req: ComputeRequest):
    report_id = f"rpt_{uuid.uuid4().hex[:24]}"
    reports[report_id] = {"status": "queued", "file": None}
    queue.put((report_id, req.model_dump()))
    return {"id": report_id, "status": "queued"}

@router.get("/{report_id}", response_model=ReportStatusResponse)
def get_report(report_id: str):
    info = reports.get(report_id)
    if not info:
        raise HTTPException(status_code=404, detail="not found")
    data = {"id": report_id, "status": info["status"]}
    if info["status"] == "done" and info.get("file"):
        data["download_url"] = f"/dev-assets/{info['file']}"
    return data
