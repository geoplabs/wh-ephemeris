"""
AI-powered daily forecast composer using parallel 4o-mini calls.

Architecture:
- 9 parallel calls to OpenAI 4o-mini for different sections
- Redis caching with 24h TTL
- Fallback to template system on failure
- Total response time target: 2-3 seconds
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from api.schemas.forecasts import DailyTemplatedResponse, MorningMindset, SectionWithBullets, LoveSection, HealthSection, CautionWindow, LuckyDetails

logger = logging.getLogger(__name__)

# ============================================================================
# SYSTEM PROMPTS FOR EACH SECTION
# ============================================================================

SYSTEM_PROMPTS = {
    "header": """You are a copy editor rephrasing astrological content into plain language.

CRITICAL: Return JSON with EXACT same keys: "mood", "theme", "opening_summary"

RULES:
- Keep "mood" VALUE exactly as-is - DO NOT CHANGE
- Rephrase "theme" VALUE: 
  * PRESERVE the core observation and meaning (relationships, work, emotions, challenges, support, etc.)
  * Keep key descriptive words (disciplined, intense, flowing, structured, etc.)
  * Make it reader-friendly but DON'T change the subject or focus
  * Must be ≤12 words
  
- Rephrase "opening_summary" VALUE:  preserve core observation. Must be ≤25 words.

Example theme transformations:
Input: "Notably disciplined challenges around relationships"
Output: "Significant relationship challenges requiring discipline and structure"

Input: "Subtly flowing creative energy in work"
Output: "Gentle creative flow supporting your work today"

DO NOT invent new meanings. DO NOT use generic placeholders like "Daily Insights".""",

    "morning_mindset": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "paragraph", "mantra"
PRESERVE the core meaning and observation. 
Keep the emotional tone and practical advice. Make it reader-friendly but don't change the subject.""",

    "career": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "paragraph", "bullets"
The "bullets" key must contain an array.
PRESERVE the core career observation and advice. 
Keep the practical career focus and action items. Don't change the subject.""",

    "love": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "paragraph", "attached", "single"
PRESERVE the core relationship observation and advice.
Keep the emotional tone and relationship focus. Don't change the subject.""",

    "health": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "paragraph", "good_options"
The "good_options" key must contain an array.
PRESERVE the core wellness observation and advice. 
Keep the practical health focus. Don't change the subject.""",

    "finance": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "paragraph", "bullets"
The "bullets" key must contain an array.
PRESERVE the core financial observation and advice. 
Keep the practical money focus and caution. Don't change the subject.""",

    "do_avoid": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "do", "avoid"
Both keys must contain arrays.
PRESERVE the core advice. 
Keep items under 12 words. Don't change the subject or invent new advice.""",

    "caution": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "time_window", "note"
Keep "time_window" VALUE unchanged. Only rephrase "note" VALUE.
PRESERVE the core caution and warning. 
Keep the practical warning. Don't change the subject or severity.""",

    "lucky": """You are a copy editor. ONLY rephrase the VALUES (text content), NOT the JSON keys.

CRITICAL: Return JSON with EXACT same keys: "color", "time_window", "direction", "affirmation", "remedies", "one_line_summary"
Keep "color", "time_window", "direction", "one_line_summary" VALUES unchanged.
The "remedies" key must contain an array.
Only rephrase "affirmation" and items in "remedies" array.
PRESERVE the core meaning and focus of affirmation and remedies. 
Don't change the subject or practical advice.""",
}

# ============================================================================
# REDIS CLIENT INITIALIZATION
# ============================================================================

_redis_client: Optional[redis.Redis] = None

