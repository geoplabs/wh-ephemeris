"""
Comprehensive compatibility analysis service with LLM integration.
Supports love, friendship, and business compatibility for both basic (sign-only)
and advanced (full natal chart) analysis.

PRODUCTION READY:
- P0-1: Context passed to synastry for proper type-specific weighting
- P0-2: Uses public natal_positions API (not private _natal_positions)
- P0-3: Guards against missing bodies with clear error messages
- P0-4: Deterministic sorting (handled in engine)
- P1: Configurable LLM model/max_tokens
- P1: Robust JSON extraction with incremental parsing
- P1: No sensitive data in error logs
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

# P1: Configurable LLM settings (can be overridden via env vars)
DEFAULT_LLM_MODEL = os.getenv("COMPATIBILITY_LLM_MODEL", "gpt-4o-mini")
DEFAULT_LLM_MAX_TOKENS = int(os.getenv("COMPATIBILITY_LLM_MAX_TOKENS", "2000"))

from .compatibility_engine import synastry, aggregate_score, natal_positions
from .compatibility_helpers import (
    get_sign_relationship,
    get_sign_polarity,
    get_ruler_compatibility,
    get_zodiac_aspect_bonus,
    calculate_planet_sign_compatibility,
)
from .llm_client import generate_section_text, LLMUnavailableError as LLMError
from .compatibility_qa_editor import (
    qa_edit_basic_compatibility_response,
    qa_edit_advanced_compatibility_response,
    validate_response_completeness,
)
from ..schemas.compatibility import (
    BasicCompatibilityRequest,
    BasicCompatibilityResponse,
    AdvancedCompatibilityRequest,
    AdvancedCompatibilityResponse,
    CompatibilityScore,
    ElementCompatibility,
    ModalityCompatibility,
    AspectAnalysis,
    HouseOverlay,
)

logger = logging.getLogger(__name__)

# FIX: Import constants from separate module to avoid circular imports
from .compatibility_constants import (
    SIGN_DATA,
    ELEMENT_COMPATIBILITY,
    MODALITY_COMPATIBILITY,
)


# =====================================================================
# ASPECT INTERPRETATIONS
# =====================================================================

ASPECT_DESCRIPTIONS = {
    "love": {
        "conjunction": {
            "Sun-Sun": "Strong ego connection; similar life purposes and identities",
            "Sun-Moon": "Powerful emotional bond; masculine and feminine energies unite",
            "Moon-Moon": "Deep emotional understanding; you feel like soulmates",
            "Venus-Venus": "Similar love languages and aesthetic tastes",
            "Venus-Mars": "Intense sexual chemistry and romantic attraction",
            "Mars-Mars": "Strong physical passion but potential for conflicts",
            "Mercury-Mercury": "Excellent communication; you understand each other's thinking",
        },
        "trine": {
            "Sun-Moon": "Harmonious emotional flow; easy natural compatibility",
            "Venus-Mars": "Passionate yet comfortable sexual relationship",
            "Moon-Venus": "Affectionate, nurturing love; emotional security",
            "Sun-Venus": "Mutual appreciation and admiration",
            "Jupiter-Sun": "Optimism, growth, and expansion in the relationship",
        },
        "square": {
            "Sun-Moon": "Emotional needs clash with identity; requires compromise",
            "Venus-Mars": "Sexual tension that can be exciting or frustrating",
            "Moon-Saturn": "Emotional coldness or restriction; one feels judged",
            "Sun-Saturn": "One partner may feel limited or criticized",
        },
        "opposition": {
            "Sun-Moon": "Opposite but complementary; attraction of opposites",
            "Venus-Mars": "Magnetic sexual attraction with potential power struggles",
            "Sun-Sun": "Different life paths requiring balance and understanding",
        },
    },
    "friendship": {
        "conjunction": {
            "Sun-Sun": "Similar personalities and life approaches",
            "Mercury-Mercury": "Think alike; great conversations and understanding",
            "Moon-Moon": "Emotional support; you 'get' each other",
            "Jupiter-Jupiter": "Shared beliefs, optimism, and sense of adventure",
        },
        "trine": {
            "Mercury-Mercury": "Easy communication; conversations flow naturally",
            "Sun-Moon": "Supportive and uplifting friendship",
            "Jupiter-Sun": "Encouraging, expansive friendship with mutual growth",
            "Venus-Venus": "Shared social values and enjoyment",
        },
        "square": {
            "Mercury-Mercury": "Miscommunication; different thinking styles",
            "Sun-Saturn": "One may feel judged or restricted",
            "Mars-Mars": "Competitive friction; may argue",
        },
    },
    "business": {
        "conjunction": {
            "Sun-Sun": "Shared vision and goals; similar leadership styles",
            "Mercury-Mercury": "Excellent business communication and planning",
            "Saturn-Saturn": "Shared work ethic and sense of responsibility",
            "Mars-Mars": "High energy and drive, but may compete",
        },
        "trine": {
            "Sun-Saturn": "One provides vision; other provides structure",
            "Mercury-Saturn": "Practical communication; efficient planning",
            "Mars-Jupiter": "Ambitious goals with optimistic action",
            "Sun-Jupiter": "Expansive vision with confidence",
        },
        "square": {
            "Sun-Saturn": "Authority conflicts; one feels limited",
            "Mars-Saturn": "Action blocked by caution; frustrating delays",
            "Mercury-Jupiter": "Overoptimism vs. practical details",
        },
        "opposition": {
            "Sun-Sun": "Opposite approaches requiring balance",
            "Saturn-Jupiter": "Caution vs. expansion creates tension",
        },
    },
}


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================

def _get_element_compatibility(elem1: str, elem2: str) -> Tuple[str, str]:
    """Get element compatibility rating and description."""
    key = (elem1, elem2) if (elem1, elem2) in ELEMENT_COMPATIBILITY else (elem2, elem1)
    return ELEMENT_COMPATIBILITY.get(key, ("medium", "Moderate compatibility"))


def _get_modality_compatibility(mod1: str, mod2: str) -> Tuple[str, str]:
    """Get modality compatibility rating and description."""
    key = (mod1, mod2) if (mod1, mod2) in MODALITY_COMPATIBILITY else (mod2, mod1)
    return MODALITY_COMPATIBILITY.get(key, ("medium", "Moderate compatibility"))


def _normalize_sign_name(sign: str) -> str:
    """Normalize sign name to title case."""
    return sign.strip().title()


def _get_aspect_description(comp_type: str, aspect: str, planet1: str, planet2: str) -> str:
    """Get description for a specific aspect between two planets."""
    aspect_dict = ASPECT_DESCRIPTIONS.get(comp_type, {}).get(aspect, {})
    
    # Try direct match
    key1 = f"{planet1}-{planet2}"
    key2 = f"{planet2}-{planet1}"
    
    if key1 in aspect_dict:
        return aspect_dict[key1]
    elif key2 in aspect_dict:
        return aspect_dict[key2]
    
    # Generic descriptions
    generic = {
        "conjunction": f"{planet1} and {planet2} blend energies creating strong connection",
        "trine": f"{planet1} and {planet2} flow harmoniously together",
        "sextile": f"{planet1} and {planet2} offer opportunities for growth",
        "square": f"{planet1} and {planet2} create tension requiring work",
        "opposition": f"{planet1} and {planet2} pull in opposite directions needing balance",
    }
    
    return generic.get(aspect, f"{planet1} aspects {planet2}")


def _determine_area_affected(planet1: str, planet2: str) -> str:
    """Determine which life area is affected by planetary pair."""
    areas = {
        "Sun": "identity, purpose, ego",
        "Moon": "emotions, security, instincts",
        "Mercury": "communication, thinking, daily exchanges",
        "Venus": "love, affection, values, aesthetics",
        "Mars": "action, desire, sexuality, conflict",
        "Jupiter": "growth, optimism, expansion, beliefs",
        "Saturn": "responsibility, structure, boundaries, commitment",
        "Uranus": "change, freedom, innovation",
        "Neptune": "dreams, spirituality, idealism",
        "Pluto": "transformation, power, intensity",
    }
    
    area1 = areas.get(planet1, "general")
    area2 = areas.get(planet2, "general")
    
    if area1 == area2:
        return area1
    return f"{area1} and {area2}"


def _calculate_compatibility_scores(
    synastry_aspects: List[Dict[str, Any]],
    comp_type: str,
    element_compat: str,
    modality_compat: str,
    moon_compat: float = 50.0,
    venus_compat: float = 50.0,
    mars_compat: float = 50.0
) -> CompatibilityScore:
    """
    Calculate detailed compatibility scores based on synastry aspects and relationship type.
    
    NOW INCLUDES: Moon/Venus/Mars compatibility weighting for advanced mode.
    """
    
    # Base score from synastry aspects
    base_score = aggregate_score(synastry_aspects)
    
    logger.debug(f"Base synastry score: {base_score}, Moon: {moon_compat}, Venus: {venus_compat}, Mars: {mars_compat}")
    
    # Element and modality bonuses vary by relationship type
    element_bonus = {"high": 10, "medium": 5, "low": -5}.get(element_compat, 0)
    modality_bonus = {"high": 5, "medium": 0, "low": -5}.get(modality_compat, 0)
    
    # Relationship-specific adjustments
    if comp_type == "love":
        # Love values emotional and physical connection more
        emotional_multiplier = 2.5
        physical_multiplier = 3.0
        intellectual_multiplier = 1.2
        communication_multiplier = 1.5
        values_multiplier = 1.8
    elif comp_type == "friendship":
        # Friendship values communication and shared interests
        emotional_multiplier = 1.8
        physical_multiplier = 0.5  # Less important for friendship
        intellectual_multiplier = 2.5
        communication_multiplier = 3.0
        values_multiplier = 1.5
    else:  # business
        # Business values goals, structure, and practical compatibility
        emotional_multiplier = 1.0
        physical_multiplier = 0.3  # Not relevant for business
        intellectual_multiplier = 2.0
        communication_multiplier = 2.5
        values_multiplier = 2.8  # Very important for business
    
    # Calculate category scores based on specific aspects
    emotional_score = base_score
    intellectual_score = base_score
    values_score = base_score
    communication_score = base_score
    
    # FIX E: Physical score - only relevant for love
    if comp_type == "love":
        physical_score = base_score
    else:
        physical_score = 50.0  # Neutral baseline for friendship/business
    
    for aspect in synastry_aspects:
        p1, p2 = aspect["p1"], aspect["p2"]
        weight = aspect["weight"]
        
        # Emotional (Moon, Venus for emotional connection)
        if "Moon" in [p1, p2]:
            emotional_score += weight * emotional_multiplier
        if "Venus" in [p1, p2] and comp_type in ["love", "friendship"]:
            emotional_score += weight * (emotional_multiplier * 0.8)
        
        # Intellectual (Mercury, Jupiter for mental connection)
        if "Mercury" in [p1, p2]:
            intellectual_score += weight * intellectual_multiplier
        if "Jupiter" in [p1, p2]:
            intellectual_score += weight * (intellectual_multiplier * 0.6)
        
        # Physical (Mars-Venus for romantic chemistry)
        if comp_type == "love":
            if "Mars" in [p1, p2] and "Venus" in [p1, p2]:
                physical_score += weight * physical_multiplier * 1.5  # Extra bonus for Mars-Venus
            elif "Mars" in [p1, p2] or "Venus" in [p1, p2]:
                physical_score += weight * physical_multiplier
        
        # Values (Jupiter, Saturn for shared goals and stability)
        if "Jupiter" in [p1, p2]:
            values_score += weight * values_multiplier
        if "Saturn" in [p1, p2]:
            if comp_type == "business":
                values_score += weight * (values_multiplier * 1.3)  # Saturn is great for business
            else:
                values_score += weight * (values_multiplier * 0.7)  # Can be heavy for love/friendship
        
        # Communication (Mercury for all, Sun-Moon for understanding)
        if "Mercury" in [p1, p2]:
            communication_score += weight * communication_multiplier
        if ("Sun" in [p1, p2] and "Moon" in [p1, p2]):
            communication_score += weight * (communication_multiplier * 1.2)
    
    # Normalize scores to 0-100 range with better distribution (FIX D)
    def normalize(score: float, bonus: float = 0, max_contribution: float = 100.0) -> float:
        """
        Normalize score with optional max contribution cap to prevent ceiling collapse.
        Uses soft clamping for better score distribution.
        """
        total = score + bonus
        
        # Cap extreme contributions but allow reasonable range
        if total > max_contribution:
            # Soft cap: use sigmoid-like compression above threshold
            excess = total - max_contribution
            compressed_excess = excess / (1 + excess / 20)  # Diminishing returns
            total = max_contribution + compressed_excess
        
        # Hard clamp to valid range
        normalized = min(100, max(0, total))
        return round(normalized, 1)
    
    # Weight Moon/Venus/Mars based on relationship type
    if comp_type == "love":
        # Love: Moon & Venus are crucial, Mars adds passion
        emotional_score = (emotional_score * 0.6) + (moon_compat * 0.4)
        values_score = (values_score * 0.6) + (venus_compat * 0.4)
        physical_score = (physical_score * 0.5) + (mars_compat * 0.3) + (venus_compat * 0.2)
        overall_adjustment = element_bonus * 1.2 + modality_bonus * 0.8
        
    elif comp_type == "friendship":
        # Friendship: Moon matters, Venus for shared values
        emotional_score = (emotional_score * 0.7) + (moon_compat * 0.3)
        values_score = (values_score * 0.7) + (venus_compat * 0.3)
        # FIX E: Mars for activity/energy compatibility in friendship
        physical_score = 50.0 + (mars_compat - 50.0) * 0.3  # Weighted Mars contribution
        overall_adjustment = element_bonus * 0.8 + modality_bonus * 1.2
        
    else:  # business
        # Business: Mars for drive, Venus for cooperation
        values_score = (values_score * 0.7) + (venus_compat * 0.3)
        intellectual_score = (intellectual_score * 0.8) + (mars_compat * 0.2)  # Mars = drive
        # FIX E: Mars for drive/energy in business
        physical_score = 50.0 + (mars_compat - 50.0) * 0.4  # Weighted Mars contribution
        # Moon less relevant for business
        overall_adjustment = element_bonus * 0.6 + modality_bonus * 1.5
    
    # Calculate final scores
    overall = normalize(base_score, overall_adjustment)
    
    return CompatibilityScore(
        overall=overall,
        emotional=normalize(emotional_score, element_bonus if comp_type in ["love", "friendship"] else 0),
        intellectual=normalize(intellectual_score, modality_bonus),
        physical=normalize(physical_score, element_bonus if comp_type == "love" else 0),
        values=normalize(values_score, element_bonus * 0.5 + modality_bonus * 0.5),
        communication=normalize(communication_score, modality_bonus * 1.2),
    )


# =====================================================================
# LLM INTEGRATION
# =====================================================================

def _generate_template_narrative(
    comp_type: str,
    sign1: str,
    sign2: str,
    score: CompatibilityScore,
    element_analysis: ElementCompatibility,
    modality_analysis: ModalityCompatibility,
) -> Dict[str, str]:
    """Generate template-based compatibility narrative (no LLM)."""
    
    rating = score.get_rating().lower()
    
    # Template-based summary
    summary = f"{sign1} and {sign2} have {rating} {comp_type} compatibility with an overall score of {score.overall}/100. {element_analysis.description} {modality_analysis.description}"
    
    # Template-based detailed analysis
    detailed_analysis = f"""The {comp_type} compatibility between {sign1} and {sign2} is rated as {rating}. 

