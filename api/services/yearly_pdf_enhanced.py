"""Enhanced PDF renderer for yearly forecast reports with improved UX/readability."""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Color palette (RGB tuples)
COLORS = {
    'primary': (0.2, 0.3, 0.5),  # Deep blue
    'secondary': (0.4, 0.5, 0.6),  # Slate gray
    'accent': (0.6, 0.4, 0.5),  # Muted purple
    'success': (0.2, 0.6, 0.4),  # Green
    'warning': (0.9, 0.6, 0.2),  # Orange
    'text_dark': (0.1, 0.1, 0.1),  # Almost black
    'text_light': (0.4, 0.4, 0.4),  # Gray
    'background': (0.98, 0.98, 0.98),  # Off-white
    'divider': (0.85, 0.85, 0.85),  # Light gray
}


def render_enhanced_yearly_pdf(payload: Dict[str, Any], out_path: str) -> str:
    """Render an enhanced, user-friendly yearly forecast PDF.
    
    Args:
        payload: Report data with 'report' and 'generated_at' keys
        out_path: Output file path
        
    Returns:
        Path to generated PDF
    """
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.pdfgen import canvas  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    from reportlab.lib import colors  # type: ignore
    
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    report = payload.get('report', {})
    meta = report.get('meta', {})
    year = meta.get('year') or datetime.now().year
    generated_at = payload.get('generated_at', '')
    
    c = canvas.Canvas(str(path), pagesize=A4)
    W, H = A4
    c.setTitle(f"{year} Yearly Forecast")
    
    # Render all sections
    _render_cover_page(c, W, H, year, meta, generated_at)
    _render_year_at_glance(c, W, H, report.get('year_at_glance', {}))
    _render_eclipses(c, W, H, report.get('eclipses_and_lunations', []))
    
    for month in report.get('months', [])[:12]:
        _render_monthly_section(c, W, H, month, year)
    
    _render_appendices(c, W, H, report)
    
    c.save()
    logger.info(f"Enhanced PDF generated: {path}")
    return str(path)


def _render_cover_page(c: Any, W: float, H: float, year: int, meta: Dict, generated_at: str) -> None:
    """Render elegant cover page."""
    # Background color block
    c.setFillColorRGB(*COLORS['primary'])
    c.rect(0, H - 8 * cm, W, 8 * cm, fill=True, stroke=False)
    
    # Title
    c.setFillColorRGB(1, 1, 1)  # White
    c.setFont("Helvetica-Bold", 36)
    c.drawCentredString(W / 2, H - 4 * cm, f"{year}")
    
    c.setFont("Helvetica", 20)
    c.drawCentredString(W / 2, H - 5 * cm, "Yearly Forecast")
    
    # Profile info
    profile = meta.get('profile_name') or meta.get('user_id')
    if profile:
        c.setFillColorRGB(*COLORS['text_dark'])
        c.setFont("Helvetica", 14)
        c.drawCentredString(W / 2, H - 10 * cm, f"For: {profile}")
    
    # Generation timestamp
    if generated_at:
        c.setFillColorRGB(*COLORS['text_light'])
        c.setFont("Helvetica", 9)
        c.drawCentredString(W / 2, 2 * cm, f"Generated: {generated_at}")
    
    c.showPage()


