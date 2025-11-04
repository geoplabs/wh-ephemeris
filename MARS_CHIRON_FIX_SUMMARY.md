# Mars-Chiron Aspect Polarity Fix

## 🐛 **Problem**

Mars trine Chiron (a **SUPPORTIVE** aspect with 0.03° orb) was incorrectly appearing in the **CAUTION WINDOW** instead of being recognized as a positive, supportive transit.

### Root Causes

1. **Aspect Weight Polarity Bug (`transits_engine.py`)**
   - ALL aspects (including trines and sextiles) were assigned POSITIVE weights
   - This caused supportive aspects to have positive scores (friction) instead of negative scores (support)
   
2. **Score Calculation Bug (`transits_engine.py`)**
   - The formula added aspect_weight + planet_weight, neutralizing the polarity
   - Formula didn't preserve the sign of the aspect weight

3. **Window Classification Bug (`caution_windows.py`)**
   - "Insight" severity (for Chiron aspects) was being upgraded to "Caution" when angles were involved
   - Supportive aspects should never be upgraded to caution

4. **Fallback Logic Bug (`render.py`)**
   - `_looks_challenging()` didn't check score polarity
   - Supportive events could be classified as "challenging" based on tone/intensity alone
   - Fallback logic could pick supportive events for caution window

## ✅ **Solution**

### 1. Fixed Aspect Weights (`api/services/transits_engine.py`)

```python
# BEFORE (ALL POSITIVE)
ASPECT_WEIGHTS = {
    "trine": 2,      # Wrong: positive (friction)
    "sextile": 1,    # Wrong: positive (friction)
    ...
}

# AFTER (CORRECT POLARITY)
ASPECT_WEIGHTS = {
    "trine": -2,         # Supportive (NEGATIVE)
    "sextile": -1,       # Supportive (NEGATIVE)
    "opposition": 4,     # Friction (POSITIVE)
    "square": 3,         # Friction (POSITIVE)
    ...
}
```

### 2. Fixed Score Calculation (`api/services/transits_engine.py`)

```python
# BEFORE
def _severity_score(aspect, orb, orb_limit, t_body):
    base = ASPECT_WEIGHTS.get(aspect, 1) + PLANET_WEIGHTS.get(t_body, 1)  # Neutralizes polarity!
    closeness = 1.0 - (orb / orb_limit)
    return 10.0 * (0.3*base/8.0 + 0.7*closeness)

# AFTER
def _severity_score(aspect, orb, orb_limit, t_body):
    """Calculate score with proper polarity: negative=supportive, positive=friction."""
    aspect_weight = ASPECT_WEIGHTS.get(aspect, 1)
    planet_weight = PLANET_WEIGHTS.get(t_body, 1)
    closeness = 1.0 - (orb / orb_limit)
    
    # Polarity from aspect, magnitude from planet & closeness
    polarity = 1 if aspect_weight > 0 else -1 if aspect_weight < 0 else 0
    magnitude = abs(aspect_weight) * planet_weight * closeness
    
    return round(polarity * magnitude * 3.0, 2)
```

### 3. Prevented Supportive->Caution Upgrade (`src/content/caution_windows.py`)

```python
# BEFORE
if _has_angle_trigger(contributors) and severity in {"No flag", "Gentle Note", "Support", "Insight"}:
    severity = "Caution"  # Wrong: upgrades supportive aspects!

# AFTER
if _has_angle_trigger(contributors) and severity in {"No flag", "Gentle Note"}:
    severity = "Caution"  # Only upgrade neutral aspects, NOT supportive ones
```

### 4. Added Score Check to `_looks_challenging` (`api/services/option_b_cleaner/render.py`)

```python
# BEFORE
looks_bad = _looks_challenging(aspect, note.lower(), tone, intensity)

# AFTER
score = event.get("score", 0)
# Supportive aspects (score < 0) should NEVER be used for caution
looks_bad = _looks_challenging(aspect, note.lower(), tone, intensity) and score > 0
```

### 5. Fixed Fallback to Filter Supportive Events (`api/services/option_b_cleaner/render.py`)

```python
# Fallback: use the first FRICTION event (score > 0), not supportive events
for item in enriched_events:
    fallback_event = item.get("event")
    if isinstance(fallback_event, Mapping):
        score = fallback_event.get("score", 0)
        if score > 0:  # Only use friction events
            ...return caution window...
```

## 📊 **Results**

### Before Fix:
- Mars trine Chiron: score = **+8.43** (positive/friction) ❌
- Appeared in: **CAUTION WINDOW** ❌
- Note: "Trust the momentum..." (positive language in caution!) ❌

### After Fix:
- Mars trine Chiron: score = **-11.88** (negative/supportive) ✅
- Appears in: **NOT in caution window** ✅
- Caution window: Shows Saturn square Venus (actual friction event) ✅

## 🧪 **Verification**

Test case: Birth 1984-01-24 06:06 Guwahati, Forecast 2025-11-04

**Events on 2025-11-04:**
- Mars trine Chiron: -11.88 (supportive)
- Saturn square Venus: +7.20 (friction)
- Mars sextile Ascendant: -4.28 (supportive)
- Moon trine Venus: -2.47 (supportive)
- Venus sextile Venus: -2.09 (supportive)

**Result:**
- ✅ Caution window: Saturn square Venus (friction)
- ✅ Lucky window: Supportive transits
- ✅ Mars-Chiron correctly excluded from caution

## 📝 **Files Modified**

1. `api/services/transits_engine.py` - Fixed aspect weights & score calculation
2. `src/content/caution_windows.py` - Prevented supportive->caution upgrade
3. `api/services/option_b_cleaner/render.py` - Added score checks to fallback logic

