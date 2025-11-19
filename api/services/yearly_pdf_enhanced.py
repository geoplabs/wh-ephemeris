"""Enhanced PDF renderer for yearly forecast reports with improved UX/readability."""
from __future__ import annotations

import logging
import textwrap
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import A4

logger = logging.getLogger(__name__)

# WhatHoroscope Brand Colors (RGB tuples)
COLORS = {
    'crimson': (0.863, 0.149, 0.149),  # #dc2626 - WhatHoroscope brand crimson
    'crimson_dark': (0.7, 0.1, 0.1),  # Darker crimson for emphasis
    'crimson_light': (0.95, 0.7, 0.7),  # Light crimson for backgrounds
    'text_dark': (0.1, 0.1, 0.1),  # Almost black
    'text_light': (0.4, 0.4, 0.4),  # Gray
    'background': (0.98, 0.98, 0.98),  # Off-white
    'divider': (0.85, 0.85, 0.85),  # Light gray
    'white': (1.0, 1.0, 1.0),  # Pure white
}

# Typography styles
STYLES = {
    'h1': {'font': 'Helvetica-Bold', 'size': 22, 'leading': 28, 'space_before': 1.5, 'space_after': 1.0},
    'h2': {'font': 'Helvetica-Bold', 'size': 16, 'leading': 20, 'space_before': 1.2, 'space_after': 0.6},
    'h3': {'font': 'Helvetica-Bold', 'size': 13, 'leading': 16, 'space_before': 0.8, 'space_after': 0.4},
    'body': {'font': 'Helvetica', 'size': 10, 'leading': 14, 'space_before': 0, 'space_after': 0.3},
    'small': {'font': 'Helvetica', 'size': 9, 'leading': 12, 'space_before': 0, 'space_after': 0.2},
}

# Page tracking for TOC and headers/footers
PAGE_TRACKER = {
    'current_page': 0,
    'total_pages': 0,
    'toc_entries': [],
    'current_section': ''
}


def render_enhanced_yearly_pdf(payload: Dict[str, Any], out_path: str) -> str:
    """Render an enhanced, user-friendly yearly forecast PDF with TOC, headers, and footers.
    
    Args:
        payload: Report data with 'report' and 'generated_at' keys
        out_path: Output file path
        
    Returns:
        Path to generated PDF
    """
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    report = payload.get('report', {})
    meta = report.get('meta', {})
    year = meta.get('year') or datetime.now().year
    generated_at = payload.get('generated_at', '')
    
    # Reset page tracker
    PAGE_TRACKER['current_page'] = 0
    PAGE_TRACKER['total_pages'] = 0
    PAGE_TRACKER['toc_entries'] = []
    PAGE_TRACKER['current_section'] = ''
    
    W, H = A4
    
    # Create canvas
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle(f"{year} Personalized Yearly Forecast")
    c.setAuthor("WhatHoroscope.com")
    c.setSubject(f"Astrological Forecast for {year}")
    
    # Extract profile info for headers/footers
    profile_name = meta.get('profile_name') or meta.get('user_id', 'User')
    
    # Render all sections
    _render_cover_page(c, W, H, year, meta, generated_at, profile_name)
    _render_table_of_contents(c, W, H, year, profile_name)
    _render_year_at_glance(c, W, H, report.get('year_at_glance', {}), year, profile_name)
    _render_eclipses(c, W, H, report.get('eclipses_and_lunations', []), year, profile_name)
    
    for month in report.get('months', [])[:12]:
        _render_monthly_section(c, W, H, month, year, profile_name)
    
    _render_appendices(c, W, H, report, year, profile_name)
    
    c.save()
    logger.info(f"Enhanced PDF generated: {path} ({PAGE_TRACKER['current_page']} pages)")
    return str(path)


# ============================================================================
# HELPER FUNCTIONS: Headers, Footers, TOC
# ============================================================================

def _add_page(c: Any) -> None:
    """Show page and increment counter."""
    c.showPage()
    PAGE_TRACKER['current_page'] += 1


def _add_toc_entry(title: str, page_num: int, level: int = 1) -> None:
    """Add an entry to the table of contents."""
    PAGE_TRACKER['toc_entries'].append({'title': title, 'page': page_num, 'level': level})