def _get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client for caching."""
    global _redis_client
    if not REDIS_AVAILABLE:
        return None
    
    if _redis_client is None:
        import os
        redis_url = os.getenv("REDIS_URL")
        if not redis_url:
            logger.warning("REDIS_URL not set, caching disabled")
            return None
        
        try:
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            _redis_client.ping()
            logger.info("Redis connected for AI composer caching")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            _redis_client = None
    
    return _redis_client

# ============================================================================
# OPENAI CLIENT INITIALIZATION
# ============================================================================

_openai_client: Optional[AsyncOpenAI] = None

def _get_openai_client() -> Optional[AsyncOpenAI]:
    """Get or create OpenAI async client."""
    global _openai_client
    if not OPENAI_AVAILABLE:
        logger.error("OpenAI library not installed")
        return None
    
    if _openai_client is None:
        import os
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("OPENAI_API_KEY not set")
            return None
        
        _openai_client = AsyncOpenAI(api_key=api_key)
        logger.info("OpenAI async client initialized")
    
    return _openai_client

# ============================================================================
# PAYLOAD BUILDERS
# ============================================================================

def _build_header_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for header section (mood, theme, opening_summary).
    NOTE: profile_name and date are NOT sent to GPT - they pass through unchanged.
    NOTE: mood should NOT be changed by AI, only theme and opening_summary should be rephrased.
    """
    # Get mood - this will be kept as-is per user request
    mood = context.get("mood", "")
    
    # Get theme and opening_summary - these will be rephrased
    theme = context.get("theme", "")
    opening_summary = context.get("opening_summary", "")
    
    # Log what we're sending for debugging
    logger.info(f"[AI_MINI] Header payload - mood: {mood!r}, theme: {theme!r}, opening_summary: {opening_summary[:50] if opening_summary else ''}...")
    
    return {
        "mood": mood,
        "theme": theme,
        "opening_summary": opening_summary,
    }

def _build_morning_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for morning mindset section.
    NOTE: build_context returns flat keys like 'morning_paragraph' and 'mantra'.
    """
    return {
        "paragraph": context.get("morning_paragraph", ""),
        "mantra": context.get("mantra", ""),
    }

def _build_area_payload(context: Dict[str, Any], area: str) -> Dict[str, Any]:
    """Build payload for area sections (career, love, health, finance).
    NOTE: build_context returns flat keys like 'career_paragraph', 'career_bullets', etc.
    """
    if area == "career":
        return {
            "paragraph": context.get("career_paragraph", ""),
            "bullets": context.get("career_bullets", []),
        }
    elif area == "love":
        return {
            "paragraph": context.get("love_paragraph", ""),
            "attached": context.get("love_attached", ""),
            "single": context.get("love_single", ""),
        }
    elif area == "health":
        return {
            "paragraph": context.get("health_paragraph", ""),
            "good_options": context.get("health_opts", []),
        }
    elif area == "finance":
        return {
            "paragraph": context.get("finance_paragraph", ""),
            "bullets": context.get("finance_bullets", []),
        }
    else:
        return {"paragraph": "", "bullets": []}

def _build_do_avoid_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for do/avoid section."""
    return {
        "do": context.get("do_today", []),
        "avoid": context.get("avoid_today", []),
    }

def _build_caution_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for caution window section."""
    caution = context.get("caution_window", {})
    return {
        "time_window": caution.get("time_window", "") if isinstance(caution, dict) else "",
        "note": caution.get("note", "") if isinstance(caution, dict) else "",
    }

def _build_lucky_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for lucky elements and remedies."""
    lucky = context.get("lucky", {})
    return {
        "color": lucky.get("color", "") if isinstance(lucky, dict) else "",
        "time_window": lucky.get("time_window", "") if isinstance(lucky, dict) else "",
        "direction": lucky.get("direction", "") if isinstance(lucky, dict) else "",
        "affirmation": lucky.get("affirmation", "") if isinstance(lucky, dict) else "",
        "remedies": context.get("remedies", []),
        "one_line_summary": context.get("one_line_summary", ""),
    }

# ============================================================================
# OPENAI CALL
# ============================================================================

