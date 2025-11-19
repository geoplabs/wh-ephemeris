"""PDF rendering helpers for reports."""

import os
from pathlib import Path
from typing import Dict, Any, Optional


# WeasyPrint is heavy and slow; enable only if USE_WEASY=true
USE_WEASY = os.getenv("USE_WEASY", "false").lower() == "true"
if USE_WEASY:  # pragma: no cover - optional dependency
    try:
        from weasyprint import HTML, CSS  # type: ignore

        HAVE_WEASY = True
    except Exception:  # pragma: no cover
        HAVE_WEASY = False
else:  # pragma: no cover - default to ReportLab
    HAVE_WEASY = False


def _render_story_yearly(out_path: Path, payload: Dict[str, Any]) -> None:
    """Render an interpreted yearly report using ReportLab fallback."""

    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    import textwrap

    report = payload.get("report") or {}
    meta = report.get("meta") or {}
    year = meta.get("year") or meta.get("target_year") or "Yearly Forecast"
    generated_at = payload.get("generated_at")

    def draw_wrapped(cvs: Any, text: str, x: float, y: float, width: float, leading: float = 12) -> float:
        cvs.setFont("Helvetica", 10)
        lines = []
        for paragraph in filter(None, (text or "").split("\n")):
            lines.extend(textwrap.wrap(paragraph, width=int(width / 5)))
            lines.append("")
        for line in lines:
            cvs.drawString(x, y, line)
            y -= leading
        return y

    c = canvas.Canvas(str(out_path), pagesize=A4)
    W, H = A4
    c.setTitle(f"{year} Story Report")

    # Cover / header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, H - 2 * cm, f"{year} Story-Level Forecast")
    profile = meta.get("profile_name") or meta.get("user_id")
    if profile:
        c.setFont("Helvetica", 12)
        c.drawString(2 * cm, H - 3 * cm, f"For: {profile}")
    if generated_at:
        c.setFont("Helvetica", 10)
        c.drawString(2 * cm, H - 3.8 * cm, f"Generated: {generated_at}")

    c.showPage()

    # Year at a glance
    yag = report.get("year_at_glance") or {}
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, "Year at a Glance")
    y = H - 3 * cm
    commentary = yag.get("commentary") or "Stay curious and steady throughout the year."
    y = draw_wrapped(c, commentary, 2 * cm, y, W - 4 * cm)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "Top Events")
    y -= 0.4 * cm
    c.setFont("Helvetica", 10)
    for ev in yag.get("top_events", [])[:6]:
        summary = ev.get("summary") or "Key turning point"
        c.drawString(2 * cm, y, f"- {ev.get('date') or ''} {ev.get('title')}: {summary}")
        y -= 0.45 * cm
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm

    # Eclipses & Lunations
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, "Eclipses & Lunations")
    y = H - 3 * cm
    for ec in report.get("eclipses_and_lunations", [])[:10]:
        c.setFont("Helvetica-Bold", 11)
        c.drawString(2 * cm, y, f"{ec.get('date')}: {ec.get('kind')}")
        y -= 0.35 * cm
        y = draw_wrapped(c, ec.get("guidance") or "Reflect and stay grounded.", 2 * cm, y, W - 4 * cm)
        y -= 0.2 * cm
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm

    # Monthly sections
    for month in report.get("months", [])[:12]:
        c.showPage()
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2 * cm, H - 2 * cm, str(month.get("month")))
        y = H - 3 * cm

        y = draw_wrapped(c, "Overview: " + (month.get("overview") or ""), 2 * cm, y, W - 4 * cm)
        y = draw_wrapped(c, "Career & Finance: " + (month.get("career_and_finance") or ""), 2 * cm, y, W - 4 * cm)
        y = draw_wrapped(c, "Relationships & Family: " + (month.get("relationships_and_family") or ""), 2 * cm, y, W - 4 * cm)
        y = draw_wrapped(c, "Health & Energy: " + (month.get("health_and_energy") or ""), 2 * cm, y, W - 4 * cm)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Planner Actions")
        y -= 0.4 * cm
        c.setFont("Helvetica", 10)
        for action in month.get("planner_actions", [])[:6]:
            c.drawString(2 * cm, y, f"• {action}")
            y -= 0.35 * cm
            if y < 3 * cm:
                c.showPage()
                y = H - 2 * cm
                c.setFont("Helvetica", 10)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "High Score Days")
        y -= 0.4 * cm
        c.setFont("Helvetica", 10)
        for ev in month.get("high_score_days", [])[:6]:
            c.drawString(2 * cm, y, f"- {ev.get('date')}: {ev.get('transit_body')} to {ev.get('natal_body')} ({ev.get('aspect')})")
            y -= 0.35 * cm
            if y < 3 * cm:
                c.showPage()
                y = H - 2 * cm
                c.setFont("Helvetica", 10)

        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, "Caution Days")
        y -= 0.4 * cm
        c.setFont("Helvetica", 10)
        for ev in month.get("caution_days", [])[:6]:
            c.drawString(2 * cm, y, f"- {ev.get('date')}: {ev.get('transit_body')} to {ev.get('natal_body')} ({ev.get('aspect')})")
            y -= 0.35 * cm
            if y < 3 * cm:
                c.showPage()
                y = H - 2 * cm
                c.setFont("Helvetica", 10)

    # Appendices
    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, "Appendix A: All Events")
    y = H - 3 * cm
    c.setFont("Helvetica", 10)
    for ev in report.get("appendix_all_events", [])[:60]:
        text = f"{ev.get('date')}: {ev.get('transit_body')} to {ev.get('natal_body')} ({ev.get('aspect')}) {ev.get('user_friendly_summary') or ''}"
        y = draw_wrapped(c, text, 2 * cm, y, W - 4 * cm, leading=11)
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm

    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, "Appendix B: Glossary")
    y = H - 3 * cm
    c.setFont("Helvetica", 10)
    for term, definition in (report.get("glossary") or {}).items():
        y = draw_wrapped(c, f"{term}: {definition}", 2 * cm, y, W - 4 * cm, leading=11)
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm

    c.showPage()
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, H - 2 * cm, "Appendix C: Interpretation Index")
    y = H - 3 * cm
    c.setFont("Helvetica", 10)
    for term, definition in (report.get("interpretation_index") or {}).items():
        y = draw_wrapped(c, f"{term}: {definition}", 2 * cm, y, W - 4 * cm, leading=11)
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm

    c.showPage()
    c.save()


