"""Interpret yearly forecast payloads into narrative report sections."""

from __future__ import annotations

import asyncio
import datetime as dt
import re
import os
import logging
from typing import Any, Dict, Iterable, List, Optional, Set

from ..schemas.yearly_forecast_report import (
    EclipseSummary,
    EventSummary,
    MonthlySection,
    TopEventSummary,
    YearAtGlance,
    YearlyForecastReport,
)
from .llm_client import LLMUnavailableError, generate_section_text

logger = logging.getLogger(__name__)

# Rate limiting: Max concurrent LLM calls across all users
# OpenAI API limits by tier:
# - Tier 1 (Free): 500 RPM = ~8/second
# - Tier 2 ($5+ spent): 3,500 RPM = ~58/second
# - Tier 3 ($50+ spent): 3,500 RPM = ~58/second
# - Tier 4 ($100+ spent): 10,000 RPM = ~166/second
# - Tier 5 ($1000+ spent): 10,000 RPM = ~166/second
# 
# For paid service: Set to 50-100 concurrent calls (safe for Tier 2+)
# For production: Increase to 100-200 (Tier 3+)
MAX_CONCURRENT_LLM_CALLS = int(os.getenv("MAX_CONCURRENT_LLM_CALLS", "100"))
_llm_semaphore = asyncio.Semaphore(MAX_CONCURRENT_LLM_CALLS)

SUPPORTIVE_ASPECTS = {"trine", "sextile", "conjunction"}
CHALLENGING_ASPECTS = {"square", "opposition", "quincunx"}

SYSTEM_PROMPT = """You are a renowned astrologer writing for WhatHoroscope, a trusted platform known for empowering, practical astrological guidance.

BRAND VOICE & TONE:
- Empowering, not fatalistic: Frame challenges as opportunities for growth
- Warm & personal: Use second person ("you") and conversational language
- Practical & actionable: Focus on specific steps the reader can take
- Optimistic but realistic: Acknowledge difficulties while emphasizing agency
- Professional but accessible: Avoid overly technical jargon

OUTPUT REQUIREMENTS - MARKDOWN FORMATTING:
- Headings (end at newline, NO closing tag):
  * ### Heading Text (one line only, creates H3 section heading)
  * #### Sub-Heading (one line only, creates H4 sub-section)
  * Always add a BLANK LINE after headings before starting paragraph text
  
- Paragraphs (use blank lines to separate):
  * Write 2-4 sentences of regular text
  * Press ENTER TWICE (blank line) to start a new paragraph
  * Single newlines within a paragraph will word-wrap together
  
- Emphasis:
  * **bold text** for key dates (e.g., **January 15**), important insights, theme names
  * Use bold liberally but purposefully
  
- Lists:
  * - Bullet item (use for action steps, key points)
  * Add blank line before and after bullet lists
  
EXAMPLE FORMAT:
### Career Highlights
(blank line)
This month brings three major career transits. **Mars enters your 10th house on January 5**, energizing your professional goals.
(blank line)
Around **January 15**, a Full Moon illuminates achievements and completion. This is your moment to shine.
(blank line)
#### Action Steps
(blank line)
- Update your resume and LinkedIn profile before **January 5**
- Schedule a meeting with your manager around **January 15**
- Network at industry events during the third week
(blank line)

- Structure: Clear headings, short paragraphs (2-4 sentences), bullet lists for actions
- Length: Concise and focused (avoid rambling or filler phrases like "Absolutely!", "Here are some...")
- Specificity: Reference specific dates, transits, and life areas when possible

WHAT TO AVOID:
- Fatalistic predictions ("you will...", "this guarantees...")
- Medical advice or diagnoses
- Financial guarantees or investment advice
- Generic advice that could apply to anyone
- Overly dramatic or fear-based language
- Chatbot-style responses ("As you step into...", "Here's what...")

WHAT TO INCLUDE:
- Specific transit dates and their themes
- Concrete action steps tied to the astrology
- Both opportunities and challenges for each area
- Encouragement for the reader's personal agency
- Practical rituals, journaling prompts, or reflection questions"""


