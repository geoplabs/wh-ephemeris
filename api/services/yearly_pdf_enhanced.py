"""Enhanced PDF renderer for interpreted yearly horoscope reports."""

from __future__ import annotations

import io
import logging
import re
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Branding constants & typography guidance
# --------------------------------------------------------------------------------------
BRAND_COLORS = {
    "crimson": (0.863, 0.149, 0.149),
    "crimson_dark": (0.71, 0.14, 0.14),
    "crimson_light": (0.984, 0.921, 0.921),
    "energy_green": (0.82, 0.94, 0.86),
    "care_amber": (0.99, 0.9, 0.8),
    "text_dark": (0.13, 0.13, 0.13),
    "text_light": (0.45, 0.45, 0.45),
    "divider": (0.85, 0.85, 0.85),
    "white": (1, 1, 1),
}

HOUSE_KEYWORDS = {
    1: "Identity, vitality, first impressions",
    2: "Resources, income, values",
    3: "Learning, siblings, daily logistics",
    4: "Home, roots, family systems",
    5: "Creativity, dating, children",
    6: "Routines, health, service",
    7: "Partnerships, contracts, collaboration",
    8: "Shared assets, transformation, intimacy",
    9: "Travel, study, publishing, belief",
    10: "Career, reputation, public standing",
    11: "Allies, networks, future goals",
    12: "Rest, subconscious, spiritual reset",
}

PAGE_LAYOUT = {
    "margin": 2 * cm,
    "header_height": 1.4 * cm,
    "footer_height": 1.6 * cm,
}

FILLER_PREFIXES = (
    "absolutely",
    "here are some",
    "here's",
    "as we step into",
    "as you step into",
    "let's",
    "remember",
    "in summary",
)

GENERIC_BULLET_STRINGS = (
    "communicate openly",
    "reflect on your goals",
    "prioritize self care",
)

LIFE_AREA_KEYWORDS = {
    "career": {"career", "ambition", "mission", "work", "profession", "midheaven", "mc"},
    "money": {"finance", "money", "income", "earnings", "resources"},
    "home": {"home", "family", "roots", "domestic", "foundation"},
    "love": {"relationship", "love", "venus", "partnership", "marriage"},
    "health": {"health", "wellbeing", "energy", "body", "vitality"},
    "inner": {"spiritual", "healing", "inner", "emotional", "intuition"},
}


