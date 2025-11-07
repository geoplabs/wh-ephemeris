# 📚 Phrasebank Integration Architecture

## 🎯 Overview

This document describes the integration of the advanced `phrasebank.py` variation engine (941 lines) with the existing narrative generation system. Phase 3 is now **enabled by default** with enhanced quality features.

---

## 🏗️ Architecture Components

### **1. Core Systems**

| **Component** | **File** | **Purpose** | **Lines** |
|--------------|----------|-------------|-----------|
| **Phrasebank Engine** | `src/content/phrasebank.py` | Variation engine with QA, guardrails, constraints | 941 |
| **Variation Engine** | `src/content/variation.py` | Weighted selection with anti-repetition | 303 |
| **Inflection** | `src/content/inflection.py` | Grammatical transformations (gerunds, articles) | 385 |
| **Integration Bridge** | `api/services/option_b_cleaner/phrasebank_integration.py` | Bridge layer | **NEW** |

### **2. Integration Layer**

#### **`phrasebank_integration.py`** (NEW)

**Functions:**
```python
get_enhanced_bullets(area, mode, keywords, event=None, archetype="support", intensity="steady")
    → Uses phrasebank.py to generate quality-checked bullets

apply_qa_polish(text, area="general", check_cliches=True, check_length=True)
    → Applies QA linting (sentence length, clichés, duplicates)

inject_driver_microcopy(text, events, max_injections=1)
    → Injects astrological pattern hints ("Energy peaks—tackle a meaty task.")

get_archetype_from_tone(tone)
    → Maps tone to phrasebank archetype

get_intensity_from_score(score)
    → Maps event score to intensity level
```

---

## 📊 Integration Points

### **Point 1: Bullet Generation (`clean.py`)**

**Before:**
```python
def imperative_bullet(s, order, mode, area=None, asset=None):
    # Directly formats from phrases.json templates
    templates = _resolve_templates(area, mode, asset)
    # ... template formatting ...
```

**After:**
```python
def imperative_bullet(s, order, mode, area=None, asset=None, event=None, use_phrasebank=True):
    # Try phrasebank integration first
    if use_phrasebank and area:
        bullets = get_enhanced_bullets(
            area=area,
            mode=mode,
            keywords=keywords,
            event=event,
            archetype=archetype,
            intensity=intensity,
        )
        if bullets:
            return bullets[0]
    
    # Fallback to original template system
    # ... original logic ...
```

**Benefits:**
- ✅ Uses `VariationEngine` for anti-repetition
- ✅ Applies QA checks automatically
- ✅ Deterministic seeding from events
- ✅ Graceful fallback to original system

---

### **Point 2: Paragraph Composition (`language.py`)**

**Before:**
```python
def _compose_paragraph(lead, evidence, closing):
    parts = [lead] + list(evidence) + [closing]
    return " ".join(parts).strip()
```

**After:**
```python
def _compose_paragraph(lead, evidence, closing, area="general", events=None, apply_qa=True):
    parts = [lead] + list(evidence) + [closing]
    result = " ".join(parts).strip()
    
    # Apply phrasebank QA polish
    result = apply_qa_polish(result, area=area)
    
    # Inject driver microcopy if events present
    if events:
        result = inject_driver_microcopy(result, events, max_injections=1)
    
    return result
```

**Benefits:**
- ✅ Automatic sentence length checks (12-18 words avg)
- ✅ Cliché detection and replacement
- ✅ Driver microcopy injection from astrological patterns
- ✅ Area-specific context awareness

---

### **Point 3: Event-Driven Paragraphs**

**Updated `_build_story_paragraph()`:**
```python
# Collect events for QA context
events_list = [event, supporting_event] if event and supporting_event else \
              [event] if event else \
              [supporting_event] if supporting_event else None

return _compose_paragraph(
    opener, 
    evidence, 
    closing, 
    area=area,         # ← Area context for QA
    events=events_list, # ← Events for driver microcopy
    apply_qa=True       # ← Enable QA polish
)
```

---

## 🎛️ Feature Flags

### **Phase 3 (Planet-Specific Templates)**
```bash
export ENABLE_PHASE3=true  # ← DEFAULT (now enabled by default)
```

