"""
Compatibility Engine - Pair-Aware Aspect Weighting

Features:
- Context-aware scoring (love/friendship/business/generic)
- Pair-aware aspect weighting (Venus-Mars square positive in love!)
- Rule-based defaults for common coverage
- Explicit overrides for high-impact pairs
- Order-invariant pair normalization
- Circular midpoint for composite charts
- Deterministic iteration (stable across environments)
- Best aspect per pair (prevents overcount)

Note: "Rule-based defaults" provide coverage for most combinations,
but "comprehensive overrides" only seed high-impact pairs. Additional
pairs can be added to seed_overrides() as needed.

GENDER FIELD DECISION:
This module does NOT use gender for scoring (longitude-based calculations only).
Gender may be useful for downstream interpretation/narratives:
- Pronouns (already supported via optional schema fields - recommended)
- Cultural narratives (e.g., "masculine/feminine polarity" interpretations)
- Future matching logic variants

Recommendation: Add optional gender field to request schemas if needed:
  gender?: "male" | "female" | "nonbinary" | "unspecified"
Keep it outside this math layer - use in narrative/LLM layer only.
Pronouns are preferred (more inclusive, direct usage).
"""

from typing import Dict, Any, List, Tuple
import math
from . import ephem, aspects as aspects_svc
from .constants import sign_name_from_lon

# -----------------------------
# Core Constants
# -----------------------------
ASPECT_AFFECTION: Dict[str, float] = {
    "conjunction": 3.0,
    "trine": 2.0,
    "sextile": 1.0,
    "square": -2.0,
    "opposition": -2.0,
}

# Normalized pair weights (always store with p1 <= p2)
PAIR_WEIGHTS: Dict[Tuple[str, str], float] = {
    ("Jupiter", "Moon"): 1.3,
    ("Jupiter", "Sun"): 1.3,
    ("Mars", "Mars"): 2.0,
    ("Mercury", "Mercury"): 1.5,
    ("Moon", "Mars"): 1.6,
    ("Moon", "Moon"): 3.0,
    ("Moon", "Venus"): 1.7,
    ("Saturn", "Moon"): 1.4,
    ("Saturn", "Sun"): 1.4,
    ("Sun", "Mars"): 1.4,
    ("Sun", "Moon"): 3.0,
    ("Sun", "Sun"): 2.0,
    ("Sun", "Venus"): 1.5,
    ("Venus", "Mars"): 3.0,
    ("Venus", "Venus"): 2.0,
}

# Aspect type sets
HARD = {"square", "opposition"}
SOFT = {"trine", "sextile"}
CONJ = {"conjunction"}

# Valid contexts (for validation)
VALID_CONTEXTS = {"love", "friendship", "business", "generic"}

# FIX #3: Context aliases for better DX
CONTEXT_ALIASES = {
    "dating": "love",
    "romance": "love",
    "romantic": "love",
    "relationship": "love",
    "work": "business",
    "career": "business",
    "professional": "business",
    "colleague": "business",
    "friends": "friendship",
    "platonic": "friendship",
}

# Planet classifications
PLANET_CLASS: Dict[str, str] = {
    "Sun": "luminary",
    "Moon": "luminary",
    "Mercury": "personal",
    "Venus": "personal",
    "Mars": "personal",
    "Jupiter": "social",
    "Saturn": "social",
    "Uranus": "outer",
    "Neptune": "outer",
    "Pluto": "outer",
    "TrueNode": "point",
    "MeanNode": "point",
    "Chiron": "point",
    "Lilith": "point",
}

# Allowed bodies for synastry (FIX #5: filter unknown bodies)
ALLOWED_BODIES = set(PLANET_CLASS.keys())

# Planet ordering for deterministic composite output
PLANET_ORDER = [
    "Sun", "Moon", "Mercury", "Venus", "Mars",
    "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    "TrueNode", "MeanNode", "Chiron", "Lilith"
]

# -----------------------------
# Override Tables
# -----------------------------
ASPECT_BASE_OVERRIDES: Dict[Tuple[str, str, str, str], float] = {}
ASPECT_MULT_OVERRIDES: Dict[Tuple[str, str, str, str], float] = {}
_OVERRIDES_SEEDED = False  # FIX #4: Idempotency guard

# -----------------------------
# Helper Functions
# -----------------------------
def _norm_pair(a: str, b: str) -> Tuple[str, str]:
    """Normalize pair to alphabetical order for consistent lookup."""
    return (a, b) if a <= b else (b, a)