def _sanitize_bullet_artifacts(text: str) -> str:
    if not text:
        return ""
    cleaned = text.strip()
    cleaned = re.sub(r"^[\s•\-*]+", "", cleaned)
    return cleaned.strip()


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax and convert to plain text for PDF rendering.
    
    Markdown → Plain Text conversions:
    - ### Heading → Heading (remove ### and ####)
    - **bold** → bold (remove **)
    - *italic* → italic (remove *)
    - Numbered lists (1. item) → • item
    - Bullet lists (- item or * item) → • item
    - Remove extra blank lines
    """
    if not text:
        return ""
    
    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Convert markdown headings (###, ####, etc.) to plain text
        # Remove heading markers both at start and anywhere in the line
        line = re.sub(r'^#{1,6}\s*', '', line)  # At start (space optional)
        line = re.sub(r'\s*#{1,6}\s*', ' ', line)  # Anywhere else (spaces optional)

        # Convert **bold** or __bold__ to plain text (remove markers)
        line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)
        line = re.sub(r'__([^_]+)__', r'\1', line)

        # Convert *italic* or _italic_ to plain text (remove markers)
        line = re.sub(r'\*([^*]+)\*', r'\1', line)
        line = re.sub(r'_([^_]+)_', r'\1', line)

        # Convert numbered lists (1. item, 2. item) to bullets
        line = re.sub(r'^\d+\.\s+', '• ', line)

        # Convert markdown bullets (- item or * item) to standard bullets
        line = re.sub(r'^[-*]\s+', '• ', line)

        # Remove any leftover repeated markdown markers like **, ###, or ```
        line = re.sub(r'(\*{2,}|#{2,}|`{2,})', ' ', line)

        # Clean up multiple spaces
        line = re.sub(r'\s+', ' ', line).strip()

        if line:
            cleaned_lines.append(line)

    # Join with single space instead of newlines for paragraph text
    return ' '.join(cleaned_lines)

MONTH_NAME_ORDER = (
    "December 2024",
    "January 2025",
    "February 2025",
    "March 2025",
    "April 2025",
    "May 2025",
    "June 2025",
    "July 2025",
    "August 2025",
    "September 2025",
    "October 2025",
    "November 2025",
    "December 2025",
)


@dataclass
class TocEntry:
    """Table-of-contents entry with bookmark metadata."""

    title: str
    level: int
    page: int
    anchor: str


@dataclass
class RenderState:
    """Tracks pagination, bookmarks, and QA metadata during rendering."""

    collecting: bool
    current_page: int = 0
    current_section: str = ""
    total_pages: int = 0
    toc_entries: List[TocEntry] = field(default_factory=list)
    toc_cursor: int = 0
    paragraph_event_links: List[Dict[str, Any]] = field(default_factory=list)

    def reset(self, collecting: bool) -> None:
        self.collecting = collecting
        self.current_page = 0
        self.current_section = ""
        self.toc_entries = []
        self.toc_cursor = 0
        self.paragraph_event_links = []

    def register_section(self, title: str, level: int, pdf: Optional[canvas.Canvas] = None) -> str:
        anchor = _slugify(title, suffix=str(len(self.toc_entries) + self.toc_cursor))
        if self.collecting:
            self.toc_entries.append(TocEntry(title=title, level=level, page=self.current_page, anchor=anchor))
            return anchor

        if self.toc_cursor < len(self.toc_entries):
            entry = self.toc_entries[self.toc_cursor]
            entry.page = self.current_page
            if not entry.anchor:
                entry.anchor = anchor
            anchor = entry.anchor
        else:
            self.toc_entries.append(TocEntry(title=title, level=level, page=self.current_page, anchor=anchor))

        self.toc_cursor += 1
        if pdf is not None:
            pdf.bookmarkPage(anchor)
            pdf.addOutlineEntry(title, anchor, level - 1, closed=False)
        return anchor

    def record_paragraph_events(self, section: str, text: str, events: Iterable[Dict[str, Any]]) -> None:
        links = []
        for ev in events:
            event_id = ev.get("id") or _slugify(
                f"{ev.get('date')} {ev.get('transit_body')} {ev.get('aspect')} {ev.get('natal_body')}"
            )
            links.append(event_id)
        if links:
            self.paragraph_event_links.append({"section": section, "text": text[:120], "events": links})


class ContentValidator:
    """Applies guardrails before rendering copy to the PDF."""

    def __init__(self, target_year: int) -> None:
        self.target_year = target_year
        self.previous_year = target_year - 1
        self.allowed_previous_month = "December"

    def clean_text(self, text: str, *, month_label: Optional[str] = None) -> str:
        if not text:
            return ""
        # NOTE: We no longer strip markdown - it will be parsed and formatted by _parse_and_render_markdown()
        cleaned = text.strip()
        while "  " in cleaned:
            cleaned = cleaned.replace("  ", " ")
        lower = cleaned.lower()
        for prefix in FILLER_PREFIXES:
            if lower.startswith(prefix):
                cleaned = cleaned[len(prefix) :].lstrip(" ,-.!")
                break
        cleaned = self._strip_generic_phrases(cleaned)
        cleaned = self._strip_technical_notation(cleaned)
        allow_previous = bool(month_label and self.allowed_previous_month in month_label and str(self.previous_year) in month_label)
        self._guard_year_mentions(cleaned, allow_previous)
        return cleaned

    def _strip_generic_phrases(self, text: str) -> str:
        for phrase in GENERIC_BULLET_STRINGS:
            text = re.sub(rf"\b{re.escape(phrase)}\b", "", text, flags=re.IGNORECASE)
        return text.strip()

    def _strip_technical_notation(self, text: str) -> str:
        text = re.sub(r"\[[^\]]+\]", "", text)
        text = re.sub(
            r"(?P<phase>applying|separating)\s+(?P<aspect>[a-z\s]+?)\s+at\s+\d+(?:\.\d+)?°\s+orb",
            lambda m: f"{m.group('aspect').strip().title()} influence",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\d+(?:\.\d+)?°\s*orb", "", text, flags=re.IGNORECASE)
        text = text.replace("Applying opposition", "Opposition")
        return " ".join(text.split())

    def _guard_year_mentions(self, text: str, allow_previous: bool) -> None:
        prev = str(self.previous_year)
        if prev in text and not allow_previous:
            raise ValueError(f"Paragraph mentions wrong year {prev}: {text}")

    def sanitize_actions(self, actions: List[str]) -> List[str]:
        sanitized: List[str] = []
        for action in actions[:7]:
            # Strip markdown first
            clean = _strip_markdown(action)
            clean = clean.strip()
            if clean.endswith("..."):
                clean = clean.rstrip(".")
            if len(clean) > 140:
                clean = clean[:137].rstrip() + "…"
            sanitized.append(clean)
        return sanitized

    def inject_transit_references(self, text: str, events: List[Dict[str, Any]], min_refs: int = 2) -> str:
        if not events or min_refs <= 0:
            return text
        references = []
        for ev in events[:min_refs]:
            snippet = _format_transit_sentence(ev)
            if snippet:
                references.append(snippet)
        if not references:
            return text
        joiner = " " if text else ""
        return f"{text}{joiner}{' '.join(references)}"

    def ensure_month_has_events(self, events: List[Dict[str, Any]], month_label: str) -> None:
        if len(events) < 2:
            raise ValueError(f"Monthly section '{month_label}' missing transit references")


# --------------------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------------------

def render_enhanced_yearly_pdf(payload: Dict[str, Any], out_path: str) -> str:
    """Render the interpreted yearly forecast with the WhatHoroscope PDF spec."""

    report = payload.get("report") or {}
    meta = report.get("meta") or {}
    target_year = int(meta.get("target_year") or meta.get("year") or datetime.utcnow().year)
    validator = ContentValidator(target_year)
    sanitized_report = _prepare_report(report, validator)

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    generated_at = payload.get("generated_at") or datetime.utcnow().isoformat()

    # First pass: gather TOC entries and total pages
    buffer = io.BytesIO()
    first_state = RenderState(collecting=True)
    _render_pdf(canvas.Canvas(buffer, pagesize=A4), sanitized_report, meta, generated_at, validator, first_state)

    # Second pass: real PDF with TOC, headers, and page counts
    second_state = RenderState(collecting=False)
    second_state.toc_entries = list(first_state.toc_entries)
    second_state.total_pages = first_state.current_page
    pdf = canvas.Canvas(str(path), pagesize=A4)
    pdf.setTitle(f"{target_year} Personalized Yearly Forecast")
    pdf.setAuthor("WhatHoroscope.com")
    pdf.setSubject(f"{target_year} Yearly Forecast for {meta.get('profile_name') or 'Client'}")
    pdf.setKeywords("astrology, yearly horoscope, WhatHoroscope, personalized forecast")
    _render_pdf(pdf, sanitized_report, meta, generated_at, validator, second_state)
    logger.info("enhanced_yearly_pdf_rendered", extra={"pages": second_state.current_page, "path": str(path)})
    return str(path)


# --------------------------------------------------------------------------------------
# Rendering orchestrator
# --------------------------------------------------------------------------------------

def _render_pdf(
    pdf: canvas.Canvas,
    report: Dict[str, Any],
    meta: Dict[str, Any],
    generated_at: str,
    validator: ContentValidator,
    state: RenderState,
) -> None:
    width, height = A4
    profile = _extract_profile(meta)
    branding = meta.get("branding") or report.get("branding") or {}
    _render_cover_page(pdf, width, height, profile, generated_at, state, branding, meta)
    _render_table_of_contents(pdf, width, height, state, profile)
    _render_year_at_glance(pdf, width, height, report.get("year_at_glance") or {}, profile, validator, state)
    _render_usage_primer(pdf, width, height, profile, state)
    _render_natal_snapshot(pdf, width, height, report, profile, meta, state)
    _render_methodology_page(pdf, width, height, report, profile, meta, state)
    _render_eclipses(pdf, width, height, report.get("eclipses_and_lunations") or [], profile, state)
    _render_retrograde_summary(pdf, width, height, report, profile, state)

    for month in _ordered_months(report.get("months") or []):
        _render_monthly_section(pdf, width, height, month, profile, validator, state)

    _render_appendices(pdf, width, height, report, profile, state)
    _render_sources_page(pdf, width, height, profile, meta, generated_at, state)
    pdf.save()


# --------------------------------------------------------------------------------------
# Cover page and TOC
# --------------------------------------------------------------------------------------

def _render_cover_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    profile: Dict[str, str],
    generated_at: str,
    state: RenderState,
    branding: Dict[str, Any],
    meta: Dict[str, Any],
) -> None:
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.rect(0, height - 13 * cm, width, 13 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["white"])
    _draw_brand_badge(pdf, width, height, branding)
    pdf.setFillColorRGB(*BRAND_COLORS["white"])
    pdf.setFont("Helvetica-Bold", 36)
    pdf.drawCentredString(width / 2, height - 4.2 * cm, f"{profile['year']} Yearly Forecast")

    subtitle = f"Prepared for {profile['name']}"
    if profile.get("sun_sign"):
        subtitle += f" · Sun in {profile['sun_sign']}"
    pdf.setFont("Helvetica", 16)
    pdf.drawCentredString(width / 2, height - 6.2 * cm, subtitle)

    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(
        width / 2,
        height - 7.4 * cm,
        f"Birth data: {profile['birth_date']} • {profile['birth_time']} • {profile['birth_place']}",
    )

    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(PAGE_LAYOUT["margin"], height - 9.5 * cm, "Snapshot")
    pdf.setFont("Helvetica", 11)
    snapshot_lines = [
        f"Client: {profile['name']}",
        f"Focus Year: {profile['year']}",
        f"Chart Ref: {meta.get('timezone', {}).get('resolved', 'UTC')}",
    ]
    y = height - 10.5 * cm
    for line in snapshot_lines:
        pdf.drawString(PAGE_LAYOUT["margin"], y, line)
        y -= 0.55 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["text_light"])
    pdf.setFont("Helvetica", 10)
    pdf.drawCentredString(width / 2, 2 * cm, _format_generated_at(generated_at))

    pdf.showPage()
    state.current_page = 1
    state.current_section = ""


def _draw_brand_badge(pdf: canvas.Canvas, width: float, height: float, branding: Dict[str, Any]) -> None:
    logo_path = branding.get("logo_path") or branding.get("logo_url") or ""
    drawn = False
    if logo_path and not logo_path.lower().startswith("http"):
        try:
            image = ImageReader(logo_path)
            pdf.drawImage(
                image,
                width / 2 - 1.5 * cm,
                height - 3.7 * cm,
                width=3 * cm,
                height=3 * cm,
                mask="auto",
            )
            drawn = True
        except Exception:
            logger.debug("cover_logo_load_failed", exc_info=True)
    if drawn:
        return
    pdf.setFillColorRGB(*BRAND_COLORS["white"])
    pdf.circle(width / 2, height - 3.2 * cm, 1.2 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawCentredString(width / 2, height - 3.3 * cm, branding.get("monogram", "WH"))


def _render_table_of_contents(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    state: RenderState,
    profile: Dict[str, str],
) -> None:
    _start_numbered_page(pdf, width, height, state, profile, "Table of Contents", include_in_toc=False)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 22)
    pdf.drawString(PAGE_LAYOUT["margin"], height - 2.5 * cm, "Table of Contents")

    y = height - 4 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    pdf.setFont("Helvetica", 11)

    for entry in state.toc_entries:
        if y < 3 * cm:
            _start_numbered_page(pdf, width, height, state, profile, "Table of Contents", include_in_toc=False)
            pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            pdf.setFont("Helvetica", 11)
            y = height - 3 * cm

        indent = 0.5 * cm if entry.level > 1 else 0
        title_x = PAGE_LAYOUT["margin"] + indent
        pdf.drawString(title_x, y, entry.title)
        dots_start = title_x + pdf.stringWidth(entry.title, "Helvetica", 11) + 0.2 * cm
        dots_end = width - PAGE_LAYOUT["margin"] - 1 * cm
        pdf.setStrokeColorRGB(*BRAND_COLORS["divider"])
        pdf.setDash(1, 2)
        pdf.line(dots_start, y + 0.1 * cm, dots_end, y + 0.1 * cm)
        pdf.setDash()
        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        pdf.drawRightString(width - PAGE_LAYOUT["margin"], y, str(entry.page))
        if not state.collecting:
            pdf.linkAbsolute(
                "",
                entry.anchor,
                Rect=(PAGE_LAYOUT["margin"], y - 0.1 * cm, width - PAGE_LAYOUT["margin"], y + 0.3 * cm),
            )
        y -= 0.6 * cm


# --------------------------------------------------------------------------------------
# Year at a glance & top events data page
# --------------------------------------------------------------------------------------

def _render_year_at_glance(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    data: Dict[str, Any],
    profile: Dict[str, str],
    validator: ContentValidator,
    state: RenderState,
) -> None:
    _start_numbered_page(pdf, width, height, state, profile, "Year at a Glance", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Year at a Glance")
    y -= 1.2 * cm

    commentary = validator.clean_text(data.get("commentary", ""))
    if commentary:
        y = _parse_and_render_markdown(pdf, commentary, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 12, 16)
        state.record_paragraph_events("Year at a Glance", commentary, data.get("top_events", []))
        y -= 0.4 * cm

    # Heatmap / focus summary text
    heat_summary = _summarize_heatmap(data.get("heatmap") or [])
    if heat_summary:
        pdf.setFont("Helvetica-Bold", 12)
        pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
        pdf.drawString(PAGE_LAYOUT["margin"], y, "Monthly Momentum")
        y -= 0.5 * cm
        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        pdf.setFont("Helvetica", 10)
        y = _draw_wrapped(pdf, heat_summary, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
        y -= 0.4 * cm

    _register_section(state, pdf, "Top Events", level=2)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Top Events")
    y -= 0.8 * cm

    for event in data.get("top_events", [])[:8]:
        if y < 4 * cm:
            _continue_page(pdf, width, height, state, profile)
            pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
            pdf.setFont("Helvetica-Bold", 14)
            pdf.drawString(PAGE_LAYOUT["margin"], height - 2.5 * cm, "Top Events (cont.)")
            y = height - 3.7 * cm

        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        pdf.setFont("Helvetica-Bold", 11)
        summary = _format_top_event_line(event)
        pdf.drawString(PAGE_LAYOUT["margin"], y, summary)
        y -= 0.4 * cm
        guidance = event.get("summary", "")
        # Strip markdown from event guidance
        guidance = _strip_markdown(guidance)
        y = _draw_wrapped(pdf, guidance, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
        y -= 0.2 * cm


# --------------------------------------------------------------------------------------
# Usage primer page to minimize monthly repetition
# --------------------------------------------------------------------------------------

def _render_usage_primer(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    profile: Dict[str, str],
    state: RenderState,
) -> None:
    _start_numbered_page(pdf, width, height, state, profile, "How to Use This Forecast", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "How to Use This Forecast")
    y -= 1 * cm

    primer_text = (
        "Health, career, and relationship notes appear in every month. Read the overview first, "
        "then skim the Key Dates table and heatbar to spot active weeks. Action plans list "
        "dated tasks tied to specific transits; use them as calendar reminders."
    )
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    y = _draw_wrapped(pdf, primer_text, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 11, 16)
    y -= 0.8 * cm

    bullets = [
        "Career & Finance callouts highlight Midheaven/10th-house transits first.",
        "Relationships & Family emphasizes Venus, Moon, and 4th/7th-house activity.",
        "Health & Energy leans on Mars, Saturn, and Virgo/Pisces placements for wellness timing.",
    ]
    y = _draw_bullet_list(pdf, bullets, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)

    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Legend & Score Guide")
    y -= 0.6 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    legend = [
        ("High Score Day", "Score ≥ +0.60 — quick wins and launches."),
        ("Navigate With Care", "Score ≤ -0.40 — slow down, rest, review."),
        ("Aspect Grid", "Squares/Oppositions = friction · Trines/Sextiles = flow."),
        ("Rituals & Journal", "Micro-practices that anchor the month's lesson."),
    ]
    for label, desc in legend:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(PAGE_LAYOUT["margin"], y, label)
        pdf.setFont("Helvetica", 10)
        pdf.drawString(PAGE_LAYOUT["margin"] + 4.2 * cm, y, desc)
        y -= 0.45 * cm

    y -= 0.2 * cm
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Score Ranges")
    y -= 0.5 * cm
    score_rows = [
        ("+0.80 to +1.00", "Peak momentum · say yes"),
        ("+0.40 to +0.79", "Supportive growth"),
        ("-0.10 to +0.39", "Neutral · focus on maintenance"),
        ("-0.40 to -0.69", "Sensitive · reduce load"),
        ("≤ -0.70", "Storm watch · rest, regroup"),
    ]
    col_widths = [3.5 * cm, width - 2 * PAGE_LAYOUT["margin"] - 3.5 * cm]
    _draw_table_row(pdf, ["Score", "Meaning"], PAGE_LAYOUT["margin"], y, col_widths, header=True)
    y -= 0.6 * cm
    for score, meaning in score_rows:
        _draw_table_row(pdf, [score, meaning], PAGE_LAYOUT["margin"], y, col_widths, header=False)
        y -= 0.5 * cm


def _render_natal_snapshot(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Dict[str, Any],
    profile: Dict[str, str],
    meta: Dict[str, Any],
    state: RenderState,
) -> None:
    _start_numbered_page(pdf, width, height, state, profile, "Natal Snapshot", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Natal Snapshot & House Themes")
    y -= 1 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["crimson_light"])
    box_height = 3 * cm
    pdf.roundRect(PAGE_LAYOUT["margin"], y - box_height, width - 2 * PAGE_LAYOUT["margin"], box_height, 0.2 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson_dark"])
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(PAGE_LAYOUT["margin"] + 0.4 * cm, y - 0.6 * cm, "Natal Essentials")
    pdf.setFont("Helvetica", 10)
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    snapshot_lines = [
        f"Name: {profile['name']}",
        f"Sun sign: {profile.get('sun_sign', '–')}",
        f"Birth: {profile['birth_date']} · {profile['birth_time']} · {profile['birth_place']}",
        f"Time zone: {meta.get('timezone', {}).get('resolved', 'UTC')}",
    ]
    cursor = y - 1.2 * cm
    for line in snapshot_lines:
        pdf.drawString(PAGE_LAYOUT["margin"] + 0.4 * cm, cursor, line)
        cursor -= 0.45 * cm
    y -= box_height + 0.8 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "House Themes Map")
    y -= 0.6 * cm
    house_focus = _aggregate_house_focus(report.get("appendix_all_events") or [])
    if not house_focus:
        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        pdf.setFont("Helvetica", 10)
        pdf.drawString(PAGE_LAYOUT["margin"], y, "House emphasis will populate once event data is available.")
        return

    col_widths = [1.8 * cm, 6 * cm, width - 2 * PAGE_LAYOUT["margin"] - 7.8 * cm]
    _draw_table_row(pdf, ["House", "Themes", "Activity"], PAGE_LAYOUT["margin"], y, col_widths, header=True)
    y -= 0.6 * cm
    for entry in house_focus[:8]:
        label = f"{entry['house']}"
        themes = entry["keywords"]
        activity = entry["intensity"]
        _draw_table_row(pdf, [label, themes, activity], PAGE_LAYOUT["margin"], y, col_widths, header=False)
        y -= 0.5 * cm


def _render_methodology_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Dict[str, Any],
    profile: Dict[str, str],
    meta: Dict[str, Any],
    state: RenderState,
) -> None:
    _start_numbered_page(pdf, width, height, state, profile, "Methodology", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Methodology & Scoring")
    y -= 0.8 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    intro = (
        "Transits are calculated with WH-Ephemeris, blended with Swiss Ephemeris accuracy, "
        "and interpreted through the WhatHoroscope narrative engine. Each paragraph you read "
        "is QA-ed to stay actionable, compassionate, and grounded."
    )
    y = _draw_wrapped(pdf, intro, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 11, 16)
    y -= 0.4 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Scoring Signals")
    y -= 0.5 * cm
    scoring_opts = (meta.get("options") or {}).get("scoring") or {}
    score_lines = []
    for key, value in scoring_opts.items():
        label = key.replace("_", " ").title()
        score_lines.append(f"{label}: {value}")
    if not score_lines:
        score_lines = [
            "Angle bonus: +0.30 when a transit hits ASC/MC/DSC/IC.",
            "Applying bonus: +0.08 as planets move toward exactness.",
            "Separating penalty: -0.04 once the aspect releases.",
        ]
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    y = _draw_bullet_list(pdf, score_lines, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)

    total_events = len(report.get("appendix_all_events") or [])
    pdf.setFont("Helvetica", 10)
    pdf.drawString(PAGE_LAYOUT["margin"], y + 0.3 * cm, f"Events scored this year: {total_events}")
    y -= 0.4 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "What the numbers mean")
    y -= 0.5 * cm
    meaning = (
        "Scores cap near ±1.00. Values above +0.60 signal green lights and bonus support. "
        "Anything below -0.40 requests gentler pacing, with -0.80 or lower flagging storm-grade windows."
    )
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    _draw_wrapped(pdf, meaning, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
# --------------------------------------------------------------------------------------
# Eclipses & Lunations data cards
# --------------------------------------------------------------------------------------

def _render_eclipses(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    eclipses: List[Dict[str, Any]],
    profile: Dict[str, str],
    state: RenderState,
) -> None:
    if not eclipses:
        return
    _start_numbered_page(pdf, width, height, state, profile, "Eclipses & Lunations", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Eclipses & Lunations")
    y -= 0.8 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    primer = (
        "Eclipses accelerate endings and beginnings. Give yourself extra recovery time, "
        "anchor with grounding rituals, and watch what resurfaces in the life area noted on each card."
    )
    y = _draw_wrapped(pdf, primer, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
    y -= 0.4 * cm
    primer_bullets = [
        "Keep schedules light ±3 days around the event.",
        "Journal what surfaces — themes repeat every ~6 months.",
        "Act on clarity, not urgency; eclipses reveal the assignment, not the entire plan.",
    ]
    y = _draw_bullet_list(pdf, primer_bullets, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
    y -= 0.6 * cm
    
    # Render full eclipse guidance narrative (LLM-generated with markdown)
    if eclipses:
        eclipse_guidance = eclipses[0].get("guidance", "")
        if eclipse_guidance and len(eclipse_guidance) > 100:  # Only if substantial guidance exists
            pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            y = _parse_and_render_markdown(
                pdf, 
                eclipse_guidance, 
                PAGE_LAYOUT["margin"], 
                y, 
                width - 2 * PAGE_LAYOUT["margin"],
                base_font_size=10,
                line_height=14
            )
            y -= 1.0 * cm

    for eclipse in eclipses:
        if y < 4 * cm:
            _continue_page(pdf, width, height, state, profile)
            pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(PAGE_LAYOUT["margin"], height - 2.5 * cm, "Eclipse Insights (cont.)")
            y = height - 3.5 * cm

        bullets = _build_eclipse_bullets(eclipse)
        _draw_eclipse_card(pdf, width, y, eclipse, bullets)
        y -= 4.5 * cm


def _render_retrograde_summary(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Dict[str, Any],
    profile: Dict[str, str],
    state: RenderState,
) -> None:
    windows = _extract_retrograde_windows(report.get("appendix_all_events") or [])
    if not windows:
        return
    _start_numbered_page(pdf, width, height, state, profile, "Retrogrades & Stations", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Retrogrades & Stations")
    y -= 0.8 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    intro = (
        "Retrograde periods stretch over several weeks. Use the start date as your cue to review, and the direct station as a "
        "natural relaunch moment."
    )
    y = _draw_wrapped(pdf, intro, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
    y -= 0.4 * cm

    for window in windows:
        if y < 4 * cm:
            _continue_page(pdf, width, height, state, profile)
            y = height - 2.5 * cm
        pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
        pdf.setFont("Helvetica-Bold", 12)
        span = f"{window['start']} → {window['end'] or 'TBD'}"
        pdf.drawString(PAGE_LAYOUT["margin"], y, f"{window['body']} retrograde")
        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        pdf.setFont("Helvetica", 10)
        pdf.drawString(PAGE_LAYOUT["margin"], y - 0.5 * cm, f"Window: {span}")
        y -= 0.9 * cm
        for station in window.get("stations", []):
            pdf.drawString(
                PAGE_LAYOUT["margin"] + 0.4 * cm,
                y,
                f"• {station['date']}: {station['label']}",
            )
            y -= 0.45 * cm
        if window.get("notes"):
            summary = window["notes"]
            y = _draw_wrapped(
                pdf,
                summary,
                PAGE_LAYOUT["margin"],
                y,
                width - 2 * PAGE_LAYOUT["margin"],
                10,
                14,
            )
        y -= 0.2 * cm


# --------------------------------------------------------------------------------------
# Monthly sections
# --------------------------------------------------------------------------------------

def _render_monthly_section(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    month: Dict[str, Any],
    profile: Dict[str, str],
    validator: ContentValidator,
    state: RenderState,
) -> None:
    month_label = month.get("month") or "Month"
    section_title = f"{month_label} – Month Overview"
    _start_numbered_page(pdf, width, height, state, profile, section_title, level=1)
    y = height - 2.7 * cm

    themes = month.get("key_themes") or _derive_month_themes(month)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, section_title)
    pdf.setFont("Helvetica", 11)
    pdf.drawString(PAGE_LAYOUT["margin"], y - 0.8 * cm, f"Key Themes: {' • '.join(themes)}")
    y -= 1.8 * cm

    events = _gather_month_events(month)
    validator.ensure_month_has_events(events, month_label)

    overview_text = validator.inject_transit_references(
        validator.clean_text(month.get("overview", ""), month_label=month_label),
        events,
    )
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    y = _parse_and_render_markdown(pdf, overview_text, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 11, 16)
    state.record_paragraph_events(section_title, overview_text, events[:3])
    y -= 0.5 * cm

    y = _render_key_insight(pdf, width, y, month)

    y = _render_key_dates_table(pdf, width, y, events)
    y = _render_heatbar(pdf, width, y, events, month_label)
    y = _render_life_area_summary(pdf, width, y, events)

    y = _render_subsection_text(
        pdf,
        width,
        height,
        y,
        "High-Score Days",
        _summarize_high_score_days(month.get("high_score_days", [])),
        state,
        profile,
        section_title,
        month.get("high_score_days", []),
    )

    y = _render_subsection_text(
        pdf,
        width,
        height,
        y,
        "Career & Finance",
        validator.inject_transit_references(
            validator.clean_text(month.get("career_and_finance", ""), month_label=month_label),
            events,
        ),
        state,
        profile,
        f"{section_title} – Career",
        events,
    )

    y = _render_subsection_text(
        pdf,
        width,
        height,
        y,
        "Relationships & Family",
        validator.inject_transit_references(
            validator.clean_text(month.get("relationships_and_family", ""), month_label=month_label),
            events,
        ),
        state,
        profile,
        f"{section_title} – Relationships",
        events,
    )

    y = _render_subsection_text(
        pdf,
        width,
        height,
        y,
        "Health & Energy",
        validator.inject_transit_references(
            validator.clean_text(month.get("health_and_energy", ""), month_label=month_label),
            events,
        ),
        state,
        profile,
        f"{section_title} – Health",
        events,
    )

    y = _render_action_plan(pdf, width, y, validator.sanitize_actions(month.get("planner_actions", [])), events)
    _render_energy_callouts(pdf, width, height, y, month, profile, state)


# --------------------------------------------------------------------------------------
# Appendices & reference tables
# --------------------------------------------------------------------------------------

def _render_appendices(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    report: Dict[str, Any],
    profile: Dict[str, str],
    state: RenderState,
) -> None:
    glossary = report.get("glossary") or {}
    interpretation = report.get("interpretation_index") or {}

    if glossary:
        _start_numbered_page(pdf, width, height, state, profile, "Appendix – Glossary", level=1)
        _register_section(state, pdf, "Glossary", level=2)
        y = height - 2.5 * cm
        pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(PAGE_LAYOUT["margin"], y, "Glossary")
        y -= 1 * cm
        for term, definition in glossary.items():
            if y < 3 * cm:
                _continue_page(pdf, width, height, state, profile)
                y = height - 2.5 * cm
            pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
            pdf.setFont("Helvetica-Bold", 11)
            pdf.drawString(PAGE_LAYOUT["margin"], y, term)
            y -= 0.4 * cm
            pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            y = _draw_wrapped(pdf, definition, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
            y -= 0.4 * cm

    if interpretation:
        _start_numbered_page(pdf, width, height, state, profile, "Appendix – Interpretation Index", level=1)
        _register_section(state, pdf, "Interpretation Index", level=2)
        y = height - 2.5 * cm
        pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawString(PAGE_LAYOUT["margin"], y, "Interpretation Index")
        y -= 1 * cm
        for term, definition in interpretation.items():
            if y < 3 * cm:
                _continue_page(pdf, width, height, state, profile)
                y = height - 2.5 * cm
            pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            pdf.setFont("Helvetica", 10)
            y = _draw_wrapped(
                pdf,
                f"{term}: {definition}",
                PAGE_LAYOUT["margin"],
                y,
                width - 2 * PAGE_LAYOUT["margin"],
                10,
                14,
            )
            y -= 0.3 * cm


def _render_sources_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    profile: Dict[str, str],
    meta: Dict[str, Any],
    generated_at: str,
    state: RenderState,
) -> None:
    _start_numbered_page(pdf, width, height, state, profile, "Sources & Credits", level=1)
    y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Sources & Versioning")
    y -= 0.8 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    versioning = meta.get("versioning") or {}
    version_line = f"Engine versions: {versioning.get('ephemeris_version', 'se-2.x')} · {versioning.get('algo_version', 'yh-2025.x')}"
    pdf.setFont("Helvetica", 10)
    pdf.drawString(PAGE_LAYOUT["margin"], y, version_line)
    y -= 0.5 * cm
    pdf.drawString(PAGE_LAYOUT["margin"], y, f"Generated: {_format_generated_at(generated_at)}")
    y -= 0.5 * cm
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Data sources: Swiss Ephemeris, NASA JPL DE430, WhatHoroscope house models.")
    y -= 0.8 * cm

    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Credits & Notes")
    y -= 0.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    bullets = [
        "Narratives generated by the WhatHoroscope LLM interpreter, reviewed by QA heuristics.",
        "Scores derive from transit strength, dignities, and bonuses for eclipses, angles, and progressions.",
        "This report is informational only — not medical, financial, or legal advice.",
        "© WhatHoroscope. Please do not redistribute without permission.",
    ]
    _draw_bullet_list(pdf, bullets, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)


# --------------------------------------------------------------------------------------
# Helper drawing functions
# --------------------------------------------------------------------------------------

def _start_numbered_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    state: RenderState,
    profile: Dict[str, str],
    section_name: str,
    *,
    include_in_toc: bool = True,
    level: int = 1,
) -> None:
    pdf.showPage()
    state.current_page += 1
    state.current_section = section_name
    _render_header(pdf, width, height, section_name)
    _render_footer(pdf, width, height, profile, state)
    if include_in_toc:
        state.register_section(section_name, level, pdf if not state.collecting else None)


def _continue_page(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    state: RenderState,
    profile: Dict[str, str],
) -> None:
    pdf.showPage()
    state.current_page += 1
    _render_header(pdf, width, height, state.current_section)
    _render_footer(pdf, width, height, profile, state)


def _render_header(pdf: canvas.Canvas, width: float, height: float, section_name: str) -> None:
    pdf.setFillColorRGB(*BRAND_COLORS["text_light"])
    pdf.setFont("Helvetica", 9)
    pdf.drawString(PAGE_LAYOUT["margin"], height - PAGE_LAYOUT["header_height"], section_name)
    pdf.setStrokeColorRGB(*BRAND_COLORS["divider"])
    pdf.setLineWidth(0.5)
    pdf.line(
        PAGE_LAYOUT["margin"],
        height - PAGE_LAYOUT["header_height"] - 0.2 * cm,
        width - PAGE_LAYOUT["margin"],
        height - PAGE_LAYOUT["header_height"] - 0.2 * cm,
    )


def _render_footer(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    profile: Dict[str, str],
    state: RenderState,
) -> None:
    pdf.setFillColorRGB(*BRAND_COLORS["text_light"])
    pdf.setFont("Helvetica", 9)
    pdf.drawString(PAGE_LAYOUT["margin"], PAGE_LAYOUT["footer_height"] - 0.3 * cm, "WhatHoroscope.com")
    pdf.drawCentredString(width / 2, PAGE_LAYOUT["footer_height"] - 0.3 * cm, f"{profile['year']} Yearly Forecast for {profile['name']}")
    total = state.total_pages if state.total_pages else state.current_page
    pdf.drawRightString(
        width - PAGE_LAYOUT["margin"],
        PAGE_LAYOUT["footer_height"] - 0.3 * cm,
        f"Page {state.current_page} of {total}",
    )


def _register_section(state: RenderState, pdf: canvas.Canvas, title: str, level: int) -> None:
    state.register_section(title, level, pdf if not state.collecting else None)


def _parse_and_render_markdown(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    base_font_size: int = 10,
    line_height: int = 14,
) -> float:
    """Parse markdown text and render with proper formatting.
    
    Supports:
    - # H1, ## H2, ### H3, #### H4 headings
    - **bold** text
    - __bold__ text
    - *italic* text (rendered as regular for simplicity)
    - _italic_ text (rendered as regular for simplicity)
    - - bullet lists
    - Paragraph breaks (double newline)
    
    Returns: new y position after rendering
    """
    if not text:
        return y
    
    current_y = y
    lines = text.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines but add spacing
        if not line:
            current_y -= line_height * 0.5
            i += 1
            continue
        
        # Check for headings
        heading_match = re.match(r'^(#{1,6})\s+(.+)$', line)
        if heading_match:
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            
            # Add spacing before heading
            if i > 0:
                current_y -= line_height * 0.8
            
            # Render heading with appropriate style
            if level == 1:  # # H1
                pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
                pdf.setFont("Helvetica-Bold", 18)
                current_y = _draw_wrapped(pdf, heading_text, x, current_y, max_width, 18, 22)
                pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            elif level == 2:  # ## H2
                pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
                pdf.setFont("Helvetica-Bold", 14)
                current_y = _draw_wrapped(pdf, heading_text, x, current_y, max_width, 14, 18)
                pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            elif level == 3:  # ### H3
                pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
                pdf.setFont("Helvetica-Bold", 12)
                current_y = _draw_wrapped(pdf, heading_text, x, current_y, max_width, 12, 16)
                pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
            else:  # #### H4+
                pdf.setFont("Helvetica-Bold", 11)
                current_y = _draw_wrapped(pdf, heading_text, x, current_y, max_width, 11, 14)
            
            current_y -= line_height * 0.3
            i += 1
            continue
        
        # Check for bullet list
        bullet_match = re.match(r'^[-*]\s+(.+)$', line)
        if bullet_match:
            bullet_text = bullet_match.group(1).strip()
            # Parse inline formatting in bullet text
            formatted_text = _parse_inline_formatting(bullet_text)
            pdf.setFont("Helvetica", base_font_size)
            # Render bullet with text
            current_y = _render_bullet_with_formatting(pdf, formatted_text, x, current_y, max_width, base_font_size, line_height)
            i += 1
            continue
        
        # Regular paragraph - parse inline formatting
        formatted_text = _parse_inline_formatting(line)
        pdf.setFont("Helvetica", base_font_size)
        current_y = _render_paragraph_with_formatting(pdf, formatted_text, x, current_y, max_width, base_font_size, line_height)
        
        i += 1
    
    return current_y


def _parse_inline_formatting(text: str) -> List[Tuple[str, str]]:
    """Parse inline markdown formatting and return list of (text, style) tuples.
    
    Returns: [(text, style), ...] where style is 'bold', 'regular', etc.
    """
    segments = []
    current_pos = 0
    
    # Pattern to match **bold** or __bold__
    bold_pattern = re.compile(r'(\*\*|__)(.+?)\1')
    
    for match in bold_pattern.finditer(text):
        # Add text before match as regular
        if match.start() > current_pos:
            segments.append((text[current_pos:match.start()], 'regular'))
        # Add matched text as bold
        segments.append((match.group(2), 'bold'))
        current_pos = match.end()
    
    # Add remaining text as regular
    if current_pos < len(text):
        segments.append((text[current_pos:], 'regular'))
    
    return segments if segments else [(text, 'regular')]


def _render_paragraph_with_formatting(
    pdf: canvas.Canvas,
    formatted_segments: List[Tuple[str, str]],
    x: float,
    y: float,
    max_width: float,
    font_size: int,
    line_height: int,
) -> float:
    """Render a paragraph with mixed formatting (bold, regular)."""
    current_y = y
    current_line = []
    current_width = 0
    
    for text, style in formatted_segments:
        # Set font based on style
        if style == 'bold':
            pdf.setFont("Helvetica-Bold", font_size)
        else:
            pdf.setFont("Helvetica", font_size)
        
        # Split text into words
        words = text.split()
        for word in words:
            word_width = pdf.stringWidth(word + ' ', pdf._fontname, font_size)
            
            # Check if word fits on current line
            if current_width + word_width > max_width and current_line:
                # Render current line
                current_y = _render_line_segments(pdf, current_line, x, current_y, font_size, line_height)
                current_line = []
                current_width = 0
            
            current_line.append((word + ' ', style))
            current_width += word_width
    
    # Render remaining line
    if current_line:
        current_y = _render_line_segments(pdf, current_line, x, current_y, font_size, line_height)
    
    return current_y - line_height * 0.3


def _render_bullet_with_formatting(
    pdf: canvas.Canvas,
    formatted_segments: List[Tuple[str, str]],
    x: float,
    y: float,
    max_width: float,
    font_size: int,
    line_height: int,
) -> float:
    """Render a bullet point with mixed formatting."""
    # Draw bullet
    pdf.setFont("Helvetica", font_size)
    pdf.drawString(x, y, "•")
    
    # Render text with indentation
    return _render_paragraph_with_formatting(
        pdf, formatted_segments, x + 0.5 * cm, y, max_width - 0.5 * cm, font_size, line_height
    )


def _render_line_segments(
    pdf: canvas.Canvas,
    segments: List[Tuple[str, str]],
    x: float,
    y: float,
    font_size: int,
    line_height: int,
) -> float:
    """Render a line with mixed bold/regular segments."""
    current_x = x
    
    for text, style in segments:
        if style == 'bold':
            pdf.setFont("Helvetica-Bold", font_size)
        else:
            pdf.setFont("Helvetica", font_size)
        
        pdf.drawString(current_x, y, text)
        current_x += pdf.stringWidth(text, pdf._fontname, font_size)
    
    return y - line_height


def _draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: int,
    leading: int,
) -> float:
    if not text:
        return y
    pdf.setFont("Helvetica", font_size)
    wrapper = textwrap.TextWrapper(width=int(width / (font_size * 0.45)))
    for line in wrapper.wrap(text):
        pdf.drawString(x, y, line)
        y -= leading
    return y


def _draw_bullet_list(
    pdf: canvas.Canvas,
    items: List[str],
    x: float,
    y: float,
    width: float,
    font_size: int,
    leading: int,
) -> float:
    pdf.setFont("Helvetica", font_size)
    for item in items:
        pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
        pdf.circle(x + 0.1 * cm, y + 0.1 * cm, 0.05 * cm, fill=True, stroke=False)
        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        y = _draw_wrapped(pdf, item, x + 0.4 * cm, y, width - 0.4 * cm, font_size, leading)
        y -= 0.2 * cm
    return y


def _draw_eclipse_card(pdf: canvas.Canvas, width: float, y: float, eclipse: Dict[str, Any], bullets: List[str]) -> None:
    pdf.setFillColorRGB(*BRAND_COLORS["crimson_light"])
    pdf.roundRect(PAGE_LAYOUT["margin"], y - 3.6 * cm, width - 2 * PAGE_LAYOUT["margin"], 3.4 * cm, 0.2 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 12)
    # Strip markdown from all eclipse fields
    kind = _strip_markdown(eclipse.get('kind', ''))
    date = eclipse.get('date', '')
    line = f"{date} • {kind}"
    sign = eclipse.get("sign")
    if sign:
        line += f" in {sign}"
    pdf.drawString(PAGE_LAYOUT["margin"] + 0.4 * cm, y - 0.6 * cm, line)
    pdf.setFont("Helvetica", 10)
    house = eclipse.get("house") or eclipse.get("life_area")
    if house:
        # Strip markdown from house/life_area
        house = _strip_markdown(house)
        pdf.drawString(PAGE_LAYOUT["margin"] + 0.4 * cm, y - 1.2 * cm, f"Life Area: {house}")
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    cursor = y - 1.9 * cm
    for bullet in bullets[:4]:
        pdf.drawString(PAGE_LAYOUT["margin"] + 0.4 * cm, cursor, f"• {bullet}")
        cursor -= 0.6 * cm


def _build_eclipse_bullets(eclipse: Dict[str, Any]) -> List[str]:
    bullets: List[str] = []
    house = eclipse.get("house") or eclipse.get("life_area")
    if house:
        # Strip markdown from house/life_area
        house = _strip_markdown(house)
        bullets.append(f"Tend to {house.lower()} shifts.")
    sign = eclipse.get("sign")
    if sign:
        # Strip markdown from sign
        sign = _strip_markdown(sign)
        bullets.append(f"Lean into {sign} traits — do it with that zodiac tone.")
    guidance = eclipse.get("guidance", "")
    # Strip markdown from guidance before processing
    guidance = _strip_markdown(guidance)
    do_line, dont_line = _split_do_dont(guidance)
    if do_line:
        bullets.append(f"Do: {_sanitize_bullet_artifacts(do_line)}")
    if dont_line:
        bullets.append(f"Skip: {_sanitize_bullet_artifacts(dont_line)}")
    if not bullets:
        bullets = ["Observe, rest, and log insights."]
    return bullets


def _render_key_insight(pdf: canvas.Canvas, width: float, y: float, month: Dict[str, Any]) -> float:
    insight = month.get("key_insight")
    if not insight:
        overview = month.get("overview", "")
        sentences = re.split(r"(?<=[.!?]) +", overview)
        insight = sentences[0].strip() if sentences else "Use this month to anchor your next bold step."
    # Strip markdown from insight
    insight = _strip_markdown(insight)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson_light"])
    pdf.roundRect(PAGE_LAYOUT["margin"], y - 1.6 * cm, width - 2 * PAGE_LAYOUT["margin"], 1.4 * cm, 0.2 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson_dark"])
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(PAGE_LAYOUT["margin"] + 0.3 * cm, y - 0.7 * cm, f"Key Insight: {insight[:220]}")
    return y - 2 * cm


def _render_key_dates_table(
    pdf: canvas.Canvas,
    width: float,
    y: float,
    events: List[Dict[str, Any]],
) -> float:
    if not events:
        return y
    table_events = sorted(events, key=lambda ev: -abs(ev.get("score", 0)))[:6]
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Key Dates")
    y -= 0.5 * cm

    col_widths = [3 * cm, 5 * cm, 4 * cm, 2 * cm, (width - 2 * PAGE_LAYOUT["margin"]) - 14 * cm]
    headers = ["Date", "Transit", "Theme", "Score", "Guidance"]
    _draw_table_row(pdf, headers, PAGE_LAYOUT["margin"], y, col_widths, header=True)
    y -= 0.6 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    pdf.setFont("Helvetica", 9)
    for ev in table_events:
        if y < 4 * cm:
            break
        transit = f"{ev.get('transit_body')} {ev.get('aspect')} {ev.get('natal_body') or ''}".strip()
        theme = ev.get("life_area") or _infer_life_area(ev) or "Focus"
        # Strip markdown from theme
        theme = _strip_markdown(theme)
        score = f"{ev.get('score', 0):.2f}"
        guidance = ev.get("user_friendly_summary") or ev.get("raw_note", "")
        # Strip markdown from guidance
        guidance = _strip_markdown(guidance)
        row = [ev.get("date", ""), transit, theme, score, guidance[:90]]
        _draw_table_row(pdf, row, PAGE_LAYOUT["margin"], y, col_widths)
        y -= 0.5 * cm
    return y - 0.4 * cm


def _render_heatbar(pdf: canvas.Canvas, width: float, y: float, events: List[Dict[str, Any]], month_label: str) -> float:
    intensities = _compute_weekly_intensity(events, month_label)
    if not intensities:
        return y
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Weekly Heatbar")
    y -= 0.6 * cm
    start_x = PAGE_LAYOUT["margin"]
    gap = 0.4 * cm
    box_width = 1.2 * cm
    pdf.setLineWidth(0.3)
    for label, intensity in intensities:
        color_scale = BRAND_COLORS["crimson_light"] if intensity < 3 else BRAND_COLORS["crimson"]
        pdf.setFillColorRGB(*color_scale)
        pdf.rect(start_x, y - 0.4 * cm, box_width, 0.4 * cm, fill=True, stroke=False)
        pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
        pdf.setFont("Helvetica", 8)
        pdf.drawCentredString(start_x + box_width / 2, y - 0.55 * cm, f"{label}\n{intensity}/5")
        start_x += box_width + gap
    return y - 1 * cm


def _render_life_area_summary(
    pdf: canvas.Canvas,
    width: float,
    y: float,
    events: List[Dict[str, Any]],
) -> float:
    summary = _summarize_life_areas(events)
    if not summary:
        return y
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(PAGE_LAYOUT["margin"], y, "Life Areas in Focus")
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    pdf.setFont("Helvetica", 10)
    y -= 0.5 * cm
    return _draw_wrapped(pdf, summary, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14) - 0.4 * cm


def _render_subsection_text(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    y: float,
    title: str,
    text: str,
    state: RenderState,
    profile: Dict[str, str],
    section_name: str,
    events: List[Dict[str, Any]],
) -> float:
    if y < 5 * cm:
        _continue_page(pdf, width, height, state, profile)
        y = height - 2.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["crimson"])
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(PAGE_LAYOUT["margin"], y, title)
    y -= 0.5 * cm
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    y = _parse_and_render_markdown(pdf, text, PAGE_LAYOUT["margin"], y, width - 2 * PAGE_LAYOUT["margin"], 10, 14)
    state.record_paragraph_events(section_name, text, events[:2])
    return y - 0.3 * cm


def _render_action_plan(
    pdf: canvas.Canvas,
    width: float,
    y: float,
    actions: List[str],
    events: List[Dict[str, Any]],
) -> float:
    if not actions:
        return y
    pdf.setFillColorRGB(*BRAND_COLORS["crimson_light"])
    box_height = 1.2 * cm + len(actions) * 0.55 * cm
    pdf.roundRect(PAGE_LAYOUT["margin"], y - box_height, width - 2 * PAGE_LAYOUT["margin"], box_height, 0.2 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["crimson_dark"])
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(PAGE_LAYOUT["margin"] + 0.3 * cm, y - 0.6 * cm, "Action Plan (date-tagged)")
    pdf.setFont("Helvetica", 10)
    y -= 1.2 * cm
    for action in actions:
        pdf.drawString(PAGE_LAYOUT["margin"] + 0.4 * cm, y, _ensure_action_format(action))
        y -= 0.5 * cm
    return y - 0.6 * cm


def _render_energy_callouts(
    pdf: canvas.Canvas,
    width: float,
    height: float,
    y: float,
    month: Dict[str, Any],
    profile: Dict[str, str],
    state: RenderState,
) -> None:
    high = _format_day_callouts(month.get("high_score_days", []), top_n=5)
    care = _format_day_callouts(month.get("caution_days", []), top_n=5)
    if not high and not care:
        return
    if y < 5 * cm:
        _continue_page(pdf, width, height, state, profile)
        y = height - 2.5 * cm
    col_width = (width - 2 * PAGE_LAYOUT["margin"] - 1 * cm) / 2
    _draw_callout_box(pdf, PAGE_LAYOUT["margin"], y, col_width, "High Energy Days", high, BRAND_COLORS["energy_green"])
    _draw_callout_box(
        pdf,
        PAGE_LAYOUT["margin"] + col_width + 1 * cm,
        y,
        col_width,
        "Navigate With Care",
        care,
        BRAND_COLORS["care_amber"],
    )


# --------------------------------------------------------------------------------------
# Data prep helpers
# --------------------------------------------------------------------------------------

def _prepare_report(report: Dict[str, Any], validator: ContentValidator) -> Dict[str, Any]:
    """Clean ALL text fields in the report to remove markdown and apply guardrails."""
    cleaned = dict(report)
    
    # Clean monthly sections
    cleaned["months"] = [
        {
            **month,
            "overview": validator.clean_text(month.get("overview", ""), month_label=month.get("month")),
            "career_and_finance": validator.clean_text(month.get("career_and_finance", ""), month_label=month.get("month")),
            "relationships_and_family": validator.clean_text(
                month.get("relationships_and_family", ""), month_label=month.get("month")
            ),
            "health_and_energy": validator.clean_text(month.get("health_and_energy", ""), month_label=month.get("month")),
            "key_insight": validator.clean_text(month.get("key_insight", ""), month_label=month.get("month")),
            "planner_actions": validator.sanitize_actions(month.get("planner_actions", [])),
        }
        for month in report.get("months", [])
    ]
    
    # Clean year at a glance
    yag = report.get("year_at_glance") or {}
    cleaned_top_events = []
    for event in yag.get("top_events", []):
        cleaned_top_events.append({
            **event,
            "title": _strip_markdown(event.get("title", "")),
            "summary": _strip_markdown(event.get("summary", "")),
            "tags": [_strip_markdown(str(tag)) for tag in (event.get("tags", []) or [])]
        })
    
    cleaned["year_at_glance"] = {
        **yag, 
        "commentary": validator.clean_text(yag.get("commentary", "")),
        "top_events": cleaned_top_events
    }
    
    # Clean eclipses and lunations
    # NOTE: Keep markdown in 'guidance' field - it will be parsed and formatted during rendering
    cleaned_eclipses = []
    for eclipse in report.get("eclipses_and_lunations", []):
        cleaned_eclipses.append({
            **eclipse,
            "kind": _strip_markdown(eclipse.get("kind", "")),  # Short label - strip markdown
            "sign": _strip_markdown(eclipse.get("sign", "")),  # Short label - strip markdown
            "house": _strip_markdown(eclipse.get("house", "")),  # Short label - strip markdown
            "life_area": _strip_markdown(eclipse.get("life_area", "")),  # Short label - strip markdown
            # "guidance" is NOT stripped - it's narrative text with markdown formatting
        })
    cleaned["eclipses_and_lunations"] = cleaned_eclipses
    
    # Clean appendix events
    if "appendix_all_events" in report:
        cleaned_events = []
        for event in report.get("appendix_all_events", []):
            cleaned_events.append({
                **event,
                "user_friendly_summary": _strip_markdown(event.get("user_friendly_summary", "")),
                "raw_note": _strip_markdown(event.get("raw_note", "")),
                "life_area": _strip_markdown(event.get("life_area", ""))
            })
        cleaned["appendix_all_events"] = cleaned_events
    
    return cleaned


def _ordered_months(months: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def index(month: Dict[str, Any]) -> int:
        label = month.get("month", "")
        try:
            return MONTH_NAME_ORDER.index(label)
        except ValueError:
            return len(MONTH_NAME_ORDER)

    return sorted(months, key=index)


def _gather_month_events(month: Dict[str, Any]) -> List[Dict[str, Any]]:
    events = []
    for key in ("high_score_days", "caution_days", "aspect_grid", "key_dates"):
        value = month.get(key) or []
        if isinstance(value, list):
            events.extend(value)
    return events


def _aggregate_house_focus(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts: Counter[int] = Counter()
    for event in events:
        house = _normalize_house(event.get("house"))
        if house:
            counts[house] += 1
    if not counts:
        return []
    max_count = max(counts.values())
    focus = []
    for house, count in counts.most_common():
        keywords = HOUSE_KEYWORDS.get(house, "Key life territory")
        intensity = _intensity_label(count, max_count)
        focus.append({"house": house, "keywords": keywords, "intensity": intensity})
    return focus


def _normalize_house(value: Any) -> Optional[int]:
    if isinstance(value, int):
        return value if 1 <= value <= 12 else None
    if isinstance(value, str):
        match = re.search(r"(\d{1,2})", value)
        if match:
            num = int(match.group(1))
            if 1 <= num <= 12:
                return num
    return None


def _intensity_label(count: int, max_count: int) -> str:
    if max_count <= 0:
        return "Trace"
    ratio = count / max_count
    if ratio >= 0.75:
        return "Primary focus"
    if ratio >= 0.45:
        return "Active"
    if ratio >= 0.25:
        return "Background hum"
    return "Trace"


def _derive_month_themes(month: Dict[str, Any]) -> List[str]:
    events = _gather_month_events(month)
    summary = _summarize_life_areas(events)
    if summary:
        return [part.strip() for part in summary.split(";")[:3] if part.strip()]
    return ["Career", "Relationships", "Inner Growth"]


def _format_top_event_line(event: Dict[str, Any]) -> str:
    date = event.get("date") or "Date TBC"
    title = _strip_markdown(event.get("title") or "Transit")
    theme = event.get("tags") or []
    # Strip markdown from theme tags
    theme_clean = [_strip_markdown(str(t)) for t in theme[:2]] if theme else []
    theme_str = " • ".join(theme_clean) if theme_clean else "Impact"
    score = event.get("score")
    score_str = f" (Score: {score:.2f})" if isinstance(score, (int, float)) else ""
    return f"{date} • {title} • {theme_str}{score_str}"


def _summarize_heatmap(heatmap: List[Dict[str, Any]]) -> str:
    if not heatmap:
        return ""
    hottest = sorted(heatmap, key=lambda item: item.get("score", 0), reverse=True)[:2]
    calm = sorted(heatmap, key=lambda item: item.get("score", 0))[:2]
    hot_months = ", ".join([item.get("label", "") for item in hottest if item.get("label")])
    calm_months = ", ".join([item.get("label", "") for item in calm if item.get("label")])
    return f"Peak windows: {hot_months}. Restoration windows: {calm_months}."


def _summarize_high_score_days(days: List[Dict[str, Any]]) -> str:
    if not days:
        return "Use the callout cards below to time bold moves."
    entries = []
    for day in days[:3]:
        entries.append(_format_transit_sentence(day))
    return " ".join(filter(None, entries))


def _format_transit_sentence(event: Dict[str, Any]) -> str:
    date = event.get("date") or "TBC"
    transit = f"{event.get('transit_body')} {event.get('aspect')} {event.get('natal_body') or ''}".strip()
    summary = _sanitize_bullet_artifacts(event.get("user_friendly_summary") or event.get("raw_note") or "brings a noticeable shift.")
    return f"{date}: {transit} — {summary}"


def _split_do_dont(guidance: str) -> Tuple[str, str]:
    if not guidance:
        return ("Focus on grounding steps.", "Avoid multitasking.")
    parts = re.split(r"do:?", guidance, flags=re.IGNORECASE)
    if len(parts) == 2:
        return parts[1].strip(), "Hold steady and avoid extremes."
    return guidance[:90], guidance[90:180] or "Skip rash reactions."


def _extract_retrograde_windows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for event in events:
        note = " ".join(
            filter(
                None,
                [
                    event.get("raw_note"),
                    event.get("user_friendly_summary"),
                    event.get("title"),
                ],
            )
        )
        text = note.lower()
        if "retrograde" not in text and "station" not in text:
            continue
        body = event.get("transit_body") or event.get("title") or "Planet"
        bucket = buckets.setdefault(body, {"start": None, "end": None, "stations": [], "notes": "", "body": body})
        date = event.get("date") or "TBC"
        summary = _sanitize_bullet_artifacts(event.get("user_friendly_summary") or event.get("raw_note") or "")
        if "retrograde" in text:
            bucket["start"] = bucket["start"] or date
            bucket["end"] = date
            if summary:
                bucket["notes"] = summary
        if "station" in text:
            if "retrograde" in text:
                label = "Station retrograde"
            elif "direct" in text:
                label = "Station direct"
            else:
                label = "Station"
            bucket["stations"].append({"date": date, "label": label})
            if "direct" in text:
                bucket["end"] = date
            if "retrograde" in text and not bucket["start"]:
                bucket["start"] = date
    windows = [bucket for bucket in buckets.values() if bucket["start"] or bucket["stations"]]
    return sorted(windows, key=lambda item: item.get("start") or "")


def _format_day_callouts(days: List[Dict[str, Any]], top_n: int) -> List[str]:
    sliced = sorted(days, key=lambda ev: -ev.get("score", 0))[:top_n]
    formatted = []
    for ev in sliced:
        label = _format_transit_sentence(ev)
        clean = _sanitize_bullet_artifacts(label)
        if clean:
            formatted.append(clean)
    return formatted


def _draw_callout_box(
    pdf: canvas.Canvas,
    x: float,
    y: float,
    width: float,
    title: str,
    lines: List[str],
    bg_color: Tuple[float, float, float],
) -> None:
    if not lines:
        return
    box_height = 1.1 * cm + len(lines) * 0.5 * cm
    pdf.setFillColorRGB(*bg_color)
    pdf.roundRect(x, y - box_height, width, box_height, 0.2 * cm, fill=True, stroke=False)
    pdf.setFillColorRGB(*BRAND_COLORS["text_dark"])
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(x + 0.3 * cm, y - 0.6 * cm, title)
    pdf.setFont("Helvetica", 9)
    y -= 1.1 * cm
    for line in lines:
        pdf.drawString(x + 0.3 * cm, y, line[:100])
        y -= 0.45 * cm


def _draw_table_row(
    pdf: canvas.Canvas,
    values: List[str],
    x: float,
    y: float,
    widths: List[float],
    header: bool = False,
) -> None:
    font = "Helvetica-Bold" if header else "Helvetica"
    size = 10 if header else 9
    pdf.setFont(font, size)
    fill = BRAND_COLORS["crimson"] if header else BRAND_COLORS["text_dark"]
    pdf.setFillColorRGB(*fill)
    cursor = x
    for value, width_part in zip(values, widths):
        pdf.drawString(cursor + 0.1 * cm, y, (value or "")[:120])
        cursor += width_part


def _format_generated_at(generated_at: str) -> str:
    try:
        dt = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        return f"Generated {dt.strftime('%d %B %Y %H:%M %Z')}"
    except ValueError:
        return f"Generated {generated_at}"


def _compute_weekly_intensity(events: List[Dict[str, Any]], month_label: str) -> List[Tuple[str, int]]:
    if not events:
        return []
    buckets: Dict[str, List[float]] = {}
    for ev in events:
        date = ev.get("date") or ""
        if len(date) < 10:
            continue
        try:
            dt = datetime.fromisoformat(date[:10])
        except ValueError:
            continue
        week = (dt.day - 1) // 7 + 1
        key = f"W{week}"
        buckets.setdefault(key, []).append(abs(ev.get("score", 0)))
    ordered = sorted(buckets.items(), key=lambda kv: kv[0])
    return [(key, min(5, max(1, round(sum(vals) / len(vals) / 2)))) for key, vals in ordered]


def _summarize_life_areas(events: List[Dict[str, Any]]) -> str:
    if not events:
        return ""
    counts: Dict[str, int] = {}
    for ev in events:
        area = _infer_life_area(ev)
        if area:
            counts[area] = counts.get(area, 0) + 1
    if not counts:
        return ""
    strongest = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
    active = ", ".join(area.title() for area, _ in strongest[:3])
    quiet = ", ".join(area.title() for area, _ in strongest[-2:])
    return f"Strong: {active}. Quieter: {quiet}."


def _infer_life_area(event: Dict[str, Any]) -> Optional[str]:
    explicit = event.get("life_area")
    if explicit:
        return explicit.lower()
    text = " ".join(
        filter(
            None,
            [event.get("transit_body"), event.get("natal_body"), event.get("user_friendly_summary"), event.get("raw_note")],
        )
    ).lower()
    for area, keywords in LIFE_AREA_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return area
    return None


def _ensure_action_format(action: str) -> str:
    match = re.match(r"(\d{1,2})\s*([A-Za-z]{3,})", action)
    if match:
        return f"{match.group(1)} {match.group(2)} – {action[match.end():].strip()}"
    return action


def _split_month_label(month_label: str) -> Tuple[str, str]:
    if not month_label:
        return ("", "")
    parts = month_label.split()
    if len(parts) >= 2:
        return parts[0], parts[-1]
    return month_label, ""


def _extract_profile(meta: Dict[str, Any]) -> Dict[str, str]:
    birth = meta.get("birth_info") or {}
    name = meta.get("profile_name") or meta.get("user_id") or "John"
    sun_sign = meta.get("sun_sign") or birth.get("sun_sign") or "Taurus"
    birth_date = birth.get("date") or meta.get("birth_date") or "15 May 1990"
    birth_time = birth.get("time") or meta.get("birth_time") or "14:30"
    birth_place = birth.get("place") or meta.get("birth_place") or "New Delhi (India)"
    year = int(meta.get("target_year") or meta.get("year") or datetime.utcnow().year)
    return {
        "name": name,
        "sun_sign": sun_sign,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "birth_place": birth_place,
        "year": year,
    }


def _slugify(value: str, suffix: str = "") -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    if suffix:
        value = f"{value}-{suffix}"
    return value or "section"


__all__ = ["render_enhanced_yearly_pdf"]