_THEMES: Dict[str, Set[str]] = {
    # Work, public role, achievement, status (10th house)
    "career": {
        "mc", "midheaven", "10th house",
        "saturn", "sun", "mars", "jupiter",
        "capricorn",
    },
    
    # Income, savings, assets, shared money (2nd & 8th houses)
    "money": {
        "2nd house", "8th house",
        "taurus", "scorpio",
        "venus", "pluto", "jupiter",
    },
    
    # Dating, romance, partnership, one-to-one relationships (7th house)
    "love": {
        "venus", "moon",
        "7th house", "descendant",
        "juno",
        "libra",
    },
    
    # Family, home, living situation, roots, parents (4th house)
    "home_family": {
        "4th house", "ic",
        "cancer", "moon",
        "north node in 4th", "south node in 10th",
    },
    
    # Friendships, networks, community, future goals, social circles (11th house)
    "community_goals": {
        "11th house",
        "aquarius",
        "uranus", "jupiter", "saturn",
    },
    
    # Creativity, children, hobbies, pleasure, self-expression (5th house)
    "creativity_children": {
        "5th house",
        "leo", "sun", "venus",
    },
    
    # Health, routines, work habits, service, daily life (6th house)
    "health_routines": {
        "6th house",
        "virgo",
        "chiron", "mars", "saturn",
        "ascendant",
    },
    
    # Mindset, communication, siblings, short trips, learning (3rd house)
    "mindset_communication": {
        "3rd house",
        "mercury", "gemini",
    },
    
    # Study, travel, publishing, beliefs, higher education (9th house)
    "study_travel": {
        "9th house",
        "sagittarius",
        "jupiter",
    },
    
    # Inner work, subconscious, rest, retreat, spirituality (12th house)
    "inner_spiritual": {
        "12th house",
        "pisces",
        "neptune", "pluto",
        "true node", "south node",
    },
    
    # Tech, disruption, innovation, experimentation, sudden change
    "innovation": {
        "uranus",
        "aquarius",
        "mercury",
    },
}


def classify_event(event: Dict[str, Any]) -> Set[str]:
    """Assign high-level themes to an event using simple heuristics."""

    themes: Set[str] = set()
    note = (event.get("note") or "").lower()
    bodies = {str(event.get("transit_body", "")).lower(), str(event.get("natal_body", "")).lower()}
    for theme, markers in _THEMES.items():
        if bodies & markers:
            themes.add(theme)
    # Career & public life
    if any(tok in note for tok in ["career", "work", "job", "promotion", "profession", "status", "reputation", "authority", "boss", "achievement"]):
        themes.add("career")
    
    # Money & resources
    if any(tok in note for tok in ["money", "income", "finance", "salary", "wealth", "assets", "savings", "investment", "debt", "inheritance"]):
        themes.add("money")
    
    # Love & romance
    if any(tok in note for tok in ["love", "romance", "dating", "attraction", "partner", "soulmate", "marriage", "commitment", "relationship", "intimacy"]):
        themes.add("love")
    
    # Home & family
    if any(tok in note for tok in ["home", "family", "parent", "mother", "father", "property", "living", "domestic", "roots", "foundation"]):
        themes.add("home_family")
    
    # Community & future goals
    if any(tok in note for tok in ["friend", "friendship", "network", "community", "group", "social", "circle", "future", "aspiration", "hope"]):
        themes.add("community_goals")
    
    # Creativity & children
    if any(tok in note for tok in ["creative", "creativity", "child", "children", "hobby", "fun", "pleasure", "joy", "expression", "art"]):
        themes.add("creativity_children")
    
    # Health & routines
    if any(tok in note for tok in ["health", "vitality", "wellness", "routine", "habit", "service", "work", "daily", "diet", "exercise"]):
        themes.add("health_routines")
    
    # Mindset & communication
    if any(tok in note for tok in ["think", "thought", "mindset", "communicate", "communication", "sibling", "neighbor", "learn", "study", "teach"]):
        themes.add("mindset_communication")
    
    # Study & travel
    if any(tok in note for tok in ["travel", "journey", "adventure", "explore", "belief", "philosophy", "education", "publish", "abroad", "foreign"]):
        themes.add("study_travel")
    
    # Inner & spiritual
    if any(tok in note for tok in ["spiritual", "intuition", "dream", "subconscious", "meditation", "retreat", "solitude", "karma", "healing", "psychic"]):
        themes.add("inner_spiritual")
    
    # Innovation & change
    if any(tok in note for tok in ["change", "innovation", "technology", "tech", "disrupt", "reinvent", "pivot", "sudden", "unexpected", "revolution"]):
        themes.add("innovation")
    return themes or {"general"}


def _event_summary(event: Dict[str, Any]) -> EventSummary:
    themes = classify_event(event)
    return EventSummary(
        date=dt.date.fromisoformat(str(event.get("date"))),
        transit_body=str(event.get("transit_body")),
        natal_body=event.get("natal_body"),
        aspect=event.get("aspect"),
        score=float(event.get("score", 0.0)),
        raw_note=str(event.get("note") or ""),
        section=next(iter(themes)),
        user_friendly_summary=str(event.get("note") or ""),
    )


def _build_heatmap(months: Dict[str, List[EventSummary]]) -> List[Dict[str, Any]]:
    heatmap = []
    for month, events in months.items():
        intensity = sum(abs(ev.score) for ev in events)
        peak_score = max((ev.score for ev in events), default=0.0)
        heatmap.append({"month": month, "intensity": intensity, "peak_score": peak_score})
    return sorted(heatmap, key=lambda item: item["month"])