def get_pair_weight(p1: str, p2: str) -> float:
    """
    Get pair weight with automatic bidirectional lookup.
    FIX #1: Centralized helper prevents silent mis-scoring.
    """
    return PAIR_WEIGHTS.get(_norm_pair(p1, p2), 1.0)

def normalize_context(context: str) -> str:
    """
    Normalize and validate context string with alias support.
    FIX #3: Prevents silent rule failures from typos like "Love" or "dating".
    Now supports aliases: "dating" → "love", "work" → "business", etc.
    """
    ctx = (context or "generic").lower().strip()
    
    # Check aliases first
    if ctx in CONTEXT_ALIASES:
        return CONTEXT_ALIASES[ctx]
    
    # Then check valid contexts
    return ctx if ctx in VALID_CONTEXTS else "generic"

def angle_diff(lon1: float, lon2: float) -> float:
    """
    Calculate shortest arc (0..180) between two longitudes.
    Unsigned distance - correct for aspect matching, not for applying/separating logic.
    """
    diff = abs(lon1 - lon2)
    return 360.0 - diff if diff > 180.0 else diff

def circular_midpoint(a: float, b: float) -> float:
    """
    Circular mean of two angles (handles 360/0 wrap correctly).
    Example: midpoint(350, 10) = 0, not 180.
    
    FIX #2: Handles 180° opposition edge case (when vector sum ≈ 0).
    """
    a_r = math.radians(a)
    b_r = math.radians(b)
    x = math.cos(a_r) + math.cos(b_r)
    y = math.sin(a_r) + math.sin(b_r)
    
    # FIX #2: Edge case - if planets are exactly opposite (180° apart),
    # vector sum is ~0 and atan2 becomes ambiguous. Fall back to arithmetic mean.
    if abs(x) < 1e-10 and abs(y) < 1e-10:
        # Arithmetic mean with wrap handling
        diff = abs(b - a)
        if diff > 180:
            # Wrap case: take mean of smaller arc
            return ((a + b) / 2 + 180) % 360.0
        return (a + b) / 2 % 360.0
    
    return math.degrees(math.atan2(y, x)) % 360.0

def _pair_class(p1: str, p2: str) -> str:
    """
    Classify planet pair for rule-based weighting.
    FIX #2: Added Jupiter/Mars/Venus categories for better business/friendship scoring.
    """
    s = {p1, p2}
    
    # High-impact specific pairs
    if s == {"Venus", "Mars"}:
        return "romance"
    if "Venus" in s and "Moon" in s:
        return "affection"
    if s == {"Sun", "Moon"}:
        return "core"
    
    # FIX #2: Add Jupiter, Mars-involved, Venus-involved categories
    if "Jupiter" in s:
        # Jupiter pairs: growth, expansion, optimism
        other = (s - {"Jupiter"}).pop() if len(s) == 2 else None
        if other in {"Sun", "Moon", "Venus", "Mars", "Mercury"}:
            return "growth"
    
    if "Mars" in s and "Venus" not in s:
        # Mars-involved (non-romantic): drive, action, energy
        other = (s - {"Mars"}).pop() if len(s) == 2 else None
        if other in {"Sun", "Moon", "Mercury"}:
            return "drive"
    
    if "Venus" in s and "Mars" not in s:
        # Venus-involved (non-romantic): values, harmony, cooperation
        other = (s - {"Venus"}).pop() if len(s) == 2 else None
        if other in {"Sun", "Mercury"}:
            return "values"
    
    if "Saturn" in s:
        return "saturn"
    if "Mercury" in s:
        return "communication"
    
    # Generic classifications
    pc1 = PLANET_CLASS.get(p1, "other")
    pc2 = PLANET_CLASS.get(p2, "other")
    
    if pc1 == "outer" or pc2 == "outer":
        return "outer"
    if pc1 == "point" or pc2 == "point":
        return "point"
    
    return "neutral"

# -----------------------------
# Override Management
# -----------------------------
def _set_base(p1: str, p2: str, aspect: str, ctx: str, val: float) -> None:
    """
    Set explicit base override for a pair-aspect-context combination.
    FIX #5: Validates override ranges to prevent accidental weight explosions.
    """
    a, b = _norm_pair(p1, p2)
    val = float(val)
    
    # FIX #5: Validate override range (bases should be reasonable)
    if abs(val) > 10.0:
        raise ValueError(f"Base override {val} for {(a,b,aspect,ctx)} exceeds safe range [-10, 10]")
    
    ASPECT_BASE_OVERRIDES[(a, b, aspect, ctx)] = val