def _render_header(c: Any, W: float, H: float, section_name: str) -> None:
    """Render page header with section name."""
    c.setFillColorRGB(*COLORS['text_light'])
    c.setFont("Helvetica", 9)
    c.drawString(2 * cm, H - 1.5 * cm, section_name)
    
    # Subtle divider line
    c.setStrokeColorRGB(*COLORS['divider'])
    c.setLineWidth(0.5)
    c.line(2 * cm, H - 1.7 * cm, W - 2 * cm, H - 1.7 * cm)


def _render_footer(c: Any, W: float, H: float, year: int, profile_name: str, page_num: int, total_pages: int = 0) -> None:
    """Render page footer with branding and page number."""
    c.setFillColorRGB(*COLORS['text_light'])
    c.setFont("Helvetica", 9)
    
    # Left: Brand
    c.drawString(2 * cm, 1.5 * cm, "WhatHoroscope.com")
    
    # Center: Report title
    center_text = f"{year} Yearly Forecast for {profile_name}"
    c.drawCentredString(W / 2, 1.5 * cm, center_text)
    
    # Right: Page number
    if total_pages > 0:
        page_text = f"Page {page_num} of {total_pages}"
    else:
        page_text = f"Page {page_num}"
    c.drawRightString(W - 2 * cm, 1.5 * cm, page_text)


def _start_new_page(c: Any, W: float, H: float, year: int, profile_name: str, section_name: str = '') -> None:
    """Start a new page with header and footer."""
    c.showPage()
    PAGE_TRACKER['current_page'] += 1
    
    if section_name:
        PAGE_TRACKER['current_section'] = section_name
    
    _render_header(c, W, H, PAGE_TRACKER['current_section'])
    _render_footer(c, W, H, year, profile_name, PAGE_TRACKER['current_page'])


# ============================================================================
# COVER PAGE
# ============================================================================

def _render_cover_page(c: Any, W: float, H: float, year: int, meta: Dict, generated_at: str, profile_name: str) -> None:
    """Render enhanced cover page with natal chart details and WhatHoroscope branding."""
    # Background color block - crimson brand color
    c.setFillColorRGB(*COLORS['crimson'])
    c.rect(0, H - 10 * cm, W, 10 * cm, fill=True, stroke=False)
    
    # Main Title
    c.setFillColorRGB(*COLORS['white'])
    c.setFont("Helvetica-Bold", 32)
    c.drawCentredString(W / 2, H - 4 * cm, f"{year}")
    
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(W / 2, H - 5.5 * cm, "Personalized Yearly Forecast")
    
    # Subtitle with name
    sun_sign = meta.get('sun_sign', '')
    if sun_sign:
        subtitle = f"Prepared for {profile_name} ({sun_sign})"
    else:
        subtitle = f"Prepared for {profile_name}"
    
    c.setFont("Helvetica", 14)
    c.drawCentredString(W / 2, H - 7 * cm, subtitle)
    
    # Brand
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(W / 2, H - 8.5 * cm, "WhatHoroscope.com")
    
    # Natal chart details (below crimson block)
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 11)
    
    birth_date = meta.get('birth_date', '')
    birth_time = meta.get('birth_time', '')
    birth_place = meta.get('birth_place', '')
    
    if birth_date or birth_time or birth_place:
        details_line = "Based on natal chart: "
        if birth_date:
            details_line += birth_date
        if birth_time:
            details_line += f" • {birth_time}"
        if birth_place:
            details_line += f" • {birth_place}"
        
        c.drawCentredString(W / 2, H - 12 * cm, details_line)
    
    # Generation timestamp
    if generated_at:
        c.setFillColorRGB(*COLORS['text_light'])
        c.setFont("Helvetica", 9)
        try:
            # Parse and format generated_at
            dt = datetime.fromisoformat(generated_at.replace('Z', '+00:00'))
            formatted_date = dt.strftime("%B %d, %Y at %H:%M UTC")
            c.drawCentredString(W / 2, 2 * cm, f"Generated: {formatted_date}")
        except:
            c.drawCentredString(W / 2, 2 * cm, f"Generated: {generated_at}")
    
    # Note: No page number on cover
    c.showPage()
    PAGE_TRACKER['current_page'] = 1


# ============================================================================
# TABLE OF CONTENTS
# ============================================================================