Their elemental combination ({element_analysis.person1_element} and {element_analysis.person2_element}) indicates {element_analysis.compatibility} compatibility. {element_analysis.description}

In terms of modality, the combination of {modality_analysis.person1_modality} and {modality_analysis.person2_modality} shows {modality_analysis.compatibility} compatibility. {modality_analysis.description}

The overall compatibility score of {score.overall}/100 reflects a balanced assessment across emotional ({score.emotional}/100), intellectual ({score.intellectual}/100), physical ({score.physical}/100), values ({score.values}/100), and communication ({score.communication}/100) dimensions."""
    
    # Template-based strengths - CUSTOMIZED BY TYPE
    strengths = []
    
    if comp_type == "love":
        # Love-specific strengths
        if element_analysis.compatibility == "high":
            strengths.append(f"Natural romantic chemistry from {element_analysis.person1_element}-{element_analysis.person2_element} harmony")
        if score.emotional >= 70:
            strengths.append("Deep emotional bond and mutual understanding of feelings")
        if score.physical >= 70:
            strengths.append("Strong physical attraction and sexual compatibility")
        if score.communication >= 70:
            strengths.append("Open emotional communication strengthens intimacy")
        if score.values >= 70:
            strengths.append("Aligned life goals and relationship values")
    
    elif comp_type == "friendship":
        # Friendship-specific strengths
        if element_analysis.compatibility == "high":
            strengths.append(f"Natural ease and flow in social interactions")
        if score.intellectual >= 70:
            strengths.append("Stimulating conversations and shared intellectual interests")
        if score.communication >= 70:
            strengths.append("Easy, effortless communication and mutual understanding")
        if modality_analysis.compatibility == "high":
            strengths.append("Compatible social energy and activity levels")
        if score.values >= 70:
            strengths.append("Similar worldviews and shared principles")
    
    else:  # business
        # Business-specific strengths
        if score.values >= 70:
            strengths.append("Aligned business goals and professional values")
        if score.communication >= 70:
            strengths.append("Clear, efficient professional communication")
        if score.intellectual >= 70:
            strengths.append("Complementary problem-solving approaches")
        if modality_analysis.compatibility == "high":
            strengths.append("Compatible work styles and decision-making processes")
        if element_analysis.person1_element == "Earth" or element_analysis.person2_element == "Earth":
            strengths.append("Practical, grounded approach to business matters")
    
    if not strengths:
        strengths = ["Potential for growth through understanding differences", "Opportunity to learn from each other"]
    
    # Template-based challenges - CUSTOMIZED BY TYPE
    challenges = []
    
    if comp_type == "love":
        # Love-specific challenges
        if element_analysis.compatibility == "low":
            challenges.append("Different emotional needs and expressions of affection")
        if score.emotional < 60:
            challenges.append("May struggle with emotional vulnerability and intimacy")
        if score.physical < 60:
            challenges.append("Different approaches to physical affection and intimacy")
        if modality_analysis.compatibility == "low":
            challenges.append("Conflicts over pace and commitment in relationship")
        if score.values < 60:
            challenges.append("Different visions for relationship future and life goals")
    
    elif comp_type == "friendship":
        # Friendship-specific challenges
        if element_analysis.compatibility == "low":
            challenges.append("Different social styles and friendship expectations")
        if score.communication < 60:
            challenges.append("Misunderstandings due to different communication styles")
        if score.intellectual < 60:
            challenges.append("May lack shared intellectual interests or topics")
        if modality_analysis.compatibility == "low":
            challenges.append("Different activity levels and social energy")
        if score.values < 60:
            challenges.append("Divergent values or moral perspectives")
    
    else:  # business
        # Business-specific challenges
        if score.values < 60:
            challenges.append("Different business philosophies and long-term goals")
        if score.communication < 60:
            challenges.append("Potential miscommunication in professional matters")
        if modality_analysis.compatibility == "low":
            challenges.append("Conflicts over decision-making speed and processes")
        if element_analysis.compatibility == "low":
            challenges.append("Different approaches to risk and business strategy")
        if score.intellectual < 60:
            challenges.append("Different problem-solving and planning styles")
    
    if not challenges:
        challenges = ["Maintaining balance between individual needs and partnership", "Avoiding complacency in the relationship"]
    
    # Template-based advice - CUSTOMIZED BY TYPE
    if comp_type == "love":
        advice = [
            "Schedule quality time for emotional and physical intimacy",
            "Communicate needs and desires openly without judgment",
            "Respect each other's love language and expressions",
            "Build trust through consistency and vulnerability"
        ]
    elif comp_type == "friendship":
        advice = [
            "Make time for regular meaningful conversations",
            "Support each other's personal growth and independence",
            "Respect boundaries while staying connected",
            "Share experiences and create positive memories together"
        ]
    else:  # business
        advice = [
            "Establish clear roles, responsibilities, and expectations",
            "Schedule regular check-ins to align on goals and progress",
            "Document agreements and maintain professional boundaries",
            "Leverage each partner's strengths for optimal results"
        ]
    
    return {
        "summary": summary,
        "detailed_analysis": detailed_analysis,
        "strengths": strengths[:5],
        "challenges": challenges[:5],
        "advice": advice[:4],
        "relationship_dynamics": f"The relationship dynamics between {sign1} and {sign2} are shaped by their {element_analysis.compatibility} elemental compatibility and {modality_analysis.compatibility} modal compatibility.",
        "long_term_potential": f"With an overall compatibility of {score.overall}/100, this pairing has {'strong' if score.overall >= 70 else 'moderate' if score.overall >= 50 else 'challenging'} long-term potential."
    }


async def _generate_compatibility_narrative_llm(
    comp_type: str,
    sign1: str,
    sign2: str,
    score: CompatibilityScore,
    element_analysis: ElementCompatibility,
    modality_analysis: ModalityCompatibility,
    aspects: List[Dict[str, Any]] = None,
    natal_data: Dict[str, Any] = None,
    person1_name: Optional[str] = None,
    person2_name: Optional[str] = None,
    person1_pronouns: Optional[str] = None,
    person2_pronouns: Optional[str] = None,
    model: Optional[str] = None,  # P1: Configurable model (defaults to env var or gpt-4o-mini)
    max_tokens: Optional[int] = None  # P1: Configurable token limit (defaults to env var or 2000)
) -> Dict[str, str]:
    """Generate personalized compatibility narrative using LLM."""
    
    # P1: Apply defaults for model and max_tokens
    if model is None:
        model = DEFAULT_LLM_MODEL
    if max_tokens is None:
        max_tokens = DEFAULT_LLM_MAX_TOKENS
    
    # FIX H: Use pronouns and names for better narrative (default to neutral)
    p1_label = person1_name or sign1
    p2_label = person2_name or sign2
    p1_pronouns = person1_pronouns or "they/them"
    p2_pronouns = person2_pronouns or "they/them"
    
    # Build context for LLM
    context = f"""
