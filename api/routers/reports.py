import json
import hashlib
import time
from fastapi import APIRouter, HTTPException, Request

from ..schemas import (
    ReportCreateRequest,
    ReportCreateResponse,
    ReportStatus,
    ReportStatusEnum,
)
from ..report_queue import job_store
from ..report_queue import queue  # ensures worker started

router = APIRouter(prefix="/v1/reports", tags=["reports"])

RATE_LIMIT = 10  # per minute
_requests: dict = {}


def _rate_key(request: Request) -> str:
    auth = request.headers.get("authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:]
    return request.client.host if request.client else "anon"


def _check_rate_limit(key: str) -> None:
    now = time.time()
    window = 60
    timestamps = _requests.setdefault(key, [])
    timestamps[:] = [t for t in timestamps if now - t < window]
    if len(timestamps) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="rate limit exceeded")
    timestamps.append(now)


@router.post("", response_model=ReportCreateResponse, status_code=202)
async def create_report(req: ReportCreateRequest, request: Request):
    _check_rate_limit(_rate_key(request))
    fingerprint = hashlib.sha256(
        json.dumps(req.chart_input.model_dump(), sort_keys=True).encode()
    ).hexdigest()
    rid, job, _ = job_store.create_job(req, fingerprint)
    return ReportCreateResponse(
        report_id=rid,
        status=job["status"],
        queued_at=job["queued_at"],
    )


@router.get("/{report_id}", response_model=ReportStatus)
async def get_report(report_id: str):
    job = job_store.jobs.get(report_id)
    if not job:
        raise HTTPException(status_code=404, detail="not found")
    download_url = None
    if job["status"] == ReportStatusEnum.done and job.get("file_path"):
        download_url = f"/dev-assets/reports/{job['file_path']}"
    return ReportStatus(
        report_id=report_id,
        status=job["status"],
        download_url=download_url,
        expires_at=None,
        error=job.get("error"),
    )