def _has_substantive_content(payload: Dict[str, Any]) -> bool:
    """Check if payload has actual text content to rephrase."""
    for key, value in payload.items():
        if isinstance(value, str) and value.strip():
            return True
        if isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value):
            return True
    return False

async def _call_openai_mini(
    section_type: str,
    payload: Dict[str, Any],
    max_tokens: int = 100,
    temperature: float = 0.7,  # Lower temperature for more consistent rephrasing
) -> Dict[str, Any]:
    """
    Call OpenAI 4o-mini for a specific section.
    
    IMPORTANT: GPT is instructed to ONLY rephrase for grammar/clarity.
    It should NOT change structure, add content, or generate new ideas.
    
    Args:
        section_type: Type of section (header, morning, career, etc.)
        payload: Input data for the section (template-generated content)
        max_tokens: Maximum tokens to generate
        temperature: Sampling temperature (0.3 for consistency)
    
    Returns:
        Parsed JSON response from OpenAI (or original payload if empty)
    """
    # If payload has no substantive content, return it unchanged
    if not _has_substantive_content(payload):
        logger.info(f"Section {section_type} has no content, skipping GPT call")
        return payload
    
    client = _get_openai_client()
    if not client:
        raise RuntimeError("OpenAI client not available")
    
    system_prompt = SYSTEM_PROMPTS.get(section_type, "You are a copy editor. Rephrase for clarity, keeping the same meaning.")
    
    # Add explicit instruction to rephrase VALUES only, NOT keys
    # Extra emphasis for header section to preserve theme meaning
    if section_type == "header":
        user_instruction = (
            "CRITICAL: PRESERVE THE CORE MEANING AND SUBJECT of each value.\n"
            "Do NOT change the subject, focus, or core observation.\n"
            "Keep the exact same JSON key names.\n\n"
            "Example:\n"
            'Input: {"theme": "Powerfully harmonizing challenges around self-expression"}\n'
            'Output: {"theme": "Significant challenges balancing harmony with self-expression"}\n\n'
            "Input JSON:\n\n"
        )
    else:
        user_instruction = (
            "REPHRASE ONLY THE VALUES (text content), NOT THE JSON KEYS.\n"
            "PRESERVE the core meaning and subject.\n"
            "Keep the exact same JSON key names.\n"
            "If a value is empty or an empty array, keep it empty.\n"
            "Input JSON:\n\n"
        )
    user_content = user_instruction + json.dumps(payload, ensure_ascii=False)
    
    # DEBUG: Log exactly what we're sending to GPT
    if section_type in ["header", "love"]:  # Debug these sections
        logger.warning(f"[AI_MINI_DEBUG] Section: {section_type}")
        logger.warning(f"[AI_MINI_DEBUG] Input payload: {json.dumps(payload, ensure_ascii=False)[:200]}")
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # DEBUG: Log what GPT returned
        if section_type in ["header", "love"]:
            logger.warning(f"[AI_MINI_DEBUG] GPT output: {json.dumps(result, ensure_ascii=False)[:200]}")
        
        # Verify result has same keys as input
        if set(result.keys()) != set(payload.keys()):
            logger.warning(f"Section {section_type} returned different keys, using original payload")
            return payload
        
        return result
    
    except Exception as e:
        logger.error(f"OpenAI call failed for {section_type}: {e}")
        raise

# ============================================================================
# PARALLEL COMPOSITION
# ============================================================================