You are an expert astrologer providing {comp_type} compatibility analysis.

PERSON 1: {p1_label} ({sign1} Sun) - Pronouns: {p1_pronouns}
PERSON 2: {p2_label} ({sign2} Sun) - Pronouns: {p2_pronouns}

IMPORTANT: When writing your analysis:
- If names are provided, use them naturally (e.g., "Sarah and Emma")
- If no names, refer to them as "{sign1}" and "{sign2}", or "both partners", "you two", "this couple/pair"
- NEVER use "Person 1" or "Person 2" or "the first person" or "the second person"
- Write naturally as if speaking to real people

ELEMENT COMPATIBILITY:
- Person 1 Element: {element_analysis.person1_element}
- Person 2 Element: {element_analysis.person2_element}
- Compatibility Level: {element_analysis.compatibility}
- Description: {element_analysis.description}

MODALITY COMPATIBILITY:
- Person 1 Modality: {modality_analysis.person1_modality}
- Person 2 Modality: {modality_analysis.person2_modality}
- Compatibility Level: {modality_analysis.compatibility}
- Description: {modality_analysis.description}

COMPATIBILITY SCORES:
- Overall: {score.overall}/100 ({score.get_rating()})
- Emotional: {score.emotional}/100
- Intellectual: {score.intellectual}/100
- Physical: {score.physical}/100
- Values: {score.values}/100
- Communication: {score.communication}/100
"""
    
    if aspects and len(aspects) > 0:
        context += "\n\nMAJOR SYNASTRY ASPECTS:\n"
        for asp in aspects[:8]:  # Top 8 aspects
            context += f"- {asp['p1']} {asp['type']} {asp['p2']} (orb: {asp['orb']}°, weight: {asp['weight']})\n"
    
    if natal_data:
        context += f"\n\nADDITIONAL CHART DATA:\n{natal_data}"
    
    # Tailor prompt based on relationship type
    if comp_type == "love":
        relationship_focus = "romantic relationship, emotional intimacy, sexual chemistry, and long-term partnership potential"
    elif comp_type == "friendship":
        relationship_focus = "friendship dynamics, mutual support, shared interests, and social compatibility"
    else:  # business
        relationship_focus = "business partnership, professional collaboration, complementary skills, and shared goals"
    
    prompt = f"""{context}