def _render_table_of_contents(c: Any, W: float, H: float, year: int, profile_name: str) -> None:
    """Render table of contents with page numbers."""
    # Note: Since we're building TOC as we go, we'll render sections first,
    # then come back and insert TOC. For now, reserve a page.
    # In actual implementation, we'd do two-pass rendering or use ReportLab's
    # built-in TOC features.
    
    # For simplicity, we'll track entries and render a placeholder
    # that can be updated in a second pass
    PAGE_TRACKER['toc_page'] = PAGE_TRACKER['current_page'] + 1
    
    c.showPage()
    PAGE_TRACKER['current_page'] += 1
    
    # Render TOC header
    _render_header(c, W, H, "Table of Contents")
    _render_footer(c, W, H, year, profile_name, PAGE_TRACKER['current_page'])
    
    y = H - 3 * cm
    
    # Title
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 22)
    c.drawString(2 * cm, y, "Table of Contents")
    
    y -= 1.5 * cm
    
    # Add TOC entries (these will be populated as we render sections)
    c.setFillColorRGB(*COLORS['text_dark'])
    
    # Placeholder entries (actual entries added during rendering)
    toc_entries = [
        ("Year at a Glance", 3),
        ("Top Events", 4),
        ("Eclipses & Lunations", 5),
        ("Monthly Forecasts", 6),
        ("  January 2025", 6),
        ("  February 2025", 12),
        ("  March 2025", 18),
        ("  April 2025", 24),
        ("  May 2025", 30),
        ("  June 2025", 36),
        ("  July 2025", 42),
        ("  August 2025", 48),
        ("  September 2025", 54),
        ("  October 2025", 60),
        ("  November 2025", 66),
        ("  December 2025", 72),
        ("Appendices", 78),
        ("  Glossary", 78),
        ("  Interpretation Index", 80),
    ]
    
    c.setFont("Helvetica", 11)
    for title, page_num in toc_entries:
        if y < 4 * cm:
            c.showPage()
            PAGE_TRACKER['current_page'] += 1
            _render_header(c, W, H, "Table of Contents")
            _render_footer(c, W, H, year, profile_name, PAGE_TRACKER['current_page'])
            y = H - 3 * cm
        
        # Draw title
        c.drawString(2 * cm, y, title)
        
        # Draw dotted leader
        dots_start_x = 2 * cm + c.stringWidth(title, "Helvetica", 11) + 0.3 * cm
        dots_end_x = W - 4 * cm
        
        c.setDash([1, 3])
        c.setStrokeColorRGB(*COLORS['text_light'])
        c.line(dots_start_x, y + 0.1 * cm, dots_end_x, y + 0.1 * cm)
        c.setDash([])
        
        # Draw page number
        c.drawRightString(W - 2 * cm, y, str(page_num))
        
        y -= 0.5 * cm


def _render_year_at_glance(c: Any, W: float, H: float, yag: Dict[str, Any], year: int, profile_name: str) -> None:
    """Render year-at-a-glance section with heatmap and commentary."""
    # Start new page with header/footer
    _start_new_page(c, W, H, year, profile_name, "Year at a Glance")
    _add_toc_entry("Year at a Glance", PAGE_TRACKER['current_page'])
    
    y = H - 2 * cm
    
    # Section header with crimson background
    c.setFillColorRGB(*COLORS['crimson'])
    c.rect(1.5 * cm, y - 0.8 * cm, W - 3 * cm, 1 * cm, fill=True, stroke=False)
    
    c.setFillColorRGB(*COLORS['white'])
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
    
    # Draw crimson star icon for top events
    _draw_star_icon(c, 2 * cm, y + 0.15 * cm, 0.3 * cm)
    
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 14)
    c.drawString(2.5 * cm, y, "Top Events")
    y -= 0.6 * cm
    
    for i, ev in enumerate(yag.get('top_events', [])[:8], 1):
        if y < 4 * cm:
            c.showPage()
            y = H - 2 * cm
        
        date = ev.get('date', '')
        title = ev.get('title', '')
        score = ev.get('score', 0)
        
        # Color code by score - use crimson for high intensity
        if score > 15:
            color = COLORS['crimson']
        elif score < -5:
            color = COLORS['crimson_dark']
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