**When enabled:**
- Uses planet-specific templates from `storylets.json`
- Example: Mars transits → "You channel fierce momentum..."
- Falls back to generic templates if planet not found

### **Phrasebank Integration (Bullets)**
```python
# In code - controlled per call
imperative_bullet(..., use_phrasebank=True)  # ← DEFAULT
imperative_bullet(..., use_phrasebank=False) # ← Disable, use original
```

### **QA Polish (Paragraphs)**
```python
# In _compose_paragraph
_compose_paragraph(..., apply_qa=True)  # ← DEFAULT
_compose_paragraph(..., apply_qa=False) # ← Disable QA checks
```

---

## 📈 Quality Improvements

### **Before Integration:**
```json
{
  "career": {
    "bullets": [
      "Focus on full Moon while tracking status updates.",
      "Focus on radiant drive while tracking deliverables.",
      "Focus on outer persona radiant energy while tracking scope."
    ]
  }
}
```

**Issues:**
- ❌ Raw event data ("full Moon", "outer persona radiant energy")
- ❌ Repetitive structure ("Focus on... while tracking...")
- ❌ Over-use of "radiant" (9x in response)

### **After Integration:**
```json
{
  "career": {
    "bullets": [
      "Prioritize strategic milestones for clear progress.",
      "Organize scope boundaries so deliverables stay measured.",
      "Clarify stakeholder updates before noon."
    ]
  }
}
```

**Improvements:**
- ✅ Event keywords filtered (moon, eclipse, culmination, etc.)
- ✅ Varied structures from phrasebank templates
- ✅ Anti-repetition via `VariationEngine`
- ✅ Area-specific lexicon ("milestones", "scope", "stakeholders" for career)

---

## 🔬 Phrasebank Features

### **1. Variation Engine**
```python
from src.content.variation import VariationEngine

engine = VariationEngine(seed=12345)
result = engine.weighted_choice(options, weights=[1, 2, 1])
# → Uses decay factor to reduce repetition
```

### **2. QA Linting**
```python
metrics = get_qa_metrics(text)
# Returns:
{
  "avg_sentence_length": 15.2,
  "passes_length_check": True,
  "has_cliches": False,
  "has_duplicates": False,
  "passes_checks": True
}
```

### **3. Driver Tags**
```python
# Maps astrological patterns to microcopy
"Sun_conj_Mars" → "Energy peaks—tackle a meaty task."
"Mercury_sextile_ASC" → "Conversations open doors—start one."
"Moon_square_MC" → "Keep public commitments light."
```

### **4. Guardrails (Area-Specific)**
```python
# Health/Finance areas get softer language
"health": {
  "modal_verbs": ["consider", "aim to", "try to"],
  "banned_verbs": ["must", "should", "need to"],
  "disclaimer_suffix": " Adjust to your needs."
}
```

### **5. Constraints**
```python
{
  "max_sentence_length": 22,
  "banned_bigrams": ["Momentum guides", "radiant energy"],
  "dedupe_window": 3,  # Avoid same phrase in last 3 picks
  "capitalize_first": True,
  "end_with_period": True
}
```

---

## 🧪 Testing

### **Test Case 1: Bullet Generation**
```python
from api.services.option_b_cleaner.phrasebank_integration import get_enhanced_bullets

bullets = get_enhanced_bullets(
    area="career",
    mode="do",
    keywords=["strategic", "planning", "stakeholders"],
    event={"score": 2.5, "transit_body": "mercury"},
    archetype="support",
    intensity="steady",
    order=0
)

# Expected: 2-3 varied bullets without repetition
assert len(bullets) >= 2
assert bullets[0] != bullets[1]
```

### **Test Case 2: QA Polish**
```python
from api.services.option_b_cleaner.phrasebank_integration import apply_qa_polish

text = "You should really, really focus on steady momentum today and tomorrow."
polished = apply_qa_polish(text, area="career")

# Expected: Clichés replaced, duplicates removed
```