async def compose_daily_forecast_parallel(
    template_context: Dict[str, Any],
    profile_name: str = "User",
    forecast_date: str = "",
) -> Optional[DailyTemplatedResponse]:
    """
    Generate daily forecast using 9 parallel 4o-mini calls.
    
    Args:
        template_context: Context from template system (fallback data)
        profile_name: User's name for personalization
        forecast_date: Date of forecast (YYYY-MM-DD)
    
    Returns:
        DailyTemplatedResponse or None if generation fails
    """
    try:
        # DEBUG: Log what template context contains for arrays
        logger.info(f"Template context arrays: career_bullets={len(template_context.get('career_bullets', []))}, "
                   f"health_opts={len(template_context.get('health_opts', []))}, "
                   f"finance_bullets={len(template_context.get('finance_bullets', []))}, "
                   f"do_today={len(template_context.get('do_today', []))}, "
                   f"avoid_today={len(template_context.get('avoid_today', []))}")
        
        # Define all 9 sections to generate
        sections = [
            ("header", _build_header_payload(template_context), 80),
            ("morning", _build_morning_payload(template_context), 100),
            ("career", _build_area_payload(template_context, "career"), 150),
            ("love", _build_area_payload(template_context, "love"), 150),
            ("health", _build_area_payload(template_context, "health"), 150),
            ("finance", _build_area_payload(template_context, "finance"), 150),
            ("do_avoid", _build_do_avoid_payload(template_context), 100),
            ("caution", _build_caution_payload(template_context), 80),
            ("lucky", _build_lucky_payload(template_context), 120),
        ]
        
        # DEBUG: Log payloads being sent to GPT
        for section_type, payload, _ in sections:
            if isinstance(payload, dict):
                array_keys = {k: len(v) if isinstance(v, list) else "N/A" for k, v in payload.items() if isinstance(v, list)}
                if array_keys:
                    logger.info(f"Section {section_type} payload arrays: {array_keys}")
        
        # Check for empty payloads and log warning
        for section_type, payload, _ in sections:
            if not payload or not any(payload.values()):
                logger.warning(f"Section {section_type} has empty payload, will use template fallback")
        
        # Fire all calls in parallel
        logger.info(f"Starting 9 parallel 4o-mini calls for {forecast_date}")
        start_time = datetime.now()
        
        results = await asyncio.gather(*[
            _call_openai_mini(section_type, payload, max_tokens)
            for section_type, payload, max_tokens in sections
        ], return_exceptions=True)
        
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"Parallel calls completed in {elapsed:.2f}s")
        
        # Check for failures
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                section_type = sections[i][0]
                logger.error(f"Section {section_type} failed: {result}")
                return None  # Fallback to template system
        
        # Assemble response
        return _assemble_response(results, template_context, profile_name, forecast_date)
    
    except Exception as e:
        logger.error(f"Parallel composition failed: {e}")
        return None  # Fallback to template system

# ============================================================================
# RESPONSE ASSEMBLY
# ============================================================================

