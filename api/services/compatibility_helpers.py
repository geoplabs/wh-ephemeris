"""
Helper functions for more accurate compatibility calculations.
Includes zodiac wheel relationships, ruling planets, and polarity logic.
"""

from typing import Tuple, Dict

# Zodiac wheel order (0-indexed)
ZODIAC_ORDER = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]

# Polarity (masculine/feminine)
MASCULINE_SIGNS = {"Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"}
FEMININE_SIGNS = {"Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"}


def get_sign_index(sign: str) -> int:
    """Get zodiac wheel index (0-11)."""
    try:
        return ZODIAC_ORDER.index(sign)
    except ValueError:
        return 0


def get_sign_relationship(sign1: str, sign2: str) -> Tuple[str, int]:
    """
    Calculate zodiac wheel relationship between two signs.
    
    Returns:
        tuple: (relationship_name, distance_in_signs)
        
    Relationships:
        - "same" (0): Same sign
        - "semisextile" (1 or 11): Adjacent signs, mild friction
        - "sextile" (2 or 10): 60°, opportunity and ease
        - "square" (3 or 9): 90°, tension and challenge
        - "trine" (4 or 8): 120°, harmony and flow
        - "quincunx" (5 or 7): 150°, adjustment needed
        - "opposition" (6): 180°, attraction and polarity
    """
    idx1 = get_sign_index(sign1)
    idx2 = get_sign_index(sign2)
    
    distance = abs(idx2 - idx1)
    if distance > 6:
        distance = 12 - distance
    
    relationships = {
        0: "same",
        1: "semisextile",
        2: "sextile",
        3: "square",
        4: "trine",
        5: "quincunx",
        6: "opposition"
    }
    
    return relationships.get(distance, "unknown"), distance


def get_sign_polarity(sign1: str, sign2: str) -> Tuple[str, str, str]:
    """
    Get polarity information for two signs.
    
    Returns:
        tuple: (sign1_polarity, sign2_polarity, compatibility)
    """
    pol1 = "masculine" if sign1 in MASCULINE_SIGNS else "feminine"
    pol2 = "masculine" if sign2 in MASCULINE_SIGNS else "feminine"
    
    if pol1 == pol2:
        compat = "similar"  # Understand each other
    else:
        compat = "complementary"  # Balance each other
    
    return pol1, pol2, compat


def get_ruler_compatibility(ruler1: str, ruler2: str, comp_type: str) -> float:
    """
    Calculate compatibility boost based on ruling planets.
    
    Returns:
        float: Bonus score adjustment
    """
    bonus = 0.0
    
    # Venus rules (Taurus, Libra)
    if comp_type == "love":
        if ruler1 == "Venus" or ruler2 == "Venus":
            bonus += 5.0  # Venus ruler boosts love
        if ruler1 == "Venus" and ruler2 == "Venus":
            bonus += 3.0  # Both Venus-ruled = extra boost
    
    # Mercury rules (Gemini, Virgo)
    if comp_type in ["friendship", "business"]:
        if ruler1 == "Mercury" or ruler2 == "Mercury":
            bonus += 4.0  # Mercury boosts communication
        if ruler1 == "Mercury" and ruler2 == "Mercury":
            bonus += 3.0
    
    # Mars rules (Aries, Scorpio)
    if comp_type in ["love", "business"]:
        if ruler1 == "Mars" or ruler2 == "Mars":
            bonus += 3.0  # Mars adds drive/passion
    
    # Saturn rules (Capricorn, Aquarius)
    if comp_type == "business":
        if ruler1 == "Saturn" or ruler2 == "Saturn":
            bonus += 5.0  # Saturn excellent for business structure
        if ruler1 == "Saturn" and ruler2 == "Saturn":
            bonus += 4.0
    elif comp_type == "love":
        if ruler1 == "Saturn" and ruler2 == "Saturn":
            bonus -= 3.0  # Double Saturn can be too heavy for romance
    
    # Jupiter rules (Sagittarius, Pisces)
    if comp_type == "friendship":
        if ruler1 == "Jupiter" or ruler2 == "Jupiter":
            bonus += 4.0  # Jupiter brings optimism and growth
    
    # Sun rules (Leo)
    if comp_type == "love":
        if ruler1 == "Sun" and ruler2 == "Sun":
            bonus -= 2.0  # Two Leos can compete for attention
    
    # Moon rules (Cancer)
    if comp_type in ["love", "friendship"]:
        if ruler1 == "Moon" or ruler2 == "Moon":
            bonus += 3.0  # Moon brings emotional depth
    
    return bonus


def get_zodiac_aspect_bonus(relationship: str, comp_type: str) -> float:
    """
    Get compatibility bonus based on zodiac wheel relationship.
    
    Args:
        relationship: "same", "sextile", "square", "trine", "opposition", etc.
        comp_type: "love", "friendship", or "business"
    
    Returns:
        float: Bonus adjustment
    """
    # Universal (all types)
    if relationship == "trine":
        return 15.0  # Natural harmony
    elif relationship == "sextile":
        return 8.0  # Easy opportunity
    elif relationship == "square":
        return -10.0  # Friction and tension
    elif relationship == "semisextile":
        return -2.0  # Mild friction
    elif relationship == "quincunx":
        return -5.0  # Requires adjustment
    
    # Type-specific for oppositions
    elif relationship == "opposition":
        if comp_type == "love":
            return 5.0  # Opposites attract!
        elif comp_type == "friendship":
            return 0.0  # Neutral, can go either way
        else:  # business
            return -5.0  # Too opposite for business alignment
    
    # Same sign
    elif relationship == "same":
        if comp_type == "friendship":
            return 10.0  # Great for friendship
        elif comp_type == "business":
            return 5.0  # Good for business
        else:  # love
            return 3.0  # Can be good but may lack spark
    
    return 0.0


def calculate_planet_sign_compatibility(sign1: str, sign2: str, element1: str, element2: str) -> float:
    """
    Calculate compatibility between two planet signs (Moon, Venus, Mars).
    
    Returns:
        float: Score 0-100
    """
    relationship, distance = get_sign_relationship(sign1, sign2)
    
    # Base from zodiac relationship
    base = 50.0
    
    if relationship == "trine" or relationship == "same":
        base = 80.0
    elif relationship == "sextile":
        base = 70.0
    elif relationship == "opposition":
        base = 60.0  # Can work but needs effort
    elif relationship == "square":
        base = 40.0
    elif relationship == "quincunx":
        base = 45.0
    
    # Element boost
    # FIX: Import from constants module to avoid circular import
    from .compatibility_constants import ELEMENT_COMPATIBILITY
    elem_key = (element1, element2) if (element1, element2) in ELEMENT_COMPATIBILITY else (element2, element1)
    if elem_key in ELEMENT_COMPATIBILITY:
        elem_compat = ELEMENT_COMPATIBILITY[elem_key][0]
        if elem_compat == "high":
            base += 10
        elif elem_compat == "low":
            base -= 10
    
    return min(100, max(0, base))

