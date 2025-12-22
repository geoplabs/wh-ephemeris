"""Pipeline for interpreted yearly forecast report generation."""

from __future__ import annotations

import asyncio
import logging
import os
import importlib
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from .forecast_builders import yearly_payload
from .forecast_reports import _ensure_storage_path, _owner_segment, _report_storage_key, _resolve_download_url
from .pdf_renderer import render_western_natal_pdf
from .yearly_interpreter import interpret_yearly_forecast
from .yearly_qa_editor import qa_edit_yearly_report
from .yearly_pdf_enhanced import render_enhanced_yearly_pdf
from ..schemas.yearly_forecast_report import (
    YearlyForecastReport,
    YearlyForecastReportResponse,
    YearlyForecastRequest,
)

logger = logging.getLogger(__name__)


async def compute_yearly_forecast(chart_input: Dict[str, Any], options: Dict[str, Any]) -> Dict[str, Any]:
    """Compute the raw yearly forecast using the existing payload builder."""

    return await asyncio.to_thread(yearly_payload, chart_input, options)


def _custom_upload(local_path: Path, storage_key: str, s3_options: Dict[str, Any]) -> bool:
    bucket = s3_options.get("bucket")
    if not bucket:
        return False

    if not importlib.util.find_spec("boto3"):
        logger.error("yearly_report_custom_upload_import_missing")
        return False

    import boto3  # type: ignore  # pragma: no cover - optional dependency

    client = boto3.client(
        "s3",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    extra = {"ContentType": "application/pdf"}
    if s3_options.get("public"):
        extra["ACL"] = "public-read"
    try:
        client.upload_file(str(local_path), bucket, storage_key, ExtraArgs=extra)
        return True
    except Exception:
        logger.exception("yearly_report_custom_upload_failed", extra={"key": storage_key})
        return False


async def build_interpreted_yearly_report(req: YearlyForecastRequest) -> YearlyForecastReport:
    """Build interpreted yearly report with QA editing applied."""
    # Get raw forecast data
    raw = await compute_yearly_forecast(req.chart_input.model_dump(), req.options.model_dump())
    
    # Interpret with LLM
    report = await interpret_yearly_forecast(raw)
    
    # Apply QA editing to polish narratives
    logger.info("Applying QA editor to yearly forecast narratives")
    edited_report_dict = qa_edit_yearly_report(report.model_dump())
    
    # Convert back to Pydantic model
    from ..schemas.yearly_forecast_report import YearlyForecastReport as ReportModel
    return ReportModel(**edited_report_dict)


def _resolve_storage(report_id: str, chart_input: Dict[str, Any], options: Dict[str, Any]) -> tuple[Path, str]:
    owner = _owner_segment(chart_input, options)
    return _ensure_storage_path(report_id, owner), _report_storage_key(report_id, owner)


async def render_yearly_report_pdf(
    report: YearlyForecastReport, chart_input: Dict[str, Any], options: Dict[str, Any]
) -> str:
    """Render the interpreted report to PDF with enhanced formatting and return a download URL."""

    report_id = f"yrf_story_{options.get('year')}_{uuid.uuid4().hex[:8]}"
    out_path, default_key = _resolve_storage(report_id, chart_input, options)
    context = {"report": report.model_dump(), "generated_at": datetime.utcnow().isoformat()}

    # Use enhanced PDF renderer for better readability
    logger.info("Rendering enhanced yearly PDF with improved formatting")
    try:
        render_enhanced_yearly_pdf(context, str(out_path))
    except Exception as e:
        # Fallback to basic renderer if enhanced fails
        import traceback
        logger.error(f"Enhanced PDF rendering failed: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        logger.warning(f"Falling back to basic renderer")
        render_western_natal_pdf(context, str(out_path), template_name="yearly_v2.html.j2")

    outputs = options.get("outputs") or {}
    s3_options = outputs.get("s3") if isinstance(outputs, dict) else {}
    storage_key = default_key
    uploaded = False
    if s3_options:
        prefix = s3_options.get("prefix") or ""
        storage_key = f"{prefix.rstrip('/')}/{out_path.name}" if prefix else out_path.name
        uploaded = _custom_upload(out_path, storage_key, s3_options)

    if not uploaded:
        try:
            uploaded = await asyncio.to_thread(os.replace, out_path, out_path)
        except Exception:
            logger.debug("noop_replace_after_render", exc_info=True)

    base_url = options.get("base_url") if isinstance(options, dict) else None
    if uploaded and s3_options.get("public") and s3_options.get("bucket"):
        bucket = s3_options.get("bucket")
        return f"https://{bucket}.s3.amazonaws.com/{storage_key}"
    if base_url:
        return f"{base_url.rstrip('/')}/{storage_key}"
    return _resolve_download_url(report_id, _owner_segment(chart_input, options), storage_key if uploaded else None)


async def generate_yearly_forecast_with_pdf(req: YearlyForecastRequest) -> YearlyForecastReportResponse:
    report = await build_interpreted_yearly_report(req)
    pdf_url = await render_yearly_report_pdf(report, req.chart_input.model_dump(), req.options.model_dump())
    return YearlyForecastReportResponse(report=report, pdf_download_url=pdf_url)