def _render_eclipses(c: Any, W: float, H: float, eclipses: List[Dict[str, Any]], year: int, profile_name: str) -> None:
    """Render eclipses and lunations section."""
    if not eclipses:
        return
    
    # Start new page with header/footer
    _start_new_page(c, W, H, year, profile_name, "Eclipses & Lunations")
    _add_toc_entry("Eclipses & Lunations", PAGE_TRACKER['current_page'])
    
    y = H - 2 * cm
    
    # Section header with crimson
    c.setFillColorRGB(*COLORS['crimson'])
    c.rect(1.5 * cm, y - 0.8 * cm, W - 3 * cm, 1 * cm, fill=True, stroke=False)
    
    # Draw moon icon
    _draw_moon_icon(c, 2 * cm, y - 0.4 * cm, 0.25 * cm)
    
    c.setFillColorRGB(*COLORS['white'])
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2.8 * cm, y - 0.5 * cm, "Eclipses & Lunations")
    
    y -= 2 * cm
    
    for eclipse in eclipses[:10]:
        if y < 5 * cm:
            c.showPage()
            y = H - 2 * cm
        
        date = eclipse.get('date', '')
        kind = eclipse.get('kind', '')
        guidance = eclipse.get('guidance', '')
        
        # Eclipse header with crimson accent
        c.setFillColorRGB(*COLORS['crimson'])
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


def _render_monthly_section(c: Any, W: float, H: float, month: Dict[str, Any], year: int, profile_name: str) -> None:
    """Render a monthly section with WhatHoroscope branding."""
    month_name = month.get('month', '')
    
    # Start new page with header/footer
    _start_new_page(c, W, H, year, profile_name, month_name)
    _add_toc_entry(month_name, PAGE_TRACKER['current_page'], level=2)
    
    y = H - 1.5 * cm
    
    # Month header with crimson
    c.setFillColorRGB(*COLORS['crimson'])
    c.rect(0, y - 1.2 * cm, W, 1.5 * cm, fill=True, stroke=False)
    
    c.setFillColorRGB(*COLORS['white'])
    c.setFont("Helvetica-Bold", 22)
    c.drawString(2 * cm, y - 0.7 * cm, month_name)
    
    y -= 2.5 * cm
    
    # Overview section
    _render_subsection(c, W, y, "Overview", month.get('overview', ''))
    y -= _calculate_text_height(month.get('overview', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Career & Finance with briefcase icon
    _draw_briefcase_icon(c, 2 * cm, y + 0.15 * cm, 0.3 * cm)
    _render_subsection_with_icon(c, W, y, "Career & Finance", month.get('career_and_finance', ''))
    y -= _calculate_text_height(month.get('career_and_finance', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Relationships with heart icon
    _draw_heart_icon(c, 2 * cm, y + 0.15 * cm, 0.3 * cm)
    _render_subsection_with_icon(c, W, y, "Relationships & Family", month.get('relationships_and_family', ''))
    y -= _calculate_text_height(month.get('relationships_and_family', ''), W - 4 * cm, 10) + 1.2 * cm
    
    if y < 6 * cm:
        c.showPage()
        y = H - 2 * cm
    
    # Health with health icon
    _draw_health_icon(c, 2 * cm, y + 0.15 * cm, 0.3 * cm)
    _render_subsection_with_icon(c, W, y, "Health & Energy", month.get('health_and_energy', ''))
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


def _render_subsection(c: Any, W: float, y: float, title: str, text: str) -> None:
    """Render a subsection with crimson header."""
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 13)
    c.drawString(2 * cm, y, title)
    
    y -= 0.6 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    _draw_wrapped_text(c, text, 2 * cm, y, W - 4 * cm, font_size=10, leading=12)


def _render_subsection_with_icon(c: Any, W: float, y: float, title: str, text: str) -> None:
    """Render a subsection with icon and crimson header."""
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 13)
    c.drawString(2.6 * cm, y, title)  # Offset for icon
    
    y -= 0.6 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    _draw_wrapped_text(c, text, 2 * cm, y, W - 4 * cm, font_size=10, leading=12)


def _render_planner_actions(c: Any, W: float, y: float, actions: List[str]) -> None:
    """Render planner actions in a styled box with crimson branding."""
    if not actions:
        return
    
    box_height = len(actions) * 0.5 * cm + 1 * cm
    
    # Box background with crimson border
    c.setFillColorRGB(*COLORS['background'])
    c.setStrokeColorRGB(*COLORS['crimson'])
    c.setLineWidth(1.5)
    c.roundRect(1.8 * cm, y - box_height, W - 3.6 * cm, box_height, 0.2 * cm, fill=True, stroke=True)
    
    # Title with checkmark icon
    _draw_checkmark_icon(c, 2.2 * cm, y - 0.4 * cm, 0.25 * cm)
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2.8 * cm, y - 0.6 * cm, "Action Plan")
    
    # Actions
    y -= 1.2 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 10)
    
    for action in actions[:8]:
        # Draw crimson bullet
        c.setFillColorRGB(*COLORS['crimson'])
        c.circle(2.3 * cm, y + 0.15 * cm, 0.05 * cm, fill=True, stroke=False)
        
        c.setFillColorRGB(*COLORS['text_dark'])
        c.drawString(2.5 * cm, y, action)
        y -= 0.5 * cm