def _extract_eclipses(events: Iterable[EventSummary]) -> List[EclipseSummary]:
    """Extract eclipse/lunation events WITH our calculated interpretations.
    
    The engine already calculates the astrological interpretation in ev.raw_note.
    We extract sign/house from the event data, and keep OUR interpretation as guidance.
    LLM will only REPHRASE for readability, not generate new astrological content.
    """
    eclipses: List[EclipseSummary] = []
    for ev in events:
        note = ev.raw_note.lower()
        aspect_lower = (ev.aspect or "").lower()
        
        # Check if this is an eclipse or lunation event
        is_eclipse_event = (
            "eclipse" in aspect_lower or
            "eclipse" in note or
            "lunar_phase" in aspect_lower or
            "new moon" in note or
            "full moon" in note
        )
        
        if not is_eclipse_event:
            continue
        
        # Extract sign from transit_body (e.g., "Sun in Aries" -> "Aries")
        sign = None
        if " in " in ev.transit_body:
            parts = ev.transit_body.split(" in ")
            if len(parts) == 2:
                sign = parts[1].strip()
        
        # Use section as house/life area (this is calculated by classify_event)
        house = ev.section or None
        
        # Determine kind with better classification
        kind = "lunar_phase"  # Default
        
        if "solar eclipse" in note:
            kind = "Solar Eclipse"
        elif "lunar eclipse" in note:
            kind = "Lunar Eclipse"
        elif "eclipse" in aspect_lower:
            # Check transit_body to determine if solar or lunar
            if "sun" in ev.transit_body.lower():
                kind = "Solar Eclipse"
            elif "moon" in ev.transit_body.lower():
                kind = "Lunar Eclipse"
            else:
                kind = "Eclipse"
        elif "new moon" in note:
            kind = "New Moon"
        elif "full moon" in note:
            kind = "Full Moon"
        elif "lunar_phase" in aspect_lower:
            # Try to determine from transit_body or note
            if "new moon" in ev.transit_body.lower():
                kind = "New Moon"
            elif "full moon" in ev.transit_body.lower():
                kind = "Full Moon"
        
        # Use OUR calculated interpretation (from engine), not LLM-generated content
        # The raw_note contains the astrological calculation - this is TRUTH
        guidance = ev.user_friendly_summary or ev.raw_note
        
        eclipse = EclipseSummary(
            date=ev.date,
            kind=kind,
            sign=sign,
            house=house,
            guidance=guidance,  # OUR calculated interpretation from engine
        )
        
        eclipses.append(eclipse)
        
        # LOG each eclipse extraction for debugging
        logger.debug(
            f"ECLIPSE_EXTRACTED: {ev.date} kind={kind} sign={sign} house={house} " +
            f"aspect={ev.aspect} transit={ev.transit_body} note_preview={ev.raw_note[:50]}"
        )
    
    logger.info(f"TOTAL_ECLIPSES_EXTRACTED: {len(eclipses)}")
    return eclipses


def build_year_overview_prompt(meta: Dict[str, Any], top_events: List[TopEventSummary], heatmap: List[Dict[str, Any]]) -> str:
    year = meta.get("target_year", "this year")
    top_3_events = [f"- {e.title} on {e.date}: {e.summary} (score: {e.score:.2f})" for e in top_events[:3]]
    peak_months = sorted(heatmap, key=lambda x: x["intensity"], reverse=True)[:3]
    
    return f"""Write a Year at a Glance overview for {year}. This is the opening section of the annual report.

KEY EVENTS (top 3):
{chr(10).join(top_3_events)}

INTENSITY PEAKS:
- Most active months: {', '.join([m['month'] for m in peak_months])}

INSTRUCTIONS:
- Start with a welcoming, empowering opening (2-3 sentences)
- Add a blank line, then highlight the 2-3 major themes or turning points of the year
- Use ### for section headings if needed
- Add blank lines between paragraphs for readability
- Keep total length to 200-250 words
- End with an encouraging note about the reader's ability to navigate the year"""


def build_month_overview_prompt(month_key: str, month_events: List[EventSummary], themes: Set[str]) -> str:
    top_events = [
        f"- {ev.date.isoformat()}: {ev.transit_body} {ev.aspect} {ev.natal_body} (score: {ev.score:.2f})"
        for ev in month_events[:5]
    ]
    
    # Extract year from month_key (format: "YYYY-MM")
    year = month_key.split('-')[0] if '-' in month_key else "this year"
    month_num = month_key.split('-')[1] if '-' in month_key else ""
    is_december = month_num == "12"
    
    # Year guidance: Always reference the target year, special wording for December
    if is_december:
        year_guidance = f"\n- This is December {year} - the final month of {year}. Naturally reference closing out {year} and looking ahead to next year"
    else:
        year_guidance = f"\n- This is {month_key}. Always reference {year} as the current year (NEVER mention {int(year)-1} or other years)"
    
    return f"""Write a monthly overview for {month_key}. This is the opening section for this month in the yearly report.

KEY THEMES: {', '.join(sorted(themes))}

TOP 5 TRANSITS:
{chr(10).join(top_events)}

INSTRUCTIONS:
- Start with 1-2 sentences setting the overall tone/energy of the month
- Add a blank line, then mention the 2-3 most significant transits with specific dates
- Use #### for any subheadings (e.g., "#### Major Shifts")
- Add blank lines between paragraphs
- Reference all major themes: {', '.join(sorted(themes))}{year_guidance}
- Keep total length to 150-180 words
- End with an actionable insight or encouragement"""