def _set_mult(p1: str, p2: str, aspect: str, ctx: str, val: float) -> None:
    """
    Set explicit multiplier override for a pair-aspect-context combination.
    FIX #5: Validates override ranges to prevent accidental weight explosions.
    """
    a, b = _norm_pair(p1, p2)
    val = float(val)
    
    # FIX #5: Validate multiplier range (should be reasonable boost/reduction)
    if val < 0.1 or val > 3.0:
        raise ValueError(f"Multiplier override {val} for {(a,b,aspect,ctx)} outside safe range [0.1, 3.0]")
    
    ASPECT_MULT_OVERRIDES[(a, b, aspect, ctx)] = val

def seed_overrides() -> None:
    """
    Seed high-impact overrides for planetary combinations.
    FIX #4: Guarded to prevent multiple seeding.
    """
    global _OVERRIDES_SEEDED
    if _OVERRIDES_SEEDED:
        return
    
    # Venus-Mars: romantic chemistry (positive squares in love!)
    _set_base("Venus", "Mars", "square", "love", 0.8)
    _set_base("Venus", "Mars", "opposition", "love", 1.2)
    _set_mult("Venus", "Mars", "square", "love", 1.10)
    _set_mult("Venus", "Mars", "opposition", "love", 1.15)
    
    # Saturn: heavy responsibility
    _set_base("Saturn", "Sun", "square", "generic", -3.0)
    _set_base("Saturn", "Sun", "opposition", "generic", -3.0)
    _set_base("Saturn", "Moon", "square", "generic", -2.6)
    _set_base("Saturn", "Moon", "opposition", "generic", -2.6)
    
    # Mercury: communication dynamics
    _set_mult("Mercury", "Mercury", "trine", "generic", 1.15)
    _set_mult("Mercury", "Mercury", "sextile", "generic", 1.10)
    _set_base("Mercury", "Mercury", "square", "generic", -1.8)
    _set_base("Mercury", "Mercury", "opposition", "generic", -1.8)
    
    # Points: softer influence (don't dominate)
    for pt in ["TrueNode", "MeanNode", "Chiron", "Lilith"]:
        for core in ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]:
            _set_mult(pt, core, "conjunction", "generic", 0.75)
            _set_mult(pt, core, "square", "generic", 0.70)
            _set_mult(pt, core, "opposition", "generic", 0.70)
            _set_mult(pt, core, "trine", "generic", 0.80)
            _set_mult(pt, core, "sextile", "generic", 0.80)
    
    _OVERRIDES_SEEDED = True

# Initialize overrides at module load (idempotent)
seed_overrides()

# -----------------------------
# Pair-Aware Aspect Weighting
# -----------------------------
def get_aspect_base(planet1: str, planet2: str, aspect_type: str, context: str = "generic") -> float:
    """
    Get pair-aware base score for an aspect.
    
    Priority:
    1. Explicit override for (pair, aspect, context)
    2. Explicit override for (pair, aspect, "generic")
    3. Rule-based defaults using pair_class
    4. Baseline ASPECT_AFFECTION
    """
    p1, p2 = _norm_pair(planet1, planet2)
    context = normalize_context(context)  # FIX #3: Validate context
    
    # Check explicit overrides
    if (p1, p2, aspect_type, context) in ASPECT_BASE_OVERRIDES:
        return ASPECT_BASE_OVERRIDES[(p1, p2, aspect_type, context)]
    if (p1, p2, aspect_type, "generic") in ASPECT_BASE_OVERRIDES:
        return ASPECT_BASE_OVERRIDES[(p1, p2, aspect_type, "generic")]
    
    # Rule-based defaults
    base = ASPECT_AFFECTION.get(aspect_type, 0.0)
    pc = _pair_class(p1, p2)
    
    if aspect_type in HARD:
        if context == "love":
            if pc == "romance":
                base = 0.6 if aspect_type == "square" else 0.9
            elif pc == "affection":
                base = base + 0.4
            elif pc == "saturn":
                base = base - 0.8
            elif pc == "outer":
                base = base - 0.4
            elif pc == "point":
                base = base * 0.6
            # FIX #2: Add growth/drive/values rules
            elif pc == "growth":
                base = base * 0.8  # Jupiter hard aspects softer in love
        elif context == "business":
            if pc == "saturn":
                base = base * 0.7  # Saturn slightly softer in business
            elif pc == "romance":
                base = base * 0.5  # Romance pairs less relevant
            elif pc == "growth":
                base = base * 0.75  # Jupiter challenges manageable
            elif pc == "values":
                base = base - 0.3  # Venus values important
            elif pc == "point":
                base = base * 0.7
        elif context == "friendship":
            if pc == "communication":
                base = base - 0.2  # Mercury challenges matter
            elif pc == "romance":
                base = base * 0.7
            elif pc == "growth":
                base = base * 0.8  # Jupiter more forgiving
            elif pc == "point":
                base = base * 0.7
    
    elif aspect_type in SOFT:
        if context == "love" and pc in {"romance", "affection"}:
            base = base + 0.3
        # FIX #2: Growth/values boost in relevant contexts
        if context == "business" and pc == "growth":
            base = base + 0.2  # Jupiter soft aspects great for business
        if context in ["business", "friendship"] and pc == "values":
            base = base + 0.15  # Venus harmony helpful
        if pc == "point":
            base = base * 0.8
    
    return float(base)