def _render_day_highlights(c: Any, W: float, y: float, high_days: List[Dict], caution_days: List[Dict]) -> None:
    """Render high score and caution days side by side with crimson icons."""
    col_width = (W - 5 * cm) / 2
    
    # High Energy Days (left column) with star icon
    _draw_star_icon(c, 2 * cm, y + 0.15 * cm, 0.25 * cm)
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.6 * cm, y, "High Energy Days")
    
    y_left = y - 0.5 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 9)
    
    for day in high_days[:6]:
        date = day.get('date', '')
        transit = day.get('transit_body', '')
        natal = day.get('natal_body', '')
        # Small crimson arrow
        c.setFillColorRGB(*COLORS['crimson'])
        c.drawString(2 * cm, y_left, "→")
        c.setFillColorRGB(*COLORS['text_dark'])
        c.drawString(2.3 * cm, y_left, f"{date}: {transit}→{natal}")
        y_left -= 0.4 * cm
    
    # Navigate With Care (right column) with warning icon
    y_right = y
    _draw_warning_icon(c, W / 2 + 0.5 * cm, y_right + 0.15 * cm, 0.25 * cm)
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 11)
    c.drawString(W / 2 + 1.1 * cm, y_right, "Navigate With Care")
    
    y_right -= 0.5 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 9)
    
    for day in caution_days[:6]:
        date = day.get('date', '')
        transit = day.get('transit_body', '')
        natal = day.get('natal_body', '')
        # Small crimson warning marker
        c.setFillColorRGB(*COLORS['crimson'])
        c.drawString(W / 2 + 0.5 * cm, y_right, "!")
        c.setFillColorRGB(*COLORS['text_dark'])
        c.drawString(W / 2 + 0.8 * cm, y_right, f"{date}: {transit}→{natal}")
        y_right -= 0.4 * cm


def _render_appendices(c: Any, W: float, H: float, report: Dict[str, Any], year: int, profile_name: str) -> None:
    """Render appendices with crimson branding."""
    # Start new page with header/footer
    _start_new_page(c, W, H, year, profile_name, "Appendices - Glossary")
    _add_toc_entry("Appendices", PAGE_TRACKER['current_page'])
    _add_toc_entry("Glossary", PAGE_TRACKER['current_page'], level=2)
    
    # Glossary
    y = H - 2 * cm
    _draw_document_icon(c, 2 * cm, y + 0.15 * cm, 0.3 * cm)
    c.setFillColorRGB(*COLORS['crimson'])
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2.6 * cm, y, "Glossary")
    
    y -= 1 * cm
    c.setFillColorRGB(*COLORS['text_dark'])
    c.setFont("Helvetica", 10)
    
    for term, definition in (report.get('glossary', {})).items():
        if y < 3 * cm:
            c.showPage()
            y = H - 2 * cm
        
        c.setFillColorRGB(*COLORS['crimson'])
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2 * cm, y, f"{term}:")
        y -= 0.4 * cm
        
        c.setFillColorRGB(*COLORS['text_dark'])
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


# ============================================================================
# CRIMSON ICON DRAWING FUNCTIONS (WhatHoroscope Brand)
# ============================================================================

