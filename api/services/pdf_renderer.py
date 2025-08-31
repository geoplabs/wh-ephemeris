"""PDF rendering helpers for reports."""

from pathlib import Path
from typing import Dict, Any, Optional


# Attempt to import WeasyPrint. If unavailable, we'll fall back to ReportLab.
try:  # pragma: no cover - import-time optional dependency
    from weasyprint import HTML, CSS  # type: ignore

    HAVE_WEASY = True
except Exception:  # pragma: no cover - handled gracefully
    HAVE_WEASY = False


def _render_reportlab(out_path: Path, payload: Dict[str, Any]) -> None:
    """Render a minimal PDF using ReportLab."""

    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib.units import cm  # type: ignore

    c = canvas.Canvas(str(out_path), pagesize=A4)
    W, H = A4
    c.setTitle("Western Natal Report")
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, "Western Natal Report (Dev)")

    c.setFont("Helvetica", 10)
    meta = payload.get("meta", {})
    tz = payload.get("chart_input", {}).get("place", {}).get("tz", "")
    c.drawString(2 * cm, H - 3 * cm, f"System: {meta.get('zodiac','tropical')}  House: {meta.get('house_system','placidus')}")
    if tz:
        c.drawString(2 * cm, H - 3.6 * cm, f"Place tz: {tz}")

    # bodies table (first 8)
    y = H - 5 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Bodies")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    for b in payload.get("bodies", [])[:8]:
        c.drawString(
            2 * cm,
            y,
            f"{b['name']:>8}: {b['sign']}  {b.get('house') or '-'}  {b['lon']:.2f}°",
        )
        y -= 0.45 * cm

    # aspects (first 8)
    y -= 0.3 * cm
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "Aspects")
    y -= 0.5 * cm
    c.setFont("Helvetica", 10)
    for a in payload.get("aspects", [])[:8]:
        c.drawString(2 * cm, y, f"{a['p1']} {a['type']} {a['p2']} (orb {a['orb']}°)")
        y -= 0.45 * cm
        if y < 2 * cm:
            c.showPage()
            y = H - 2 * cm

    c.showPage()
    c.save()


def render_western_natal_pdf(
    payload: Dict[str, Any],
    out_path: str,
    branding: Optional[Dict[str, Any]] = None,
    template_name: str = "western_natal.html.j2",
) -> str:
    """Render a PDF to ``out_path`` using the selected template."""

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if HAVE_WEASY:
        from jinja2 import Environment, FileSystemLoader, select_autoescape
        from pathlib import Path as _P

        tpl_dir = _P(__file__).resolve().parent.parent / "templates" / "reports"
        env = Environment(
            loader=FileSystemLoader(str(tpl_dir)), autoescape=select_autoescape()
        )
        html = env.get_template(template_name).render(
            data=payload, branding=branding or {}, css_href="report.css"
        )
        # CSS path is provided for completeness; WeasyPrint will load it via base_url
        CSS_FILENAME = tpl_dir / "report.css"
        HTML(string=html, base_url=str(tpl_dir)).write_pdf(
            str(out), stylesheets=[CSS(str(CSS_FILENAME))]
        )
        return str(out)
    else:
        _render_reportlab(out, payload)
        return str(out)