def _render_year_at_glance(c: Any, W: float, H: float, yag: Dict[str, Any]) -> None:
    """Render year-at-a-glance section with heatmap and commentary."""
    y = H - 2 * cm
    
    # Section header with colored background
    c.setFillColorRGB(*COLORS['primary'])
    c.rect(1.5 * cm, y - 0.8 * cm, W - 3 * cm, 1 * cm, fill=True, stroke=False)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, y - 0.5 * cm, "Year at a Glance")
    
    y -= 2 * cm
    
    # Commentary
    c.setFillColorRGB(*COLORS['text_dark'])
    commentary = yag.get('commentary', '')
    if commentary:
        y = _draw_wrapped_text(
            c,
            commentary,
            2 * cm,
            y,
            W - 4 * cm,
            font_size=11,
            leading=14,
            color=COLORS['text_dark']
        )
        y -= 0.5 * cm
    
    # Top events
    _draw_section_divider(c, y, W)
    y -= 0.8 * cm
    
    c.setFillColorRGB(*COLORS['secondary'])
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2 * cm, y, "⭐ Top Events")
    y -= 0.6 * cm
    
    for i, ev in enumerate(yag.get('top_events', [])[:8], 1):
        if y < 4 * cm:
            c.showPage()
            y = H - 2 * cm
        
        date = ev.get('date', '')
        title = ev.get('title', '')
        score = ev.get('score', 0)
        
        # Color code by score
        if score > 15:
            color = COLORS['warning']
        elif score < -5:
            color = COLORS['success']
        else:
            color = COLORS['text_dark']
        
        c.setFillColorRGB(*color)
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2.5 * cm, y, f"{i}. {date}")
        
        c.setFillColorRGB(*COLORS['text_dark'])
        c.setFont("Helvetica", 10)
        summary = ev.get('summary', '')[:100]
        c.drawString(5 * cm, y, f"{title}: {summary}")
        
        y -= 0.5 * cm
    
    c.showPage()


def _render_eclipses(c: Any, W: float, H: float, eclipses: List[Dict[str, Any]]) -> None:
    """Render eclipses and lunations section."""
    if not eclipses:
        return
    
    y = H - 2 * cm
    
    # Section header
    c.setFillColorRGB(*COLORS['accent'])
    c.rect(1.5 * cm, y - 0.8 * cm, W - 3 * cm, 1 * cm, fill=True, stroke=False)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, y - 0.5 * cm, "🌙 Eclipses & Lunations")
    
    y -= 2 * cm
    
    for eclipse in eclipses[:10]:
        if y < 5 * cm:
            c.showPage()
            y = H - 2 * cm
        
        date = eclipse.get('date', '')
        kind = eclipse.get('kind', '')
        guidance = eclipse.get('guidance', '')
        
        # Eclipse header
        c.setFillColorRGB(*COLORS['accent'])
        c.setFont("Helvetica-Bold", 12)
        c.drawString(2 * cm, y, f"{date} — {kind}")
        y -= 0.5 * cm
        
        # Guidance
        c.setFillColorRGB(*COLORS['text_dark'])
        y = _draw_wrapped_text(
            c,
            guidance,
            2.5 * cm,
            y,
            W - 5 * cm,
            font_size=10,
            leading=12
        )
        y -= 0.8 * cm
    
    c.showPage()


