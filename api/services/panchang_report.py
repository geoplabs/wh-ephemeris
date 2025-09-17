"""Synchronous Panchang PDF generation."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, Any

DEV_ASSETS_DIR = Path("/app/data/dev-assets/reports")
DEV_ASSETS_DIR.mkdir(parents=True, exist_ok=True)


def _render_pdf(viewmodel: Dict[str, Any], out_path: Path) -> None:
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib.units import cm  # type: ignore

    c = canvas.Canvas(str(out_path), pagesize=A4)
    width, height = A4

    c.setTitle("Panchang Report")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, height - 2 * cm, "Today's Panchang")

    header = viewmodel.get("header", {})
    solar = viewmodel.get("solar", {})
    lunar = viewmodel.get("lunar", {})
    tithi = viewmodel.get("tithi", {})
    nakshatra = viewmodel.get("nakshatra", {})
    locale = header.get("locale", {}) if isinstance(header, dict) else {}
    lang = locale.get("lang")
    script = locale.get("script")
    bilingual = viewmodel.get("bilingual") if isinstance(viewmodel, dict) else None

    weekday = header.get("weekday", {}) if isinstance(header, dict) else {}
    weekday_display = weekday.get("display_name") if isinstance(weekday, dict) else weekday
    weekday_en = None
    if isinstance(weekday, dict):
        weekday_en = weekday.get("aliases", {}).get("en")

    tithi_display = tithi.get("display_name") if isinstance(tithi, dict) else tithi
    tithi_aliases = tithi.get("aliases", {}) if isinstance(tithi, dict) else {}
    nak_display = nakshatra.get("display_name") if isinstance(nakshatra, dict) else nakshatra

    c.setFont("Helvetica", 10)
    c.drawString(
        2 * cm,
        height - 3 * cm,
        f"Date: {header.get('date_local')} ({weekday_display})",
    )
    if lang == "hi" and script == "deva" and weekday_en:
        c.setFont("Helvetica", 8)
        c.setFillGray(0.4)
        c.drawString(2 * cm, height - 3.3 * cm, f"English: {weekday_en}")
        c.setFillGray(0)
        c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 3.6 * cm, f"Sunrise: {solar.get('sunrise')}  Sunset: {solar.get('sunset')}")
    c.drawString(2 * cm, height - 4.2 * cm, f"Tithi: {tithi_display} ({tithi.get('number')})")
    if lang == "hi" and script == "deva" and tithi_aliases:
        c.setFont("Helvetica", 8)
        c.setFillGray(0.4)
        en_alias = tithi_aliases.get("en")
        iast_alias = tithi_aliases.get("iast")
        if en_alias or iast_alias:
            c.drawString(
                2 * cm,
                height - 4.5 * cm,
                f"English: {en_alias or ''}  IAST: {iast_alias or ''}",
            )
        c.setFillGray(0)
        c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 4.8 * cm, f"Nakshatra: {nak_display} Pada {nakshatra.get('pada')}")
    if lang == "hi" and script == "deva" and isinstance(nakshatra, dict):
        aliases = nakshatra.get("aliases", {})
        en_alias = aliases.get("en")
        if en_alias:
            c.setFont("Helvetica", 8)
            c.setFillGray(0.4)
            c.drawString(2 * cm, height - 5.1 * cm, f"English: {en_alias}")
            c.setFillGray(0)
            c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 5.4 * cm, f"Moonrise: {lunar.get('moonrise')}  Moonset: {lunar.get('moonset')}")

    if bilingual:
        c.setFont("Helvetica-Oblique", 8)
        c.setFillGray(0.4)
        c.drawString(
            2 * cm,
            height - 6.0 * cm,
            f"Bilingual helper: {bilingual.get('tithi_en', '')} / {bilingual.get('tithi_hi', '')}",
        )
        c.setFillGray(0)

    c.showPage()
    c.save()


def generate_panchang_report(viewmodel) -> Dict[str, Any]:
    rid = uuid.uuid4().hex
    out_path = DEV_ASSETS_DIR / f"{rid}.pdf"
    payload = viewmodel.model_dump() if hasattr(viewmodel, "model_dump") else viewmodel
    _render_pdf(payload, out_path)
    download_url = f"/dev-assets/reports/{rid}.pdf"
    if hasattr(viewmodel, "assets"):
        try:
            viewmodel.assets.pdf_download_url = download_url
        except Exception:
            pass
    return {
        "report_id": rid,
        "download_url": download_url,
        "status": "ready",
    }