def get_aspect_multiplier(planet1: str, planet2: str, aspect_type: str, context: str = "generic") -> float:
    """
    Get pair-aware multiplier for an aspect.
    
    Priority:
    1. Explicit override for (pair, aspect, context)
    2. Explicit override for (pair, aspect, "generic")
    3. Rule-based defaults using pair_class
    4. 1.0 (neutral)
    """
    p1, p2 = _norm_pair(planet1, planet2)
    context = normalize_context(context)  # FIX #3: Validate context
    
    # Check explicit overrides
    if (p1, p2, aspect_type, context) in ASPECT_MULT_OVERRIDES:
        return ASPECT_MULT_OVERRIDES[(p1, p2, aspect_type, context)]
    if (p1, p2, aspect_type, "generic") in ASPECT_MULT_OVERRIDES:
        return ASPECT_MULT_OVERRIDES[(p1, p2, aspect_type, "generic")]
    
    # Rule-based defaults
    mult = 1.0
    pc = _pair_class(p1, p2)
    
    if pc == "point":
        mult *= 0.75
    if pc == "outer" and aspect_type in SOFT:
        mult *= 0.90
    
    if context == "love":
        if pc in {"romance", "affection"} and aspect_type in (SOFT | CONJ):
            mult *= 1.15
        if pc == "saturn" and aspect_type in HARD:
            mult *= 1.10
    elif context == "business":
        if pc == "communication" and aspect_type in SOFT:
            mult *= 1.10
        # FIX #2: Growth boost in business
        if pc == "growth" and aspect_type in SOFT:
            mult *= 1.15
    elif context == "friendship":
        # FIX #2: Drive compatibility in friendship
        if pc == "drive" and aspect_type in SOFT:
            mult *= 1.10
    
    # Clamp to reasonable range
    return float(max(0.5, min(1.5, mult)))

# -----------------------------
# Ephemeris Integration
# -----------------------------
def natal_positions(chart_input: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """
    Calculate natal positions from chart input.
    
    PUBLIC API - stable interface for computing planetary positions.
    
    FIX #4: Validates required fields to prevent cryptic KeyErrors in production.
    PRODUCTION FIX #4: Wraps ephem failures with clear error messages.
    """
    # FIX #4: Input validation
    required_fields = ["system", "date", "time", "place"]
    missing = [f for f in required_fields if f not in chart_input]
    if missing:
        raise ValueError(f"chart_input missing required fields: {missing}")
    
    if "tz" not in chart_input.get("place", {}):
        raise ValueError("chart_input.place missing required field: 'tz'")
    
    # PRODUCTION FIX #4: Wrap ephem calls for better error messages
    try:
        sidereal = chart_input["system"] == "vedic"
        ayan = ((chart_input.get("options") or {}).get("ayanamsha", "lahiri") if sidereal else None)
        jd = ephem.to_jd_utc(chart_input["date"], chart_input["time"], chart_input["place"]["tz"])
        return ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)
    except (ValueError, TypeError, KeyError) as e:
        # Re-raise with clear context about what went wrong
        raise ValueError(
            f"Invalid date/time/place/tz format in chart_input. "
            f"Check: date='{chart_input.get('date')}', time='{chart_input.get('time')}', "
            f"tz='{chart_input.get('place', {}).get('tz')}'. Error: {e}"
        ) from e