def _draw_star_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson star icon (for top events, high energy)."""
    c.setFillColorRGB(*COLORS['crimson'])
    c.setStrokeColorRGB(*COLORS['crimson'])
    # Draw a simple 5-point star using a path
    path = c.beginPath()
    import math
    for i in range(5):
        angle = (i * 144 - 90) * math.pi / 180
        r = size if i % 2 == 0 else size * 0.4
        px = x + r * math.cos(angle)
        py = y + r * math.sin(angle)
        if i == 0:
            path.moveTo(px, py)
        else:
            path.lineTo(px, py)
    path.close()
    c.drawPath(path, fill=True, stroke=False)


def _draw_heart_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson heart icon (for relationships)."""
    c.setFillColorRGB(*COLORS['crimson'])
    # Simplified heart shape using curves
    path = c.beginPath()
    path.moveTo(x, y - size * 0.3)
    path.curveTo(x - size * 0.3, y + size * 0.5, x - size * 0.5, y, x, y - size * 0.5)
    path.curveTo(x + size * 0.5, y, x + size * 0.3, y + size * 0.5, x, y - size * 0.3)
    c.drawPath(path, fill=True, stroke=False)


def _draw_briefcase_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson briefcase icon (for career)."""
    c.setFillColorRGB(*COLORS['crimson'])
    c.setLineWidth(0.5)
    # Rectangle for briefcase
    c.rect(x - size * 0.4, y - size * 0.3, size * 0.8, size * 0.6, fill=True, stroke=False)
    # Handle on top
    c.setStrokeColorRGB(*COLORS['crimson'])
    c.rect(x - size * 0.2, y + size * 0.3, size * 0.4, size * 0.2, fill=False, stroke=True)


def _draw_health_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson health/medical cross icon (for health)."""
    c.setFillColorRGB(*COLORS['crimson'])
    # Cross shape
    c.rect(x - size * 0.15, y - size * 0.5, size * 0.3, size, fill=True, stroke=False)
    c.rect(x - size * 0.5, y - size * 0.15, size, size * 0.3, fill=True, stroke=False)


def _draw_checkmark_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson checkmark icon (for action plan)."""
    c.setStrokeColorRGB(*COLORS['crimson'])
    c.setLineWidth(2)
    path = c.beginPath()
    path.moveTo(x - size * 0.3, y)
    path.lineTo(x, y - size * 0.4)
    path.lineTo(x + size * 0.5, y + size * 0.5)
    c.drawPath(path, fill=False, stroke=True)


def _draw_warning_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson warning triangle icon (for caution)."""
    c.setFillColorRGB(*COLORS['crimson'])
    path = c.beginPath()
    path.moveTo(x, y + size * 0.5)
    path.lineTo(x - size * 0.5, y - size * 0.5)
    path.lineTo(x + size * 0.5, y - size * 0.5)
    path.close()
    c.drawPath(path, fill=True, stroke=False)
    # Exclamation mark
    c.setFillColorRGB(*COLORS['white'])
    c.rect(x - size * 0.05, y - size * 0.2, size * 0.1, size * 0.3, fill=True, stroke=False)
    c.circle(x, y - size * 0.35, size * 0.06, fill=True, stroke=False)


def _draw_moon_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson crescent moon icon (for eclipses/lunations)."""
    c.setFillColorRGB(*COLORS['white'])
    c.circle(x, y, size, fill=True, stroke=False)
    c.setFillColorRGB(*COLORS['crimson'])
    c.circle(x + size * 0.3, y, size * 0.8, fill=True, stroke=False)


def _draw_document_icon(c: Any, x: float, y: float, size: float) -> None:
    """Draw a crimson document icon (for glossary/appendix)."""
    c.setFillColorRGB(*COLORS['crimson'])
    # Document rectangle
    c.rect(x - size * 0.3, y - size * 0.5, size * 0.6, size, fill=True, stroke=False)
    # Folded corner
    c.setFillColorRGB(*COLORS['white'])
    path = c.beginPath()
    path.moveTo(x + size * 0.3, y + size * 0.5)
    path.lineTo(x + size * 0.3, y + size * 0.2)
    path.lineTo(x, y + size * 0.5)
    path.close()
    c.drawPath(path, fill=True, stroke=False)


__all__ = ['render_enhanced_yearly_pdf']