def _assemble_response(
    results: List[Dict[str, Any]],
    template_context: Dict[str, Any],
    profile_name: str,
    forecast_date: str,
) -> DailyTemplatedResponse:
    """Assemble final response from AI-generated sections."""
    
    header, morning, career, love, health, finance, do_avoid, caution, lucky_remedies = results
    
    # Use original profile_name and date from template_context (don't let AI change them)
    original_profile = template_context.get("profile_name", profile_name)
    original_date = template_context.get("date", forecast_date)
    
    # Generic/bad themes that indicate AI didn't rephrase properly
    GENERIC_THEMES = {
        "daily insights", "daily guidance", "a day of growth", "daily forecast",
        "today's guidance", "daily overview", "daily horoscope"
    }
    
    # Get theme from AI, but validate it's not generic
    ai_theme = header.get("theme", "")
    original_theme = template_context.get("theme", "A day of growth and reflection")
    
    # If AI theme is generic or empty, use original template theme
    if not ai_theme or ai_theme.lower().strip() in GENERIC_THEMES:
        logger.warning(f"[AI_MINI] AI returned generic theme '{ai_theme}', using original: '{original_theme}'")
        final_theme = original_theme
    else:
        final_theme = ai_theme
    
    # Build response
    return DailyTemplatedResponse(
        profile_name=original_profile,  # Pass through from template
        date=original_date,              # Pass through from template
        mood=header.get("mood") or template_context.get("mood", "Vibrant"),  # Keep original mood
        theme=final_theme,  # Use validated theme
        opening_summary=header.get("opening_summary") or template_context.get("opening_summary", "Focus on what matters most today."),
        
        morning_mindset=MorningMindset(
            paragraph=morning.get("paragraph", ""),
            mantra=morning.get("mantra", "I trust my inner wisdom"),
        ),
        
        career=SectionWithBullets(
            paragraph=career.get("paragraph") or template_context.get("career_paragraph", ""),
            bullets=career.get("bullets") or template_context.get("career_bullets", []),
        ),
        
        love=LoveSection(
            paragraph=love.get("paragraph") or template_context.get("love_paragraph", ""),
            attached=love.get("attached") or template_context.get("love_attached", ""),
            single=love.get("single") or template_context.get("love_single", ""),
        ),
        
        health=HealthSection(
            paragraph=health.get("paragraph") or template_context.get("health_paragraph", ""),
            good_options=health.get("good_options") or template_context.get("health_opts", []),
        ),
        
        finance=SectionWithBullets(
            paragraph=finance.get("paragraph") or template_context.get("finance_paragraph", ""),
            bullets=finance.get("bullets") or template_context.get("finance_bullets", []),
        ),
        
        do_today=do_avoid.get("do") or template_context.get("do_today", []),
        avoid_today=do_avoid.get("avoid") or template_context.get("avoid_today", []),
        
        caution_window=CautionWindow(
            time_window=caution.get("time_window", "All day"),
            note=caution.get("note", "Stay mindful of your energy"),
        ),
        
        remedies=lucky_remedies.get("remedies", []),
        
        lucky=LuckyDetails(
            color=lucky_remedies.get("color", template_context.get("lucky", {}).get("color", "Blue")),
            time_window=lucky_remedies.get("time_window", template_context.get("lucky", {}).get("time_window", "Morning hours")),
            direction=lucky_remedies.get("direction", template_context.get("lucky", {}).get("direction", "North")),
            affirmation=lucky_remedies.get("affirmation", template_context.get("lucky", {}).get("affirmation", "I attract positive energy")),
        ),
        
        one_line_summary=lucky_remedies.get("one_line_summary", template_context.get("one_line_summary", "Trust your instincts today.")),
    )

# ============================================================================
# CACHING
# ============================================================================

def _generate_cache_key(chart_hash: str, forecast_date: str, generation_mode: str) -> str:
    """Generate cache key for forecast."""
    key_string = f"daily_forecast:{chart_hash}:{forecast_date}:{generation_mode}"
    return hashlib.sha256(key_string.encode()).hexdigest()[:16]

def get_cached_forecast(
    chart_hash: str,
    forecast_date: str,
    generation_mode: str,
) -> Optional[Dict[str, Any]]:
    """Get cached forecast from Redis."""
    redis_client = _get_redis_client()
    if not redis_client:
        return None
    
    try:
        cache_key = _generate_cache_key(chart_hash, forecast_date, generation_mode)
        cached = redis_client.get(f"ai_forecast:{cache_key}")
        if cached:
            logger.info(f"Cache HIT for {forecast_date}")
            return json.loads(cached)
    except Exception as e:
        logger.error(f"Cache read failed: {e}")
    
    return None

def cache_forecast(
    chart_hash: str,
    forecast_date: str,
    generation_mode: str,
    forecast_data: Dict[str, Any],
    ttl_hours: int = 24,
) -> None:
    """Cache forecast in Redis."""
    redis_client = _get_redis_client()
    if not redis_client:
        return
    
    try:
        cache_key = _generate_cache_key(chart_hash, forecast_date, generation_mode)
        redis_client.setex(
            f"ai_forecast:{cache_key}",
            ttl_hours * 3600,
            json.dumps(forecast_data, ensure_ascii=False),
        )
        logger.info(f"Cached forecast for {forecast_date} (TTL: {ttl_hours}h)")
    except Exception as e:
        logger.error(f"Cache write failed: {e}")