# -----------------------------
# Synastry (Aspect Calculation)
# -----------------------------
def synastry(
    person_a: Dict[str, Any],
    person_b: Dict[str, Any],
    aspect_types,
    orb_deg: float,
    *,
    context: str = "generic",
    orb_model: str = "quadratic"
) -> List[Dict[str, Any]]:
    """
    Calculate synastry aspects between two natal charts.
    
    Args:
        person_a: First person's chart data
        person_b: Second person's chart data
        aspect_types: List/set of aspect types to consider (if None, uses all MAJOR)
        orb_deg: Maximum orb in degrees
        context: "love" | "friendship" | "business" | "generic" (auto-validated)
        orb_model: "quadratic" (tight aspects favored) | "linear" (validated)
    
    Returns:
        List of aspects sorted by weight (highest first)
    
    Features:
        - Context-aware weighting (Venus-Mars square positive in love!)
        - Pair-aware base scores
        - Quadratic orb falloff (tight aspects weighted more)
        - Order-invariant pair normalization
        - Deterministic iteration (PLANET_ORDER)
        - Best aspect per pair (prevents overcount)
    
    Note: "Best aspect per pair" keeps only the closest orb for each planet pair.
    This prevents duplicate/overcount when using large orbs. For typical orb
    settings (6-8°), this rarely matters, but for larger orbs (10-15°), it ensures
    clean results. If you need "top N aspects per pair" in the future, modify
    the best_per_pair logic to track a list instead of a single dict.
    """
    # PRODUCTION FIX #1: Validate aspect_types
    if aspect_types is None or len(aspect_types) == 0:
        aspect_types = list(aspects_svc.MAJOR.keys())
    
    # PRODUCTION FIX #2: Validate orb_model
    if orb_model not in {"quadratic", "linear"}:
        raise ValueError(f"orb_model must be 'quadratic' or 'linear', got '{orb_model}'")
    
    # PRODUCTION FIX #4: Wrap ephem failures with clear error
    try:
        A = natal_positions(person_a)
        B = natal_positions(person_b)
    except Exception as e:
        # Re-raise with clearer context
        raise ValueError(f"Failed to calculate natal positions: {e}") from e
    
    # FIX #5: Filter to allowed bodies only
    A = {k: v for k, v in A.items() if k in ALLOWED_BODIES}
    B = {k: v for k, v in B.items() if k in ALLOWED_BODIES}
    
    # FIX #3: Normalize and validate context
    context = normalize_context(context)
    
    orb_deg_eff = max(0.1, float(orb_deg))
    
    def orb_factor(orb: float) -> float:
        """Calculate orb falloff factor."""
        x = max(0.0, min(1.0, 1.0 - (orb / orb_deg_eff)))
        return x * x if orb_model == "quadratic" else x
    
    # Convert aspect_types to set for O(1) membership
    aspect_types_set = set(aspect_types) if not isinstance(aspect_types, set) else aspect_types
    
    # FIX #1: Track best aspect per pair (prevents duplicate/overcount with large orbs)
    best_per_pair: Dict[Tuple[str, str], Dict[str, Any]] = {}
    
    # PRODUCTION FIX #3: Deterministic iteration order (use PLANET_ORDER)
    # Get planet names in deterministic order
    planets_a = [p for p in PLANET_ORDER if p in A]
    planets_b = [p for p in PLANET_ORDER if p in B]
    
    # Add any extra planets not in PLANET_ORDER (sorted)
    extras_a = sorted(set(A.keys()) - set(PLANET_ORDER))
    extras_b = sorted(set(B.keys()) - set(PLANET_ORDER))
    planets_a.extend(extras_a)
    planets_b.extend(extras_b)
    
    for a_name in planets_a:
        a_pos = A[a_name]
        for b_name in planets_b:
            b_pos = B[b_name]
            # Safety: skip if lon missing
            if "lon" not in a_pos or "lon" not in b_pos:
                continue
            
            d = angle_diff(a_pos["lon"], b_pos["lon"])
            pair_key = _norm_pair(a_name, b_name)
            
            for t, exact in aspects_svc.MAJOR.items():
                if t not in aspect_types_set:
                    continue
                
                if abs(d - exact) <= orb_deg_eff:
                    orb = round(abs(d - exact), 2)
                    
                    # Pair-aware weighting
                    base = get_aspect_base(a_name, b_name, t, context=context)
                    mult = get_aspect_multiplier(a_name, b_name, t, context=context)
                    pair_boost = get_pair_weight(a_name, b_name)  # FIX #1: Use helper
                    
                    # Final weight
                    w = base * pair_boost * mult * orb_factor(orb)
                    
                    aspect_data = {
                        "p1": a_name,
                        "p2": b_name,
                        "type": t,
                        "orb": orb,
                        "weight": round(w, 2),
                        "context": context,
                    }
                    
                    # FIX #1: Keep only closest (smallest orb) aspect per pair
                    if pair_key not in best_per_pair or orb < best_per_pair[pair_key]["orb"]:
                        best_per_pair[pair_key] = aspect_data
    
    # Convert to list and sort deterministically (P0-4: handle ties)
    res = list(best_per_pair.values())
    # Sort by: weight desc, orb asc, p1 asc, p2 asc, type asc
    res.sort(key=lambda x: (-x["weight"], x["orb"], x["p1"], x["p2"], x["type"]))
    return res