Based on this astrological data, provide a comprehensive {comp_type} compatibility analysis focusing on {relationship_focus}.

**IMPORTANT: Write naturally and use markdown formatting:**
- Use **bold** (`**text**`) for key astrological terms, planet names, signs, and important concepts
- Use *italic* (`*text*`) for subtle emphasis, nuances, or secondary points
- Write as if speaking directly to real people in a conversational, professional tone
- Use natural pronouns and references (their names if provided, or "both partners", "this couple", etc.)
- AVOID robotic phrases like "Person 1", "the first person", "the second person"

Please provide:

1. **Summary** (2-3 sentences): High-level overview of the compatibility. 
   - Start with the zodiac signs or names (e.g., "**{sign1}** and **{sign2}** create a vibrant connection...")
   - Use **bold** for key zodiac signs and important concepts
   - Be warm and direct

2. **Detailed Analysis** (3-4 paragraphs): Deep dive into how these energies interact:
   - Refer to them naturally as "{sign1} and {sign2}" or "both partners" or by their names
   - Use **bold** for elements (**{element_analysis.person1_element}**, **{element_analysis.person2_element}**)
   - Use **bold** for modalities (**{modality_analysis.person1_modality}**, **{modality_analysis.person2_modality}**)
   - Explain harmony and friction in practical, relatable terms