def _render_reportlab(out_path: Path, payload: Dict[str, Any]) -> None:
    """Render a minimal PDF using ReportLab."""

    # If the payload already contains a structured report (story-level yearly),
    # render a more narrative PDF instead of the natal snapshot fallback.
    if "report" in payload:
        _render_story_yearly(out_path, payload)
        return

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


def render_viewmodel_pdf(
    viewmodel: dict,
    out_path: str,
    branding: Dict[str, Any] | None = None,
    template_name: str = "full_natal.html.j2",
) -> str:
    """Render a PDF from a pre-built viewmodel."""

    tpl_dir = Path(__file__).parent.parent / "templates" / "reports"
    if HAVE_WEASY:
        from jinja2 import Environment, FileSystemLoader

        env = Environment(
            loader=FileSystemLoader(str(tpl_dir)), autoescape=True, trim_blocks=True, lstrip_blocks=True
        )
        html = env.get_template(template_name).render(
            vm=viewmodel, branding=branding or {}, css_href="report.css"
        )
        out = Path(out_path)
        HTML(string=html, base_url=str(tpl_dir)).write_pdf(str(out), stylesheets=[])
        return str(out)
    else:
        from reportlab.pdfgen import canvas

        c = canvas.Canvas(out_path)
        c.setTitle("Full Natal Report")
        c.drawString(72, 800, "Full Natal Report")
        c.drawString(
            72,
            780,
            f"System: {viewmodel['header']['system']}  Zodiac: {viewmodel['header']['zodiac']}",
        )
        c.showPage()
        c.save()
        return out_path

