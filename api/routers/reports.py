"""Endpoints for report generation and status retrieval."""

from fastapi import APIRouter, HTTPException, Request, Body

from ..schemas import ReportCreateRequest, ReportStatus
from ..services.job_store import STORE
from ..services.inproc_queue import Q


router = APIRouter(prefix="/v1/reports", tags=["reports"])


def _rate_limit_ok(request: Request) -> bool:
    """Simple per-process rate limiter (10/min per IP)."""

    ip = request.client.host if request.client else "unknown"
    k = ("_rl", ip)
    bucket = request.app.state.__dict__.setdefault("rate", {})
    import time

    now = time.time()
    win = 60

    # Purge old timestamps
    if k in bucket:
        bucket[k] = [t for t in bucket[k] if now - t < win]
    else:
        bucket[k] = []

    if len(bucket[k]) >= 10:
        # reset bucket after rejecting to avoid lingering state in tests
        bucket[k] = []
        return False

    bucket[k].append(now)
    return True


@router.post("", response_model=ReportStatus, status_code=202)
def create_report(
    request: Request,
    req: ReportCreateRequest = Body(
        ...,
        example={
            "product": "western_natal_pdf",
            "chart_input": {
                "system": "western",
                "date": "1990-08-18",
                "time": "14:32:00",
                "time_known": True,
                "place": {"lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata"},
            },
        },
    ),
) -> ReportStatus:
    """Enqueue a PDF report for rendering."""

    if not _rate_limit_ok(request):
        raise HTTPException(status_code=429, detail="RATE_LIMIT")

    allowed = {
        "western_natal_pdf",
        "advanced_natal_pdf",
        "transit_forecast_pdf",
        "yearly_forecast_pdf",
        "monthly_horoscope_pdf",
        "compatibility_pdf",
        "remedies_pdf",
        "spiritual_mission_pdf",
    }
    if req.product not in allowed:
        raise HTTPException(status_code=400, detail="UNKNOWN_PRODUCT")

    rid = STORE.create(payload=req.model_dump(), idempotency_key=req.idempotency_key)
    Q.put(rid)
    return ReportStatus(report_id=rid, status="queued")


@router.get("/{rid}", response_model=ReportStatus)
def get_report(rid: str, request: Request) -> ReportStatus:
    job = STORE.get(rid)
    if not job:
        raise HTTPException(status_code=404, detail="NOT_FOUND")

    url = None
    if job["status"] == "done" and job.get("file_path"):
        # Dev file served at /dev-assets/reports/{rid}.pdf
        url = f"/dev-assets/reports/{rid}.pdf"

    return ReportStatus(
        report_id=rid,
        status=job["status"],
        download_url=url,
        error=job.get("error"),
    )