3. **Strengths** (3-5 bullet points): Key strengths of this pairing.
   - Start each with **bold** keyword (e.g., "**Mutual respect** and understanding")
   - Write in a warm, encouraging tone

4. **Challenges** (3-5 bullet points): Main challenges they may face.
   - Start each with **bold** keyword (e.g., "**Different pacing** in decision-making")
   - Be honest but constructive

5. **Advice** (3-4 bullet points): Practical advice for making this {comp_type} work.
   - Start with **bold** action verb (e.g., "**Communicate** openly about needs")
   - Make it actionable and specific

{"6. **Relationship Dynamics** (1 paragraph): Describe the day-to-day dynamics naturally." if aspects else ""}

{"7. **Long-term Potential** (1 paragraph): Assess long-term viability with warmth and insight." if aspects else ""}

Format your response as JSON with these exact keys: "summary", "detailed_analysis", "strengths" (array), "challenges" (array), "advice" (array){', "relationship_dynamics", "long_term_potential"' if aspects else ''}.

Be specific, personalized, warm, and insightful. Use natural, conversational language. Remember markdown formatting (**bold** and *italic*).
"""
    
    try:
        system_prompt = "You are an expert astrologer specializing in relationship compatibility analysis. Provide detailed, personalized insights based on astrological data. IMPORTANT: Use markdown formatting (**bold** for key terms, *italic* for emphasis) throughout your text to highlight important concepts. Return ONLY valid JSON with no additional text."
        
        # P1: Use configurable model and max_tokens
        response = await generate_section_text(
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=max_tokens,
            model=model
        )
        
        import json
        import re
        
        # P1 FIX: Robust JSON extraction with incremental parsing
        result = None
        try:
            # Try parsing directly first
            result = json.loads(response)
        except json.JSONDecodeError:
            # Find first { and attempt incremental parsing for valid JSON object
            start_idx = response.find('{')
            if start_idx == -1:
                raise ValueError("No JSON object found in LLM response")
            
            # Try to find matching closing brace
            brace_count = 0
            end_idx = start_idx
            for i in range(start_idx, len(response)):
                if response[i] == '{':
                    brace_count += 1
                elif response[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end_idx = i + 1
                        break
            
            if end_idx > start_idx:
                try:
                    result = json.loads(response[start_idx:end_idx])
                except json.JSONDecodeError:
                    # Last resort: regex extract and try again
                    match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', response, re.DOTALL)
                    if match:
                        result = json.loads(match.group(0))
            
            if result is None:
                raise ValueError("Failed to extract valid JSON from LLM response")
        
        # Ensure all required keys exist
        result.setdefault("summary", "Compatibility analysis based on astrological factors.")
        result.setdefault("detailed_analysis", "")
        result.setdefault("strengths", [])
        result.setdefault("challenges", [])
        result.setdefault("advice", [])
        
        if aspects:
            result.setdefault("relationship_dynamics", "")
            result.setdefault("long_term_potential", "")
        
        return result
        
    except Exception as e:
        logger.error(f"LLM compatibility narrative generation failed: {e}")
        
        # Fallback to template-based response
        return {
            "summary": f"{sign1} and {sign2} have {score.get_rating().lower()} compatibility for {comp_type}.",
            "detailed_analysis": f"This {comp_type} pairing between {sign1} and {sign2} shows an overall compatibility of {score.overall}/100. {element_analysis.description} {modality_analysis.description}",
            "strengths": ["Mutual understanding", "Shared values", "Good communication"],
            "challenges": ["Different approaches", "Occasional misunderstandings"],
            "advice": ["Communicate openly", "Respect differences", "Focus on common goals"],
            "relationship_dynamics": "The relationship dynamics are influenced by their elemental and modal differences.",
            "long_term_potential": "With effort and understanding, this pairing has potential for growth."
        }


# =====================================================================
# MAIN COMPATIBILITY FUNCTIONS
# =====================================================================

async def analyze_basic_compatibility(
    req: BasicCompatibilityRequest
) -> BasicCompatibilityResponse:
    """Analyze compatibility based on Sun signs only."""
    
    sign1 = _normalize_sign_name(req.person1_sign)
    sign2 = _normalize_sign_name(req.person2_sign)
    
    if sign1 not in SIGN_DATA or sign2 not in SIGN_DATA:
        raise ValueError(f"Invalid zodiac sign(s): {sign1}, {sign2}")
    
    # Get sign data
    data1 = SIGN_DATA[sign1]
    data2 = SIGN_DATA[sign2]
    
    # Element and modality compatibility
    elem_compat, elem_desc = _get_element_compatibility(data1["element"], data2["element"])
    mod_compat, mod_desc = _get_modality_compatibility(data1["modality"], data2["modality"])
    
    element_analysis = ElementCompatibility(
        person1_element=data1["element"],
        person2_element=data2["element"],
        compatibility=elem_compat,
        description=elem_desc
    )
    
    modality_analysis = ModalityCompatibility(
        person1_modality=data1["modality"],
        person2_modality=data2["modality"],
        compatibility=mod_compat,
        description=mod_desc
    )
    
    # Calculate base scores using proper astrology
    base_score = 50.0  # Neutral base
    
    # 1. ZODIAC WHEEL RELATIONSHIP (trine, square, opposition, etc.)
    relationship, distance = get_sign_relationship(sign1, sign2)
    zodiac_bonus = get_zodiac_aspect_bonus(relationship, req.compatibility_type)
    base_score += zodiac_bonus
    
    logger.debug(f"Zodiac relationship: {sign1}-{sign2} = {relationship}, bonus: {zodiac_bonus}")
    
    # 2. ELEMENT COMPATIBILITY (cleaner, no double-counting)
    if elem_compat == "high":
        base_score += 10
    elif elem_compat == "low":
        base_score -= 5
    
    # 3. MODALITY COMPATIBILITY
    if mod_compat == "high":
        base_score += 8
    elif mod_compat == "low":
        base_score -= 5
    
    # 4. RULING PLANET BONUSES (type-specific)
    ruler_bonus = get_ruler_compatibility(data1["ruler"], data2["ruler"], req.compatibility_type)
    base_score += ruler_bonus
    
    logger.debug(f"Ruler bonus: {data1['ruler']}-{data2['ruler']} for {req.compatibility_type} = {ruler_bonus}")
    
    # 5. POLARITY (masculine/feminine)
    pol1, pol2, pol_compat = get_sign_polarity(sign1, sign2)
    if pol_compat == "complementary":
        base_score += 3.0  # Different polarities balance each other
    elif pol_compat == "similar":
        base_score += 1.0  # Same polarity understand each other
    
    # 6. TYPE-SPECIFIC FINE-TUNING (non-overlapping with above)
    if req.compatibility_type == "love":
        # Fire+Water can have intense passion (not counted above)
        if {data1["element"], data2["element"]} == {"Fire", "Water"} and relationship == "opposition":
            base_score += 5  # Magnetic attraction of opposites
    
    elif req.compatibility_type == "friendship":
        # Mutable+Mutable extra adaptability bonus
        if data1["modality"] == "Mutable" and data2["modality"] == "Mutable":
            base_score += 3
    
    else:  # business
        # Cardinal+Fixed is THE power combo for business
        if {data1["modality"], data2["modality"]} == {"Cardinal", "Fixed"}:
            base_score += 8  # Vision + persistence = success
    
    base_score = min(100, max(0, base_score))
    
    # Helper to clamp scores to valid range
    def clamp_score(score: float) -> float:
        return round(min(100, max(0, score)), 1)
    
    # Create compatibility score with type-specific emphasis
    if req.compatibility_type == "love":
        # Love emphasizes emotional and physical
        score = CompatibilityScore(
            overall=clamp_score(base_score),
            emotional=clamp_score(base_score + (10 if "Water" in [data1["element"], data2["element"]] else -5)),
            intellectual=clamp_score(base_score + (3 if "Air" in [data1["element"], data2["element"]] else -3)),
            physical=clamp_score(base_score + (12 if "Fire" in [data1["element"], data2["element"]] else -5)),
            values=clamp_score(base_score + (5 if "Earth" in [data1["element"], data2["element"]] else 0)),
            communication=clamp_score(base_score + (5 if "Air" in [data1["element"], data2["element"]] else -5)),
        )
    
    elif req.compatibility_type == "friendship":
        # Friendship emphasizes communication and intellectual
        score = CompatibilityScore(
            overall=clamp_score(base_score),
            emotional=clamp_score(base_score + (5 if "Water" in [data1["element"], data2["element"]] else 0)),
            intellectual=clamp_score(base_score + (15 if "Air" in [data1["element"], data2["element"]] else -5)),
            physical=clamp_score(base_score),  # Not relevant for friendship
            values=clamp_score(base_score + (5 if mod_compat == "high" else 0)),
            communication=clamp_score(base_score + (15 if "Air" in [data1["element"], data2["element"]] else -5)),
        )
    
    else:  # business
        # Business emphasizes values and practical results
        score = CompatibilityScore(
            overall=clamp_score(base_score),
            emotional=clamp_score(base_score),  # Less important for business
            intellectual=clamp_score(base_score + (8 if "Air" in [data1["element"], data2["element"]] else 0)),
            physical=clamp_score(base_score - 10),  # Not relevant for business
            values=clamp_score(base_score + (15 if "Earth" in [data1["element"], data2["element"]] else -5)),
            communication=clamp_score(base_score + (10 if mod_compat == "high" else -5)),
        )
    
    # Generate narrative (LLM or template-based)
    if req.llm:
        narrative = await _generate_compatibility_narrative_llm(
            req.compatibility_type,
            sign1,
            sign2,
            score,
            element_analysis,
            modality_analysis,
            person1_name=req.person1_name,
            person2_name=req.person2_name,
            person1_pronouns=req.person1_pronouns,
            person2_pronouns=req.person2_pronouns
        )
    else:
        narrative = _generate_template_narrative(
            req.compatibility_type,
            sign1,
            sign2,
            score,
            element_analysis,
            modality_analysis
        )
    
    # Build response
    response = BasicCompatibilityResponse(
        person1_sign=sign1,
        person2_sign=sign2,
        compatibility_type=req.compatibility_type,
        system=req.system,
        score=score,
        element_analysis=element_analysis,
        modality_analysis=modality_analysis,
        strengths=narrative.get("strengths", []),
        challenges=narrative.get("challenges", []),
        advice=narrative.get("advice", []),
        summary=narrative.get("summary", ""),
        detailed_analysis=narrative.get("detailed_analysis", ""),
        generated_at=datetime.utcnow().isoformat() + "Z"
    )
    
    # Apply QA editing to polish the response
    response_dict = response.model_dump()
    edited_dict = qa_edit_basic_compatibility_response(response_dict)
    
    # Validate response completeness
    warnings = validate_response_completeness(edited_dict, "basic")
    if warnings:
        logger.warning(f"Basic compatibility response validation warnings: {warnings}")
    
    # Return polished response
    return BasicCompatibilityResponse(**edited_dict)


async def analyze_advanced_compatibility(
    req: AdvancedCompatibilityRequest
) -> AdvancedCompatibilityResponse:
    """Analyze compatibility based on full natal charts."""
    
    # Build chart inputs
    person1_chart = {
        "date": req.person1.date.isoformat(),
        "time": req.person1.time,
        "place": req.person1.place.model_dump(),
        "system": req.system,
        "options": {"ayanamsha": "lahiri"} if req.system == "vedic" else {}
    }
    
    person2_chart = {
        "date": req.person2.date.isoformat(),
        "time": req.person2.time,
        "place": req.person2.place.model_dump(),
        "system": req.system,
        "options": {"ayanamsha": "lahiri"} if req.system == "vedic" else {}
    }
    
    # Calculate natal positions with error handling (P0-3: Guard missing bodies)
    try:
        natal1 = await asyncio.to_thread(natal_positions, person1_chart)
        natal2 = await asyncio.to_thread(natal_positions, person2_chart)
    except (ValueError, KeyError) as e:
        # P1: Don't log sensitive birth data - only log error type
        logger.error(f"Natal position calculation failed: {type(e).__name__}")
        raise ValueError(f"Invalid birth data provided. Please check date, time, and location accuracy.") from e
    
    # P0-3: Validate critical bodies exist (Sun and Moon are essential)
    from .constants import sign_name_from_lon
    
    if "Sun" not in natal1 or "lon" not in natal1.get("Sun", {}):
        raise ValueError("Person 1: Unable to calculate Sun position from provided birth data")
    if "Sun" not in natal2 or "lon" not in natal2.get("Sun", {}):
        raise ValueError("Person 2: Unable to calculate Sun position from provided birth data")
    if "Moon" not in natal1 or "lon" not in natal1.get("Moon", {}):
        raise ValueError("Person 1: Unable to calculate Moon position from provided birth data")
    if "Moon" not in natal2 or "lon" not in natal2.get("Moon", {}):
        raise ValueError("Person 2: Unable to calculate Moon position from provided birth data")
    
    sun1_sign = sign_name_from_lon(natal1["Sun"]["lon"])
    sun2_sign = sign_name_from_lon(natal2["Sun"]["lon"])
    moon1_sign = sign_name_from_lon(natal1["Moon"]["lon"])
    moon2_sign = sign_name_from_lon(natal2["Moon"]["lon"])
    
    # Get element and modality
    data1 = SIGN_DATA[sun1_sign]
    data2 = SIGN_DATA[sun2_sign]
    
    elem_compat, elem_desc = _get_element_compatibility(data1["element"], data2["element"])
    mod_compat, mod_desc = _get_modality_compatibility(data1["modality"], data2["modality"])
    
    element_analysis = ElementCompatibility(
        person1_element=data1["element"],
        person2_element=data2["element"],
        compatibility=elem_compat,
        description=elem_desc
    )
    
    modality_analysis = ModalityCompatibility(
        person1_modality=data1["modality"],
        person2_modality=data2["modality"],
        compatibility=mod_compat,
        description=mod_desc
    )
    
    # Calculate synastry aspects with context-aware weighting
    # P0-1 FIX: Explicitly pass context AND orb_model for proper weighting
    aspect_types = ["conjunction", "trine", "sextile", "square", "opposition"]
    synastry_aspects = await asyncio.to_thread(
        synastry,
        person1_chart,
        person2_chart,
        aspect_types,
        8.0,  # orb
        context=req.compatibility_type,  # Pass love/friendship/business context
        orb_model="quadratic"  # Tight aspects preferred (explicit choice)
    )
    
    # Extract Venus and Mars signs for type-specific weighting (with safety checks)
    venus1_data = natal1.get("Venus", {})
    venus2_data = natal2.get("Venus", {})
    mars1_data = natal1.get("Mars", {})
    mars2_data = natal2.get("Mars", {})
    
    # Check if planets are present (FIX B: Don't default to lon=0)
    has_venus = venus1_data.get("lon") is not None and venus2_data.get("lon") is not None
    has_mars = mars1_data.get("lon") is not None and mars2_data.get("lon") is not None
    
    if has_venus:
        venus1_sign = sign_name_from_lon(venus1_data["lon"])
        venus2_sign = sign_name_from_lon(venus2_data["lon"])
        venus_compat = calculate_planet_sign_compatibility(
            venus1_sign, venus2_sign,
            SIGN_DATA[venus1_sign]["element"],
            SIGN_DATA[venus2_sign]["element"]
        )
    else:
        venus1_sign = "Unknown"
        venus2_sign = "Unknown"
        venus_compat = 50.0  # Neutral if missing
        logger.warning("Venus position missing for one or both charts")
    
    if has_mars:
        mars1_sign = sign_name_from_lon(mars1_data["lon"])
        mars2_sign = sign_name_from_lon(mars2_data["lon"])
        mars_compat = calculate_planet_sign_compatibility(
            mars1_sign, mars2_sign,
            SIGN_DATA[mars1_sign]["element"],
            SIGN_DATA[mars2_sign]["element"]
        )
    else:
        mars1_sign = "Unknown"
        mars2_sign = "Unknown"
        mars_compat = 50.0  # Neutral if missing
        logger.warning("Mars position missing for one or both charts")
    
    # Moon should always be present, but add safety check
    moon1_sign = sign_name_from_lon(natal1["Moon"]["lon"]) if "Moon" in natal1 else "Unknown"
    moon2_sign = sign_name_from_lon(natal2["Moon"]["lon"]) if "Moon" in natal2 else "Unknown"
    
    if moon1_sign != "Unknown" and moon2_sign != "Unknown":
        moon_compat = calculate_planet_sign_compatibility(
            moon1_sign, moon2_sign,
            SIGN_DATA[moon1_sign]["element"],
            SIGN_DATA[moon2_sign]["element"]
        )
    else:
        moon_compat = 50.0
        logger.warning("Moon position missing for one or both charts")
    
    logger.debug(f"Planet compatibility - Moon: {moon_compat}, Venus: {venus_compat}, Mars: {mars_compat}")
    
    # Calculate compatibility scores with planet weighting
    score = _calculate_compatibility_scores(
        synastry_aspects,
        req.compatibility_type,
        elem_compat,
        mod_compat,
        moon_compat,
        venus_compat,
        mars_compat
    )
    
    # Build major aspects list
    major_aspects = []
    for asp in synastry_aspects[:12]:  # Top 12 aspects
        influence = "positive" if asp["weight"] > 0 else "negative" if asp["weight"] < 0 else "neutral"
        area = _determine_area_affected(asp["p1"], asp["p2"])
        description = _get_aspect_description(req.compatibility_type, asp["type"], asp["p1"], asp["p2"])
        
        major_aspects.append(AspectAnalysis(
            aspect_type=asp["type"],
            planet1=asp["p1"],
            planet2=asp["p2"],
            orb=asp["orb"],
            influence=influence,
            area_affected=area,
            description=description
        ))
    
    # Generate narrative (LLM or template-based)
    if req.llm:
        # FIX C: Add element/modality context for key planets
        moon1_elem = SIGN_DATA.get(moon1_sign, {}).get("element", "Unknown") if moon1_sign != "Unknown" else "Unknown"
        moon2_elem = SIGN_DATA.get(moon2_sign, {}).get("element", "Unknown") if moon2_sign != "Unknown" else "Unknown"
        venus1_elem = SIGN_DATA.get(venus1_sign, {}).get("element", "Unknown") if venus1_sign != "Unknown" else "Unknown"
        venus2_elem = SIGN_DATA.get(venus2_sign, {}).get("element", "Unknown") if venus2_sign != "Unknown" else "Unknown"
        mars1_elem = SIGN_DATA.get(mars1_sign, {}).get("element", "Unknown") if mars1_sign != "Unknown" else "Unknown"
        mars2_elem = SIGN_DATA.get(mars2_sign, {}).get("element", "Unknown") if mars2_sign != "Unknown" else "Unknown"
        
        natal_data_summary = f"""
