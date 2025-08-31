"""Background worker that renders PDF reports.

This worker pulls report jobs from the in-memory queue defined in
``api.report_queue``.  For each job it computes the chart data using the
existing ``/v1/charts/compute`` logic, renders a PDF with Jinja2 and
WeasyPrint, stores the result and marks the job as completed.

Dev environment:  PDFs are written to
``/app/data/dev-assets/reports/{report_id}.pdf`` so they can be served by the
FastAPI app for inspection.

Prod environment:  PDFs are uploaded to the S3 bucket specified by
``S3_BUCKET`` (default ``wh-reports``).  A ``s3://`` URL is stored in the
job information.
"""

from __future__ import annotations

import os
from pathlib import Path
from queue import Empty
from typing import Any, Dict

import boto3
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from api.report_queue import queue, reports
from api.schemas import ComputeRequest
from api.routers import charts as charts_router


# Determine environment and important paths
APP_ENV = os.getenv("APP_ENV", "dev")
DEV_REPORTS_DIR = Path("/app/data/dev-assets/reports")
TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"

# Prepare Jinja2 environment once at startup
env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(),
)
template = env.get_template("report.html")


def _store_pdf(report_id: str, pdf_bytes: bytes) -> str:
    """Store the PDF according to the environment.

    Returns the file path or URL recorded for the report.
    """

    if APP_ENV == "prod":
        bucket = os.getenv("S3_BUCKET", "wh-reports")
        # Support LocalStack via either S3_ENDPOINT or AWS_ENDPOINT_URL
        endpoint = os.getenv("S3_ENDPOINT") or os.getenv("AWS_ENDPOINT_URL")
        s3 = boto3.client("s3", endpoint_url=endpoint) if endpoint else boto3.client("s3")
        key = f"reports/{report_id}.pdf"
        s3.put_object(Bucket=bucket, Key=key, Body=pdf_bytes, ContentType="application/pdf")
        return f"s3://{bucket}/{key}"

    # Dev: save under data/dev-assets/reports
    DEV_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_path = DEV_REPORTS_DIR / f"{report_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)
    return f"reports/{report_id}.pdf"


def process_job(report_id: str, payload: Dict[str, Any]) -> None:
    """Render a single report job."""

    reports[report_id]["status"] = "processing"
    try:
        chart = charts_router.compute_chart(ComputeRequest(**payload))
        html = template.render(chart=chart)
        pdf_bytes = HTML(string=html).write_pdf()
        file_ref = _store_pdf(report_id, pdf_bytes)
        reports[report_id]["status"] = "done"
        reports[report_id]["file"] = file_ref
    except Exception:
        # In a real worker we'd log the exception details
        reports[report_id]["status"] = "error"
    finally:
        queue.task_done()


def main() -> None:
    """Main worker loop."""

    print("[worker] starting report worker loop...", flush=True)
    try:
        while True:
            try:
                report_id, payload = queue.get(timeout=5)
            except Empty:
                # No job - provide a heartbeat so container logs show liveness
                print("[worker] heartbeat", flush=True)
                continue
            process_job(report_id, payload)
    except KeyboardInterrupt:
        print("[worker] stopping.", flush=True)


if __name__ == "__main__":
    main()