def build_section_prompt(month_key: str, theme: str, events_for_theme: List[EventSummary]) -> str:
    if not events_for_theme:
        return f"""Write a brief {theme} section for {month_key}.

INSTRUCTIONS:
- Since there are no major transits for this theme this month, write 2-3 sentences about maintaining steady progress
- Keep it positive and encouraging (50-80 words)"""
    
    event_details = [
        f"- {ev.date.isoformat()}: {ev.transit_body} {ev.aspect} {ev.natal_body} (score: {ev.score:.2f})"
        for ev in events_for_theme[:5]
    ]
    
    theme_guidance = {
        "career and finance": "Professional growth, work achievements, public reputation, income, financial decisions, resources, and money matters",
        "love and romance": "Dating, attraction, romantic partnerships, intimacy, commitment. Address both singles (meeting someone) and couples (deepening bonds)",
        "home and family": "Home life, family dynamics, living situation, roots, parents, property, domestic matters, and community connections",
        "health and routines": "Physical health, wellness, daily routines, work habits, service, diet, exercise, and vitality",
        "growth and learning": "Education, travel, creativity, hobbies, self-expression, communication, mindset, and personal development",
        "inner work and innovation": "Spirituality, inner work, subconscious patterns, meditation, intuition, and innovative breakthroughs or unexpected changes"
    }
    
    return f"""Write guidance for {theme} in {month_key}.

THEME FOCUS: {theme_guidance.get(theme, "Focus on this life area")}

RELEVANT TRANSITS:
{chr(10).join(event_details)}

INSTRUCTIONS:
- Start with the overall theme/trend for this area (1-2 sentences)
- Add a blank line, then highlight the most significant transit with its date
- Add a blank line, then provide 2-3 specific, actionable suggestions
- Use **bold** for key insights or dates
- Keep total length to 100-130 words
- Be practical and empowering"""


def build_eclipse_guide_prompt(eclipse_events: List[EclipseSummary]) -> str:
    """Generate comprehensive eclipse guidance with markdown formatting."""
    if not eclipse_events:
        # Fallback if no eclipses detected
        return (
            "Create a guide to eclipses and lunations for the year. "
            "Explain how eclipses accelerate endings and beginnings, and how lunations (New/Full Moons) "
            "mark monthly cycles of intention-setting and release. "
            "Include: ### Full Moons (culmination/release), ### New Moons (fresh starts), "
            "### Eclipses (3-6x more potent). Add practical rituals for each. 200-300 words."
        )
    
    # Format eclipse dates for the prompt
    eclipse_dates = ", ".join([f"{e.date.strftime('%B %d')}" for e in eclipse_events[:6]])
    
    return (
        f"Write a comprehensive guide to eclipses and lunations for this year. "
        f"Key eclipse dates include: {eclipse_dates}. "
        "Structure your response with markdown:\n\n"
        "### Full Moons: Culmination and Release\n"
        "Explain how Full Moons illuminate what's been building. Add 3-4 practical rituals.\n\n"
        "### New Moons: Fresh Starts\n"
        "Explain how New Moons are ideal for intention-setting. Add 3-4 practical rituals.\n\n"
        "### Eclipses: Accelerated Change\n"
        "Explain how eclipses are 3-6x more potent than regular lunations. Add specific guidance.\n\n"
        "Use **bold** for key dates and concepts. Keep tone empowering, not fatalistic. 250-350 words total."
    )


def build_rituals_prompt(month_key: str, key_themes: Set[str], hot_days: List[EventSummary], caution_days: List[EventSummary]) -> str:
    return (
        f"Suggest rituals and journal prompts for {month_key}."
        f" Themes: {sorted(key_themes)}. Hot days: {[e.date.isoformat() for e in hot_days[:3]]}."
        f" Caution days: {[e.date.isoformat() for e in caution_days[:3]]}."
    )


