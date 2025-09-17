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

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 3 * cm, f"Date: {header.get('date_local')} ({header.get('weekday')})")
    c.drawString(2 * cm, height - 3.6 * cm, f"Sunrise: {solar.get('sunrise')}  Sunset: {solar.get('sunset')}")
    c.drawString(2 * cm, height - 4.2 * cm, f"Tithi: {tithi.get('name')} ({tithi.get('number')})")
    c.drawString(2 * cm, height - 4.8 * cm, f"Nakshatra: {nakshatra.get('name')} Pada {nakshatra.get('pada')}")
    c.drawString(2 * cm, height - 5.4 * cm, f"Moonrise: {lunar.get('moonrise')}  Moonset: {lunar.get('moonset')}")

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