def _render_monthly_section(c: Any, W: float, H: float, month: Dict[str, Any], year: int) -> None:
    """Render a monthly section with enhanced typography."""
    month_name = month.get('month', '')
    
    y = H - 1.5 * cm
    
    # Month header with gradient effect
    c.setFillColorRGB(*COLORS['primary'])
    c.rect(0, y - 1.2 * cm, W, 1.5 * cm, fill=True, stroke=False)
    
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(2 * cm, y - 0.7 * cm, month_name)
    
    y -= 2.5 * cm
    
    # Overview section
    _render_subsection(c, W, y, "Overview", month.get('overview', ''), 'primary')
    y -= _calculate_text_height(month.get('overview', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Career & Finance
    _render_subsection(c, W, y, "💼 Career & Finance", month.get('career_and_finance', ''), 'secondary')
    y -= _calculate_text_height(month.get('career_and_finance', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Relationships
    _render_subsection(c, W, y, "❤️ Relationships & Family", month.get('relationships_and_family', ''), 'secondary')
    y -= _calculate_text_height(month.get('relationships_and_family', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Health
    _render_subsection(c, W, y, "🌱 Health & Energy", month.get('health_and_energy', ''), 'secondary')
    y -= _calculate_text_height(month.get('health_and_energy', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 8 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Planner Actions (boxed)
    _render_planner_actions(c, W, y, month.get('planner_actions', []))
    y -= (len(month.get('planner_actions', [])) * 0.5 + 1.5) * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # High/Caution Days (side by side)
    _render_day_highlights(c, W, y, month.get('high_score_days', []), month.get('caution_days', []))
    
    c.showPage()


def _render_subsection(c: Any, W: float, y: float, title: str, text: str, color_key: str) -> None:
    """Render a subsection with colored header."""
    c.setFillColorRGB(*COLORS[color_key])
    c.setFont("Helvetica-Bold", 13)
    c.drawString(2 * cm, y, title)
    
    y -= 0.6 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    _draw_wrapped_text(c, text, 2 * cm, y, W - 4 * cm, font_size=10, leading=12)


def _render_planner_actions(c: Any, W: float, y: float, actions: List[str]) -> None:
    """Render planner actions in a styled box."""
    if not actions:
        return
    
    box_height = len(actions) * 0.5 * cm + 1 * cm
    
    # Box background
    c.setFillColorRGB(*COLORS['background'])
    c.setStrokeColorRGB(*COLORS['divider'])
    c.roundRect(1.8 * cm, y - box_height, W - 3.6 * cm, box_height, 0.2 * cm, fill=True, stroke=True)
    
    # Title
    c.setFillColorRGB(*COLORS['primary'])
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2.2 * cm, y - 0.6 * cm, "✓ Action Plan")
    
    # Actions
    y -= 1.2 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 10)
    
    for action in actions[:8]:
        c.drawString(2.5 * cm, y, f"• {action}")
        y -= 0.5 * cm


def _render_day_highlights(c: Any, W: float, y: float, high_days: List[Dict], caution_days: List[Dict]) -> None:
    """Render high score and caution days side by side."""
    col_width = (W - 5 * cm) / 2
    
    # High Score Days (left column)
    c.setFillColorRGB(*COLORS['success'])
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, "✨ High Energy Days")
    
    y_left = y - 0.5 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 9)
    
    for day in high_days[:6]:
        date = day.get('date', '')
        transit = day.get('transit_body', '')
        natal = day.get('natal_body', '')
        c.drawString(2 * cm, y_left, f"{date}: {transit}→{natal}")
        y_left -= 0.4 * cm
    
    # Caution Days (right column)
    y_right = y
    c.setFillColorRGB(*COLORS['warning'])
    c.setFont("Helvetica-Bold", 11)
    c.drawString(W / 2 + 0.5 * cm, y_right, "⚠️ Navigate With Care")
    
    y_right -= 0.5 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 9)
    
    for day in caution_days[:6]:
        date = day.get('date', '')
        transit = day.get('transit_body', '')
        natal = day.get('natal_body', '')
        c.drawString(W / 2 + 0.5 * cm, y_right, f"{date}: {transit}→{natal}")
        y_right -= 0.4 * cm


def _render_appendices(c: Any, W: float, H: float, report: Dict[str, Any]) -> None:
    """Render appendices with clean formatting."""
    # Glossary
    y = H - 2 * cm
    c.setFillColorRGB(*COLORS['secondary'])
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "📖 Glossary")
    
    y -= 1 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 10)
    
    for term, definition in (report.get('glossary', {})).items():
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm
        
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, f"{term}:")
        y -= 0.4 * cm
        
        c.setFont("Helvetica", 10)
        y = _draw_wrapped_text(c, definition, 2.5 * cm, y, W - 5 * cm, 10, 12)
        y -= 0.6 * cm
    
    c.showPage()


def _draw_section_divider(c: Any, y: float, W: float) -> None:
    """Draw a horizontal divider line."""
    c.setStrokeColorRGB(*COLORS['divider'])
    c.setLineWidth(0.5)
    c.line(2 * cm, y, W - 2 * cm, y)


def _draw_wrapped_text(
    c: Any,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: int = 10,
    leading: int = 12,
    color: tuple = None
) -> float:
    """Draw wrapped text and return new y position."""
    if color:
        c.setFillColorRGB(*color)
    
    c.setFont("Helvetica", font_size)
    
    # Wrap text
    char_width = font_size * 0.5
    max_chars = int(width / char_width)
    lines = textwrap.wrap(text, width=max_chars)
    
    for line in lines:
        c.drawString(x, y, line)
        y -= leading
    
    return y


def _calculate_text_height(text: str, width: float, font_size: int = 10) -> float:
    """Calculate height needed for wrapped text."""
    char_width = font_size * 0.5
    max_chars = int(width / char_width)
    lines = textwrap.wrap(text, width=max_chars)
    return len(lines) * 12  # 12pt leading


__all__ = ['render_enhanced_yearly_pdf']