def build_eclipse_rephrase_prompt(eclipse: EclipseSummary) -> str:
    """Rephrase our calculated eclipse guidance for better readability.
    
    IMPORTANT: The LLM does NOT generate astrological content.
    It only REPHRASES our calculated guidance (from the engine) to make it more user-friendly.
    """
    date_str = eclipse.date.strftime("%B %d, %Y")
    kind = eclipse.kind.replace("_", " ").title()
    
    # Build context string
    context_parts = []
    if eclipse.sign:
        context_parts.append(f"in {eclipse.sign}")
    if eclipse.house:
        house_name = eclipse.house.replace("_", " ").title()
        context_parts.append(f"(affects {house_name})")
    
    context = " ".join(context_parts) if context_parts else ""
    
    # Our calculated guidance from the engine (TRUTH)
    original_guidance = eclipse.guidance
    
    return f"""Rephrase the following astrological interpretation to make it more readable and actionable for users.

EVENT: {kind} on {date_str} {context}
ORIGINAL INTERPRETATION (from astrological calculation):
"{original_guidance}"

YOUR TASK:
- Rephrase the above interpretation in 50-80 words
- Keep ALL astrological facts from the original (planets, aspects, houses, dates)
- Make it warm, personal, and actionable (use "you", add 1-2 action suggestions)
- Use plain text only (NO markdown: no **, no ###, no formatting)
- DO NOT add new astrological interpretations - only rephrase what's given

EXAMPLE:
Original: "Solar Eclipse conjunction Midheaven. Career reset. Structure change possible."
Rephrased: "This Solar Eclipse activates your career sector, bringing a powerful reset to your professional path. Old job structures may shift, making room for new opportunities. Use this energy to clarify your long-term goals and take one concrete step toward your true calling."

Now rephrase the above interpretation:"""


def build_planner_actions_prompt(month_key: str, high_score_days: List[EventSummary], caution_days: List[EventSummary]) -> str:
    """Generate planner action items prompt."""
    high_dates = [f"{e.date.strftime('%B %d')} ({e.section})" for e in high_score_days[:4]]
    caution_dates = [f"{e.date.strftime('%B %d')} ({e.aspect})" for e in caution_days[:3]]
    
    return f"""Generate 4-6 specific action items for {month_key} calendar planning.

KEY HIGH-ENERGY DATES: {', '.join(high_dates) if high_dates else 'None'}
CAUTION DATES: {', '.join(caution_dates) if caution_dates else 'None'}

REQUIREMENTS:
- Each action must be a SINGLE line starting with a date or time range
- Format: "Month Day: Action verb + specific task"
- NO markdown formatting (no ###, no **, no blank lines)
- NO section headers or labels
- NO explanations or descriptions
- Just the action items, one per line

EXAMPLE FORMAT:
January 3: Set intentions for your career goals and update your vision board
January 15-17: Schedule important meetings during this high-energy window
January 23: Practice self-care and avoid overcommitting to social events
January 28-31: Focus on financial planning and review your budget

Now generate 4-6 actions for {month_key}:"""
    
    
async def _call_llm(user_prompt: str, max_tokens: int = 800, context: str = "") -> str:
    """Call LLM with rate limiting and return markdown-formatted response.
    
    Rate limiting ensures:
    - No more than MAX_CONCURRENT_LLM_CALLS active at once (across all users)
    - Prevents OpenAI rate limit errors (429)
    - Controls costs during high-traffic periods
    
    Markdown will be parsed and formatted by the PDF renderer:
    - **bold** → bold text
    - ### heading → H3 style
    - #### heading → H4 style
    - Newlines preserved for paragraph breaks
    """
    async with _llm_semaphore:
        try:
            # LOG INPUT PROMPT
            logger.info(f"LLM_PROMPT [{context}]: len={len(user_prompt)} max_tokens={max_tokens}")
            logger.debug(f"LLM_PROMPT_FULL [{context}]: {user_prompt}")
            
            response = await generate_section_text(SYSTEM_PROMPT, user_prompt, max_tokens=max_tokens)
            
            # LOG OUTPUT RESPONSE
            logger.info(f"LLM_RESPONSE [{context}]: len={len(response)} words={len(response.split())}")
            logger.debug(f"LLM_RESPONSE_FULL [{context}]: {response}")
            
            return response
        except LLMUnavailableError as e:
            # Log the actual error reason
            logger.error(f"❌ LLM_FAILED [{context}]: {str(e)}")
            logger.error(f"LLM failure reason: {type(e).__name__}: {str(e)}")
            return ""
        except Exception as e:
            # Catch any other unexpected errors
            logger.error(f"❌ LLM_UNEXPECTED_ERROR [{context}]: {type(e).__name__}: {str(e)}")
            return ""


def _fallback_paragraph(title: str, month_key: Optional[str] = None) -> str:
    if month_key:
        return f"{month_key}: Focus on steady progress, listen to your rhythms, and stay flexible."
    return f"{title}: Stay curious, grounded, and avoid drastic decisions without reflection."


async def _generate_bullets(prompt: str, fallback: List[str], context: str = "bullets") -> List[str]:
    """Generate bullet points from LLM, stripping any markdown formatting."""
    raw = await _call_llm(prompt, max_tokens=300, context=context)
    if not raw:
        return fallback
    
    # Split into lines and clean
    lines = raw.splitlines()
    bullets = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines, markdown headers, and formatting instructions
        if not line:
            continue
        if line.startswith("#"):  # Skip markdown headers
            continue
        if "(blank line)" in line.lower():  # Skip formatting instructions
            continue
        if line.startswith("**") and line.endswith("**"):  # Skip bold-only lines (likely headers)
            continue
        
        # Strip bullet markers and markdown
        line = line.strip("-•* ")
        line = line.replace("**", "")  # Strip bold markers
        line = line.replace("__", "")  # Strip underline markers
        
        # Only include if it's substantial (not just whitespace or very short)
        if len(line) > 15:
            bullets.append(line.strip())
    
    return bullets[:8] if bullets else fallback