Person 1 Placements:
- Sun: {sun1_sign} ({data1['element']} {data1['modality']})
- Moon: {moon1_sign} ({moon1_elem}) - Emotions, instincts
- Venus: {venus1_sign} ({venus1_elem}) - Love, values
- Mars: {mars1_sign} ({mars1_elem}) - Drive, passion

Person 2 Placements:
- Sun: {sun2_sign} ({data2['element']} {data2['modality']})
- Moon: {moon2_sign} ({moon2_elem}) - Emotions, instincts
- Venus: {venus2_sign} ({venus2_elem}) - Love, values
- Mars: {mars2_sign} ({mars2_elem}) - Drive, passion

Key Planet Compatibility:
- Moon (emotional) compatibility: {moon_compat:.1f}/100
- Venus (values) compatibility: {venus_compat:.1f}/100
- Mars (drive) compatibility: {mars_compat:.1f}/100
"""
        
        narrative = await _generate_compatibility_narrative_llm(
            req.compatibility_type,
            sun1_sign,
            sun2_sign,
            score,
            element_analysis,
            modality_analysis,
            synastry_aspects,
            natal_data_summary,
            person1_name=req.person1.name,
            person2_name=req.person2.name,
            person1_pronouns=req.person1.pronouns,
            person2_pronouns=req.person2.pronouns
        )
    else:
        narrative = _generate_template_narrative(
            req.compatibility_type,
            sun1_sign,
            sun2_sign,
            score,
            element_analysis,
            modality_analysis
        )
    
    # Build response
    response = AdvancedCompatibilityResponse(
        person1_name=req.person1.name,
        person2_name=req.person2.name,
        compatibility_type=req.compatibility_type,
        system=req.system,
        score=score,
        sun_sign_compatibility=f"{sun1_sign} & {sun2_sign}",
        moon_sign_compatibility=f"{moon1_sign} & {moon2_sign}",
        venus_sign_compatibility=f"{venus1_sign} & {venus2_sign}" if req.compatibility_type == "love" else None,
        mars_sign_compatibility=f"{mars1_sign} & {mars2_sign}" if req.compatibility_type == "love" else None,
        major_aspects=major_aspects,
        house_overlays=[],  # TODO: Calculate house overlays in future enhancement
        element_analysis=element_analysis,
        modality_analysis=modality_analysis,
        strengths=narrative.get("strengths", []),
        challenges=narrative.get("challenges", []),
        opportunities=["Work on communication", "Embrace differences", "Focus on shared goals"],
        advice=narrative.get("advice", []),
        relationship_dynamics=narrative.get("relationship_dynamics", ""),
        long_term_potential=narrative.get("long_term_potential", ""),
        summary=narrative.get("summary", ""),
        detailed_analysis=narrative.get("detailed_analysis", ""),
        generated_at=datetime.utcnow().isoformat() + "Z"
    )
    
    # Apply QA editing to polish the response
    response_dict = response.model_dump()
    edited_dict = qa_edit_advanced_compatibility_response(response_dict)
    
    # Validate response completeness
    warnings = validate_response_completeness(edited_dict, "advanced")
    if warnings:
        logger.warning(f"Advanced compatibility response validation warnings: {warnings}")
    
    # Return polished response
    return AdvancedCompatibilityResponse(**edited_dict)

