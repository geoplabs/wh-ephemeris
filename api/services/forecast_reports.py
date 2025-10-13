"""Utilities for generating PDF reports for forecast endpoints."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import hashlib
import re

from zoneinfo import ZoneInfo

from ..schemas import ComputeRequest
from .pdf_renderer import render_western_natal_pdf

DEV_REPORTS_DIR = Path(os.getenv("HOME", "/opt/app")) / "data" / "dev-assets" / "reports"
DEV_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)


SUPPORTIVE = {"trine", "sextile"}
CHALLENGING = {"square", "opposition"}


@dataclass
class ForecastSection:
    """Structure describing a section in the PDF template."""

    index: int
    title: str
    entries: List[Dict[str, str]]
    fallback: str


def _safe_segment(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    if cleaned:
        return f"{cleaned[:48]}-{digest}"
    return digest


def _owner_segment(chart_input: Dict[str, Any], options: Dict[str, Any]) -> Optional[str]:
    chart_opts = chart_input.get("options") or {}
    for key in ("user_id", "profile_id", "account_id", "profile_key"):
        candidate = options.get(key) or chart_opts.get(key)
        if candidate:
            return _safe_segment(str(candidate))
    return None


def _should_use_s3() -> bool:
    flag = (os.getenv("REPORTS_USE_S3") or "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    app_env = (os.getenv("APP_ENV") or "").lower()
    return app_env in {"prod", "production", "staging", "preview"}


def _s3_bucket() -> Optional[str]:
    bucket = os.getenv("S3_BUCKET")
    if bucket:
        return bucket
    return None


def _report_storage_key(report_id: str, owner_segment: Optional[str]) -> str:
    prefix = (os.getenv("REPORTS_S3_PREFIX") or "reports").strip("/")
    base = f"{owner_segment}/{report_id}.pdf" if owner_segment else f"{report_id}.pdf"
    if prefix:
        return f"{prefix}/{base}"
    return base


@lru_cache(maxsize=1)
def _get_s3_client():  # pragma: no cover - exercised via integration tests
    if not _should_use_s3():
        return None
    bucket = _s3_bucket()
    if not bucket:
        logger.warning("report_s3_bucket_missing")
        return None
    try:  # Lazy import to keep optional dependency light for tests
        import boto3
        from botocore.config import Config
    except Exception:  # pragma: no cover - boto3 unavailable
        logger.exception("report_s3_import_failed")
        return None

    region = os.getenv("AWS_REGION", "us-east-1")
    endpoint = os.getenv("AWS_ENDPOINT_URL") or os.getenv("S3_ENDPOINT_URL")
    signature = os.getenv("AWS_S3_SIGNATURE_VERSION", "s3v4")

    session = boto3.session.Session()
    kwargs: Dict[str, Any] = {"region_name": region, "config": Config(signature_version=signature)}
    if endpoint:
        kwargs["endpoint_url"] = endpoint

    access = os.getenv("AWS_ACCESS_KEY_ID")
    secret = os.getenv("AWS_SECRET_ACCESS_KEY")
    token = os.getenv("AWS_SESSION_TOKEN")
    if access and secret:
        kwargs["aws_access_key_id"] = access
        kwargs["aws_secret_access_key"] = secret
    if token:
        kwargs["aws_session_token"] = token

    return session.client("s3", **kwargs)


def _upload_to_s3(local_path: Path, storage_key: str) -> bool:
    client = _get_s3_client()
    bucket = _s3_bucket()
    if not client or not bucket:
        return False
    try:
        client.upload_file(
            str(local_path),
            bucket,
            storage_key,
            ExtraArgs={"ContentType": "application/pdf", "ACL": os.getenv("REPORTS_S3_ACL", "private")},
        )
        return True
    except Exception:
        logger.exception("report_upload_failed", extra={"key": storage_key})
        return False


def _resolve_download_url(
    report_id: str, owner_segment: Optional[str], storage_key: Optional[str] = None
) -> str:
    """Return the public download URL for a generated report.

    Preference is given to the explicitly configured ``REPORTS_BASE_URL`` so that
    operators can point links at either the API host or a dedicated CDN without code
    changes. When that variable is not set we fall back to presigned S3 URLs (if
    available) or to environment-specific defaults.
    """
    key = storage_key or _report_storage_key(report_id, owner_segment)

    base_url = os.getenv("REPORTS_BASE_URL")
    if base_url:
        return f"{base_url.rstrip('/')}/{key}"

    client = _get_s3_client()
    bucket = _s3_bucket()
    if storage_key and client and bucket:
        try:
            ttl = int(os.getenv("REPORTS_PRESIGNED_TTL", "86400"))
        except ValueError:
            ttl = 86400
        try:
            return client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": storage_key},
                ExpiresIn=ttl,
            )
        except Exception:
            logger.exception("report_presign_failed", extra={"key": storage_key})

    app_env = (os.getenv("APP_ENV") or "").lower()
    if app_env in {"prod", "production", "staging", "preview"}:
        return f"https://api.whathoroscope.com/dev-assets/{key}"

    return f"/dev-assets/{key}"


def _ensure_storage_path(report_id: str, owner_segment: Optional[str]) -> Path:
    base_dir = Path(os.getenv("REPORTS_STORAGE_DIR", str(DEV_REPORTS_DIR)))
    if owner_segment:
        base_dir = base_dir / owner_segment
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / f"{report_id}.pdf"


def _tz_now(tz_name: str) -> datetime:
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.utcnow()


def _format_date(date_str: str, tz_name: str) -> str:
    try:
        dt = datetime.fromisoformat(date_str)
    except ValueError:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
    local = dt
    try:
        local = datetime(dt.year, dt.month, dt.day, tzinfo=ZoneInfo("UTC")).astimezone(
            ZoneInfo(tz_name)
        )
    except Exception:
        pass
    return local.strftime("%b %d")


def _month_label(month_key: str) -> str:
    dt = datetime.strptime(month_key + "-01", "%Y-%m-%d")
    return dt.strftime("%B")


def _shorten_note(note: str) -> str:
    if not note:
        return "Meaningful celestial movement invites mindful engagement."
    first_sentence = note.split(". ")[0].strip()
    if not first_sentence.endswith("."):
        first_sentence += "."
    return first_sentence


def _severity_from_score(score: float) -> str:
    if score >= 8.5:
        return "major"
    if score >= 7.0:
        return "strong"
    if score >= 5.0:
        return "notable"
    return "subtle"


def _classify_aspect(aspect: str) -> str:
    if aspect in SUPPORTIVE:
        return "supportive"
    if aspect in CHALLENGING:
        return "challenging"
    return "transformational"


def _event_tags(
    natal_body: str, natal_house: Optional[int], transit_body: str
) -> List[str]:
    tags: List[str] = []

    body_tags = {
        "Sun": ["career", "vitality"],
        "Moon": ["family", "emotions"],
        "Mercury": ["education", "career"],
        "Venus": ["love", "money"],
        "Mars": ["career", "health"],
        "Jupiter": ["education", "career", "spiritual"],
        "Saturn": ["career", "responsibility"],
        "Uranus": ["innovation", "travel"],
        "Neptune": ["spiritual"],
        "Pluto": ["transform"],
        "TrueNode": ["spiritual"],
        "Midheaven": ["career"],
    }
    for t in body_tags.get(natal_body, []):
        tags.append(t)

    # Include transit tone
    if transit_body in {"Jupiter", "Venus"}:
        tags.append("support")
    if transit_body in {"Saturn", "Mars"}:
        tags.append("discipline")

    if natal_house:
        if natal_house in {2, 8}:
            tags.append("money")
        if natal_house in {6}:
            tags.append("health")
        if natal_house in {7}:
            tags.append("love")
        if natal_house in {9}:
            tags.extend(["education", "travel", "spiritual"])
        if natal_house in {3}:
            tags.append("education")
        if natal_house in {4}:
            tags.extend(["family", "home"])
        if natal_house in {5}:
            tags.extend(["children", "joy"])
        if natal_house in {10}:
            tags.append("career")
        if natal_house in {12}:
            tags.append("spiritual")

    # Deduplicate while preserving order
    seen: set[str] = set()
    ordered: List[str] = []
    for item in tags:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered or ["general"]


def _prepared_name(chart_input: Dict[str, Any], options: Dict[str, Any]) -> str:
    candidate = (
        options.get("profile_name")
        or (chart_input.get("options") or {}).get("profile_name")
        or (chart_input.get("options") or {}).get("name")
    )
    if candidate:
        return str(candidate)
    return "WhatHoroscope Member"


def _overall_guidance(totals: Dict[str, int], top_events: Iterable[Dict[str, Any]]) -> str:
    support, challenge = totals.get("supportive", 0), totals.get("challenging", 0)
    if support - challenge >= 5:
        tone = "An overwhelmingly supportive year encourages confident leaps."
    elif challenge - support >= 4:
        tone = "A formative year invites resilience and steady pacing through challenges."
    else:
        tone = "A dynamically balanced year rewards mindful focus and flexibility."

    first = next(iter(top_events), None)
    if first:
        tone += f" Spotlight: {first['transit_body']} {first['aspect']} {first['natal_body']} around {first['date']}."
    return tone


def _section_entries(
    events: List[Dict[str, Any]],
    tz_name: str,
) -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for ev in events:
        entries.append(
            {
                "label": _format_date(ev["date"], tz_name),
                "summary": _shorten_note(ev.get("note")),
                "headline": f"{ev['transit_body']} {ev['aspect']} {ev['natal_body']}",
                "tone": _classify_aspect(ev["aspect"]),
                "severity": _severity_from_score(ev.get("score", 5.0)),
            }
        )
    return entries


def _build_sections(
    tagged_events: List[Dict[str, Any]], tz_name: str, totals: Dict[str, int], top_events: List[Dict[str, Any]]
) -> List[ForecastSection]:
    sections_config: List[Tuple[str, List[str], str]] = [
        (
            "Career & Finances",
            ["career", "money", "discipline"],
            "Career efforts and financial plans benefit from steady focus and strategic moves this year.",
        ),
        (
            "Love & Relationships",
            ["love", "support", "joy"],
            "Relationships deepen through empathy, communication, and shared growth moments.",
        ),
        (
            "Health & Wellness",
            ["health", "vitality"],
            "Wellness rhythms improve when balance, pacing, and mindful routines are honoured.",
        ),
        (
            "Education",
            ["education", "innovation"],
            "Learning pathways open when curiosity is paired with practical exploration.",
        ),
        (
            "Family & Children",
            ["family", "children", "home"],
            "Family bonds strengthen through consistent presence and heartfelt exchanges.",
        ),
        (
            "Property / Travel",
            ["home", "travel"],
            "Property decisions and travel plans align when intuition meets grounded planning.",
        ),
        (
            "Spiritual Growth",
            ["spiritual", "transform"],
            "Inner work flourishes through reflection, patience, and trust in timing.",
        ),
        (
            "Overall Guidance",
            ["general", "career", "love", "health", "spiritual", "money"],
            _overall_guidance(totals, top_events),
        ),
    ]

    sections: List[ForecastSection] = []
    for idx, (title, tags, fallback) in enumerate(sections_config, start=1):
        filtered = [e for e in tagged_events if any(t in e["tags"] for t in tags)]
        filtered.sort(key=lambda ev: ev.get("score", 0.0), reverse=True)
        sections.append(
            ForecastSection(
                index=idx,
                title=title,
                entries=_section_entries(filtered[:4], tz_name),
                fallback=fallback,
            )
        )
    return sections


def _prepare_tagged_events(
    payload: Dict[str, Any], chart_input: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    from ..routers.charts import compute_chart  # Local import to avoid heavy deps in tests

    chart = compute_chart(ComputeRequest(**chart_input))
    body_to_house = {b.name: b.house for b in chart.bodies}

    totals = {"supportive": 0, "challenging": 0, "transformational": 0}
    tagged: List[Dict[str, Any]] = []
    for events in payload.get("months", {}).values():
        for ev in events:
            tone = _classify_aspect(ev["aspect"])
            totals[tone] = totals.get(tone, 0) + 1
            tags = _event_tags(ev["natal_body"], body_to_house.get(ev["natal_body"]), ev["transit_body"])
            tagged.append({**ev, "tags": tags, "tone": tone})
    return tagged, totals


def build_yearly_pdf_payload(
    chart_input: Dict[str, Any], options: Dict[str, Any], payload: Dict[str, Any]
) -> Dict[str, Any]:
    tz_name = chart_input.get("place", {}).get("tz", "UTC")
    tagged_events, totals = _prepare_tagged_events(payload, chart_input)
    top_events = sorted(tagged_events, key=lambda ev: ev.get("score", 0.0), reverse=True)[:10]
    sections = _build_sections(tagged_events, tz_name, totals, top_events)

    monthly_highlights: List[Dict[str, str]] = []
    for month_key, events in sorted(payload.get("months", {}).items()):
        if not events:
            continue
        best = max(events, key=lambda ev: ev.get("score", 0.0))
        monthly_highlights.append(
            {
                "month": _month_label(month_key),
                "headline": f"{best['transit_body']} {best['aspect']} {best['natal_body']}",
                "summary": _shorten_note(best.get("note")),
            }
        )

    generated = _tz_now(tz_name)
    return {
        "year": options.get("year"),
        "prepared_for": _prepared_name(chart_input, options),
        "generated_at": generated.strftime("%d %B %Y"),
        "sections": [
            {
                "index": section.index,
                "title": section.title,
                "entries": section.entries,
                "fallback": section.fallback,
            }
            for section in sections
        ],
        "monthly_highlights": monthly_highlights,
        "meta": {
            "totals": totals,
            "top_events": top_events,
        },
    }


def build_monthly_pdf_payload(
    chart_input: Dict[str, Any], options: Dict[str, Any], payload: Dict[str, Any]
) -> Dict[str, Any]:
    tz_name = chart_input.get("place", {}).get("tz", "UTC")
    generated = _tz_now(tz_name)
    month_key = f"{options.get('year')}-{options.get('month'):02d}"
    events_sorted = sorted(payload.get("events", []), key=lambda ev: (-ev.get("score", 0.0), ev.get("date")))

    highlights = []
    for ev in events_sorted[:6]:
        highlights.append(
            {
                "date": _format_date(ev["date"], tz_name),
                "headline": f"{ev['transit_body']} {ev['aspect']} {ev['natal_body']}",
                "summary": _shorten_note(ev.get("note")),
            }
        )

    calendar: List[Dict[str, str]] = []
    for ev in sorted(payload.get("events", []), key=lambda e: e.get("date"))[:10]:
        calendar.append(
            {
                "date": _format_date(ev["date"], tz_name),
                "title": f"{ev['transit_body']} {ev['aspect']} {ev['natal_body']}",
                "tone": _classify_aspect(ev["aspect"]),
            }
        )

    return {
        "prepared_for": _prepared_name(chart_input, options),
        "generated_at": generated.strftime("%d %B %Y"),
        "month_label": _month_label(month_key),
        "year": options.get("year"),
        "highlights": highlights,
        "calendar": calendar,
    }


def generate_yearly_pdf(
    chart_input: Dict[str, Any], options: Dict[str, Any], payload: Dict[str, Any]
) -> Tuple[str, str]:
    report_id = f"yrf_{options.get('year')}_{uuid.uuid4().hex[:10]}"
    owner = _owner_segment(chart_input, options)
    out_path = _ensure_storage_path(report_id, owner)
    context = build_yearly_pdf_payload(chart_input, options, payload)
    render_western_natal_pdf(context, str(out_path), template_name="yearly_forecast.html.j2")
    storage_key = _report_storage_key(report_id, owner)
    uploaded = _upload_to_s3(out_path, storage_key)
    return report_id, _resolve_download_url(report_id, owner, storage_key if uploaded else None)


def generate_monthly_pdf(
    chart_input: Dict[str, Any], options: Dict[str, Any], payload: Dict[str, Any]
) -> Tuple[str, str]:
    report_id = f"mnf_{options.get('year')}{options.get('month'):02d}_{uuid.uuid4().hex[:8]}"
    owner = _owner_segment(chart_input, options)
    out_path = _ensure_storage_path(report_id, owner)
    context = build_monthly_pdf_payload(chart_input, options, payload)
    render_western_natal_pdf(context, str(out_path), template_name="monthly_horoscope.html.j2")
    storage_key = _report_storage_key(report_id, owner)
    uploaded = _upload_to_s3(out_path, storage_key)
    return report_id, _resolve_download_url(report_id, owner, storage_key if uploaded else None)