# -----------------------------
# Composite Chart (Midpoint)
# -----------------------------
def midpoint_composite(person_a: Dict[str, Any], person_b: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Calculate midpoint composite by longitude averaging (circular mean).
    
    NOTE: This is NOT Davison method. Davison requires midpoint time/place
    and computing a real chart. This simply averages planet longitudes.
    
    Returns:
        List of composite planets in deterministic order
    """
    A = natal_positions(person_a)
    B = natal_positions(person_b)
    
    # FIX #5: Filter to allowed bodies
    A = {k: v for k, v in A.items() if k in ALLOWED_BODIES}
    B = {k: v for k, v in B.items() if k in ALLOWED_BODIES}
    
    # Safe intersection: only planets present in both charts
    common = set(A.keys()) & set(B.keys())
    
    # Deterministic ordering
    ordered = [p for p in PLANET_ORDER if p in common]
    extras = sorted(common - set(PLANET_ORDER))
    names = ordered + extras
    
    comp: List[Dict[str, Any]] = []
    for name in names:
        lon = circular_midpoint(A[name]["lon"], B[name]["lon"])
        comp.append({
            "name": name,
            "lon": round(lon, 2),
            "sign": sign_name_from_lon(lon),
            "house": None,  # Not computed (requires composite location/time)
        })
    
    return comp

# -----------------------------
# Aggregate Scoring
# -----------------------------
def aggregate_score(
    syn: List[Dict[str, Any]],
    *,
    mode: str = "sigmoid",
    clamp_abs: float = 30.0,
    sigmoid_scale: float = 15.0
) -> float:
    """
    Convert synastry aspect weights into 0-100 compatibility score.
    
    Args:
        syn: List of aspects with 'weight' field
        mode: "sigmoid" (smooth, better distribution) | "linear" (legacy)
        clamp_abs: Hard clamp for linear mode
        sigmoid_scale: Scale factor for sigmoid (15.0 = good spread)
    
    Returns:
        Score from 0 (worst) to 100 (best)
    
    Examples:
        - No aspects: ~50 (neutral)
        - Strong positive: 70-90
        - Many strong: 90-98 (not all 100 due to sigmoid)
        - Challenging: 20-40
    
    CALIBRATION NOTES:
    - sigmoid_scale=15.0 is initial estimate and may need tuning per context
    - To calibrate in production:
      1. Log total_weight distribution for love/friendship/business separately
      2. Check score histogram (should spread 20-95, not cluster at extremes)
      3. Adjust sigmoid_scale: smaller = more extreme spread, larger = flatter
      4. Typical range: 10-20 for good discrimination
    - Add telemetry: log (context, total_weight, final_score) for analysis
    """
    if not syn:
        return 50.0  # Neutral if no aspects
    
    total = float(sum(x.get("weight", 0.0) for x in syn))
    
    if mode == "linear":
        # Legacy mode: hard clamp
        total = max(-clamp_abs, min(clamp_abs, total))
        return round((total + clamp_abs) / (2.0 * clamp_abs) * 100.0, 1)
    
    # Sigmoid mode (default): smooth distribution, no ceiling collapse
    x = total / max(1e-6, sigmoid_scale)
    x = max(-60.0, min(60.0, x))  # Overflow guard
    score = 100.0 / (1.0 + math.exp(-x))
    return round(score, 1)