### **Test Case 3: Driver Microcopy**
```python
from api.services.option_b_cleaner.phrasebank_integration import inject_driver_microcopy

text = "You channel energy into work."
events = [{"transit_body": "Sun", "natal_body": "Mars", "aspect": "conjunction"}]

result = inject_driver_microcopy(text, events)
# Expected: "You channel energy into work. Energy peaks—tackle a meaty task."
```

---

## 🚀 Deployment

### **Local Development:**
```bash
# Phase 3 is enabled by default, no environment variable needed
docker-compose build api
docker-compose up -d api
```

### **Production (AWS ECS):**
```bash
# Update task-def-clean.json (environment section)
{
  "name": "ENABLE_PHASE3",
  "value": "true"  # ← Already set to "true" by default in code
}

# Deploy
./deploy-to-aws.ps1
```

---

## 📊 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    API Request                                  │
│                        ↓                                        │
│               render.py::build_context()                        │
│                        ↓                                        │
│            ┌──────────────────────────────┐                     │
│            │  language.py Paragraphs      │                     │
│            │  ├─ build_career_paragraph() │                     │
│            │  ├─ build_love_paragraph()   │                     │
│            │  └─ build_health_paragraph() │                     │
│            └────────────┬─────────────────┘                     │
│                         ↓                                       │
│         ┌───────────────────────────────────┐                   │
│         │ _build_story_paragraph()          │                   │
│         │  ├─ opener (Phase 3?)             │                   │
│         │  ├─ evidence sentences            │                   │
│         │  ├─ coaching                      │                   │
│         │  └─ closing                       │                   │
│         └────────────┬──────────────────────┘                   │
│                      ↓                                          │
│         ┌────────────────────────────────┐                      │
│         │ _compose_paragraph()           │                      │
│         │  ├─ apply_qa_polish() ✨       │ ← NEW               │
│         │  └─ inject_driver_microcopy() ✨│ ← NEW               │
│         └────────────┬───────────────────┘                      │
│                      ↓                                          │
│         ┌──────────────────────────────┐                        │
│         │  Bullet Generation           │                        │
│         │  clean.py::imperative_bullet()│                       │
│         │    ├─ get_enhanced_bullets() ✨│ ← NEW                │
│         │    └─ fallback to templates   │                       │
│         └──────────────┬───────────────┘                        │
│                        ↓                                        │
│              ┌─────────────────────┐                            │
│              │ phrasebank.py       │                            │
│              │  ├─ VariationEngine │                            │
│              │  ├─ QA Linting      │                            │
│              │  ├─ Driver Tags     │                            │
│              │  └─ Guardrails      │                            │
│              └─────────────────────┘                            │
│                        ↓                                        │
│                  Final JSON                                     │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Summary

| **Feature** | **Status** | **Benefit** |
|------------|-----------|------------|
| **Phase 3 Enabled** | ✅ Default ON | Planet-specific narrative templates |
| **Phrasebank Bullets** | ✅ Integrated | QA-checked, varied, event-aware bullets |
| **QA Polish** | ✅ Auto-applied | Sentence length, clichés, duplicates |
| **Driver Microcopy** | ✅ Auto-injected | Astrological pattern hints |
| **Guardrails** | ✅ Area-aware | Softer language for health/finance |
| **Variation Engine** | ✅ Active | Anti-repetition, weighted selection |
| **Graceful Fallback** | ✅ Built-in | Never breaks existing functionality |

---

## 🔧 Future Enhancements

### **Phase 4 (Potential):**
1. **Aspect-aware coaching** - Different coaching sentences for conjunctions vs trines
2. **Intensity-based closers** - Strong vs gentle closing recommendations
3. **Cross-area coherence** - Ensure career + love narratives don't contradict
4. **User preference learning** - Adapt tone based on user feedback
5. **Multi-language support** - Extend phrasebank to other languages

---

## 📞 Support

For questions or issues:
1. Check `phrasebank_integration.py` for integration points
2. Review `src/content/phrasebank.py` for engine details
3. Test with `use_phrasebank=False` to isolate integration issues
4. Check logs for `phrasebank_integration::` prefixed messages

---

**Last Updated:** 2025-11-07  
**Version:** 1.0.0  
**Author:** Narrative Integration Team