async def _generate_month_section(month_key: str, events: List[EventSummary]) -> MonthlySection:
    themes: Set[str] = set(ev.section or "general" for ev in events)
    high_score_days = sorted(events, key=lambda e: -e.score)[:8]
    caution_days = [e for e in events if (e.aspect or "").lower() in CHALLENGING_ASPECTS][:6]

    # LOG event sections for debugging
    section_counts = {}
    for ev in events:
        section = ev.section or "none"
        section_counts[section] = section_counts.get(section, 0) + 1
    logger.info(f"MONTH_{month_key}_SECTIONS: {section_counts}")

    # Build all prompts
    overview_prompt = build_month_overview_prompt(month_key, events, themes)
    
    # Separate events by ALL 11 themes
    theme_events = {
        "career": [e for e in events if e.section == "career"],
        "money": [e for e in events if e.section == "money"],
        "love": [e for e in events if e.section == "love"],
        "home_family": [e for e in events if e.section == "home_family"],
        "community_goals": [e for e in events if e.section == "community_goals"],
        "creativity_children": [e for e in events if e.section == "creativity_children"],
        "health_routines": [e for e in events if e.section == "health_routines"],
        "mindset_communication": [e for e in events if e.section == "mindset_communication"],
        "study_travel": [e for e in events if e.section == "study_travel"],
        "inner_spiritual": [e for e in events if e.section == "inner_spiritual"],
        "innovation": [e for e in events if e.section == "innovation"],
    }
    
    # LOG theme event counts
    theme_counts = {k: len(v) for k, v in theme_events.items() if v}
    logger.info(f"MONTH_{month_key}_THEME_EVENTS: {theme_counts}")
    
    # DYNAMIC: Generate sections with ANY events (even 1 event is enough for meaningful guidance)
    # Core life areas (career, love, home, health) should ALWAYS be generated
    # Set MIN_EVENTS_FOR_SECTION=0 to always generate all sections regardless of events
    MIN_EVENTS_FOR_SECTION = int(os.getenv("MIN_EVENTS_FOR_SECTION", "1"))  # Lowered from 3 to 1
    MIN_SCORE_FOR_SECTION = float(os.getenv("MIN_SCORE_FOR_SECTION", "0.5"))  # Lowered from 0.7 to 0.5
    
    # Core life areas that should ALWAYS be generated (user expectations)
    CORE_SECTIONS = {"career", "love", "home_family", "health_routines"}
    
    def should_generate_section(events_list, theme_key=None):
        # Core sections always generate (even with 0 events - LLM will provide general guidance)
        if theme_key in CORE_SECTIONS:
            return True
        
        # For other sections, check if there are ANY events
        if not events_list:
            return False
        if len(events_list) >= MIN_EVENTS_FOR_SECTION:
            return True
        # Check if any event is high-scoring
        return any(e.score >= MIN_SCORE_FOR_SECTION for e in events_list)
    
    # Group themes for combined sections (backward compatible)
    career_finance_events = theme_events["career"] + theme_events["money"]
    love_romance_events = theme_events["love"]
    home_family_events = theme_events["home_family"] + theme_events["community_goals"]
    health_routines_events = theme_events["health_routines"]
    growth_learning_events = (theme_events["study_travel"] + 
                               theme_events["mindset_communication"] + 
                               theme_events["creativity_children"])
    inner_work_events = theme_events["inner_spiritual"] + theme_events["innovation"]
    
    # Build prompts for sections with significant events
    prompts = []
    
    # Always generate overview
    prompts.append(("overview", _call_llm(overview_prompt, context=f"{month_key}_overview")))
    
    # Career & Finance (CORE - always generate)
    if should_generate_section(career_finance_events, "career"):
        prompts.append(("career_and_finance", _call_llm(
            build_section_prompt(month_key, "career and finance", career_finance_events or []),
            context=f"{month_key}_career"
        )))
    
    # Love & Romance (CORE - always generate)
    if should_generate_section(love_romance_events, "love"):
        prompts.append(("love_and_romance", _call_llm(
            build_section_prompt(month_key, "love and romance", love_romance_events or []),
            context=f"{month_key}_love"
        )))
    
    # Home & Family (CORE - always generate)
    if should_generate_section(home_family_events, "home_family"):
        prompts.append(("home_and_family", _call_llm(
            build_section_prompt(month_key, "home and family", home_family_events or []),
            context=f"{month_key}_home"
        )))
    
    # Health & Routines (CORE - always generate)
    if should_generate_section(health_routines_events, "health_routines"):
        prompts.append(("health_and_routines", _call_llm(
            build_section_prompt(month_key, "health and routines", health_routines_events or []),
            context=f"{month_key}_health"
        )))
    
    # Growth & Learning (optional - only if events exist)
    if should_generate_section(growth_learning_events):
        prompts.append(("growth_and_learning", _call_llm(
            build_section_prompt(month_key, "growth and learning", growth_learning_events),
            context=f"{month_key}_growth"
        )))
    
    # Inner Work (optional - only if events exist)
    if should_generate_section(inner_work_events):
        prompts.append(("inner_work", _call_llm(
            build_section_prompt(month_key, "inner work and innovation", inner_work_events),
            context=f"{month_key}_inner"
        )))
    
    # Always generate rituals and planner
    prompts.append(("rituals_and_journal", _call_llm(
        build_rituals_prompt(month_key, themes, high_score_days, caution_days),
        context=f"{month_key}_rituals"
    )))
    
    # Build planner actions prompt (more explicit instructions to avoid markdown echoing)
    planner_prompt = build_planner_actions_prompt(month_key, high_score_days, caution_days)
    prompts.append(("planner_actions", _generate_bullets(
        planner_prompt,
        ["Mark key dates and pace your commitments."],
        context=f"{month_key}_planner"
    )))
    
    # Execute only the relevant LLM calls in parallel
    section_names, section_tasks = zip(*prompts) if prompts else ([], [])
    
    # LOG which sections will be generated
    logger.info(f"MONTH_{month_key}_SECTIONS_TO_GENERATE: {list(section_names)}")
    
    section_results = await asyncio.gather(*section_tasks) if section_tasks else []
    
    # Map results back to section names
    results = dict(zip(section_names, section_results))
    
    # LOG which sections have content
    sections_with_content = {k: len(v) if isinstance(v, str) else len(v) if isinstance(v, list) else 0 
                             for k, v in results.items() if v}
    logger.info(f"MONTH_{month_key}_SECTIONS_GENERATED: {sections_with_content}")
    
    # Extract with fallbacks
    overview_text = results.get("overview", "")
    career_text = results.get("career_and_finance", "")
    love_text = results.get("love_and_romance", "")
    family_text = results.get("home_and_family", "")
    health_text = results.get("health_and_routines", "")
    growth_text = results.get("growth_and_learning", "")
    inner_text = results.get("inner_work", "")
    rituals_text = results.get("rituals_and_journal", "")
    planner_bullets = results.get("planner_actions", [])

    return MonthlySection(
        month=month_key,
        overview=overview_text or _fallback_paragraph("Overview", month_key),
        high_score_days=high_score_days,
        caution_days=caution_days,
        career_and_finance=career_text or _fallback_paragraph("Career & Finance", month_key),
        love_and_romance=love_text or _fallback_paragraph("Love & Romance", month_key),
        home_and_family=family_text or _fallback_paragraph("Home & Family", month_key),
        health_and_routines=health_text or _fallback_paragraph("Health & Routines", month_key),
        growth_and_learning=growth_text or _fallback_paragraph("Growth & Learning", month_key),
        inner_work=inner_text or _fallback_paragraph("Inner Work", month_key),
        aspect_grid=[
            {
                "date": ev.date.isoformat(),
                "transit": ev.transit_body,
                "natal": ev.natal_body,
                "aspect": ev.aspect,
                "score": ev.score,
            }
            for ev in events[:20]
        ],
        rituals_and_journal=rituals_text or _fallback_paragraph("Rituals", month_key),
        planner_actions=planner_bullets,
    )


async def interpret_yearly_forecast(raw_result: Dict[str, Any]) -> YearlyForecastReport:
    # Get target year from meta
    meta = raw_result.get("meta", {})
    target_year = str(meta.get("target_year") or meta.get("year", ""))
    
    # Get all months from raw result
    months_raw: Dict[str, List[Dict[str, Any]]] = raw_result.get("months", {}) or {}
    
    # FILTER: Only include months from the target year (exclude previous year's December)
    # Month keys are in format "YYYY-MM", e.g., "2026-01", "2025-12"
    months_filtered = {
        month_key: events 
        for month_key, events in months_raw.items() 
        if month_key.startswith(target_year)
    }
    
    logger.info(f"YEAR_FILTER: target={target_year} raw_months={len(months_raw)} filtered_months={len(months_filtered)}")
    if len(months_raw) != len(months_filtered):
        excluded = [k for k in months_raw.keys() if not k.startswith(target_year)]
        logger.info(f"EXCLUDED_MONTHS: {excluded}")
    
    months_events: Dict[str, List[EventSummary]] = {
        month: [_event_summary(e) for e in events] for month, events in months_filtered.items()
    }

    top_events = [
        TopEventSummary(
            title=f"{e.get('transit_body')} to {e.get('natal_body')}",
            date=dt.date.fromisoformat(str(e.get("date"))) if e.get("date") else None,
            summary=str(e.get("note") or ""),
            score=float(e.get("score", 0.0)),
            tags=list(classify_event(e)),
        )
        for e in raw_result.get("top_events", [])
    ]

    heatmap = _build_heatmap(months_events)
    all_events_flat: List[EventSummary] = [ev for events in months_events.values() for ev in events]
    eclipses = _extract_eclipses(all_events_flat)

    # LLM driven front matter
    year_overview_prompt = build_year_overview_prompt(raw_result.get("meta", {}), top_events, heatmap)
    eclipse_general_prompt = build_eclipse_guide_prompt(eclipses)

    # Rephrase guidance for MAJOR eclipses only (for better readability)
    # Note: eclipses already have guidance from engine calculations
    # LLM only REPHRASES for readability, doesn't generate new astrological content
    major_eclipses = [e for e in eclipses if "eclipse" in e.kind.lower() and "lunar_phase" not in e.kind.lower()]
    
    # Build prompts to REPHRASE our calculated guidance (not generate new)
    eclipse_rephrase_prompts = []
    for i, eclipse in enumerate(major_eclipses[:6]):  # Limit to 6 major eclipses to control LLM costs
        if eclipse.guidance and len(eclipse.guidance) > 15:  # Only rephrase if we have content
            prompt = build_eclipse_rephrase_prompt(eclipse)
            eclipse_rephrase_prompts.append(_call_llm(
                prompt, 
                max_tokens=150, 
                context=f"eclipse_rephrase_{i+1}_{eclipse.date.strftime('%Y-%m-%d')}"
            ))
        else:
            eclipse_rephrase_prompts.append(None)  # No rephrasing needed
    
    # Gather all LLM calls in parallel
    llm_tasks = [
        _call_llm(year_overview_prompt, context="year_overview"), 
        _call_llm(eclipse_general_prompt, context="eclipse_general_guide")
    ]
    # Filter out None prompts
    rephrase_tasks = [task for task in eclipse_rephrase_prompts if task is not None]
    llm_tasks.extend(rephrase_tasks)
    
    llm_results = await asyncio.gather(*llm_tasks)
    
    year_overview_text = llm_results[0]
    eclipse_text = llm_results[1]
    rephrased_guidances = llm_results[2:] if len(llm_results) > 2 else []
    
    # Assign rephrased guidance back to major eclipses (if rephrased)
    rephrase_idx = 0
    for i, eclipse in enumerate(major_eclipses[:6]):
        if eclipse_rephrase_prompts[i] is not None:  # This eclipse was rephrased
            if rephrase_idx < len(rephrased_guidances) and rephrased_guidances[rephrase_idx]:
                eclipse.guidance = rephrased_guidances[rephrase_idx]
            rephrase_idx += 1
        # Otherwise keep original engine guidance

    month_sections = await asyncio.gather(
        *[_generate_month_section(month, events) for month, events in months_events.items()]
    )

    glossary = {
        "conjunction": "Two points share the same zodiac degree, blending energies.",
        "square": "Tension that pushes for action and adjustment.",
        "trine": "A smooth flow that supports ease and collaboration.",
    }
    interpretation_index = {
        f"{ev.transit_body} to {ev.natal_body}": ev.user_friendly_summary or ev.raw_note for ev in all_events_flat[:50]
    }

    year_at_glance = YearAtGlance(
        heatmap=heatmap,
        top_events=top_events,
        commentary=year_overview_text or _fallback_paragraph("Year overview"),
    )

    # Store eclipse guidance once (not duplicated for each eclipse)
    meta = raw_result.get("meta", {})
    report = YearlyForecastReport(
        meta=meta,
        year_at_glance=year_at_glance,
        eclipse_guidance=eclipse_text if eclipse_text else "",
        eclipses_and_lunations=eclipses,
        months=sorted(month_sections, key=lambda m: m.month),
        appendix_all_events=sorted(all_events_flat, key=lambda ev: ev.date),
        glossary=glossary,
        interpretation_index=interpretation_index,
    )
    
    # LOG FINAL REPORT SUMMARY
    target_year = meta.get("target_year") or meta.get("year") or "unknown"
    logger.info(
        f"REPORT_GENERATED: year={target_year} months={len(report.months)} " +
        f"eclipses={len(report.eclipses_and_lunations)} " +
        f"major_eclipses_with_guidance={sum(1 for e in report.eclipses_and_lunations if e.guidance and len(e.guidance) > 50)} " +
        f"total_events={len(report.appendix_all_events)}"
    )
    eclipse_details = [(e.date.isoformat() if hasattr(e.date, 'isoformat') else str(e.date), 
                        e.kind, 
                        len(e.guidance if e.guidance else '')) 
                       for e in report.eclipses_and_lunations[:10]]
    logger.debug(f"REPORT_ECLIPSE_DETAILS: {eclipse_details}")
    
    return report
