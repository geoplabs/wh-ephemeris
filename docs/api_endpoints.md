# API Endpoint Reference

This guide documents the JSON contracts for every FastAPI route currently exposed by the `wh-ephemeris` service. All payloads are UTF-8 encoded JSON. Unless otherwise noted, responses use HTTP 200 for success and return `application/json` content.

## Root service

### `GET /`
Returns a simple service heartbeat message.

```json
{
  "message": "wh-ephemeris dev API is running. See /__health and /docs (when implemented)."
}
```

### `GET /__health`
Health check endpoint used by infrastructure monitors.

```json
{ "ok": true }
```

### `GET /dev-assets/{path}`
Development-only helper that streams PDF/SVG assets from the worker scratch directory. When the asset is missing, it responds with HTTP 404 and `{ "error": "not found" }`.

## Chart utilities

### `POST /v1/charts/compute`
Calculates a natal chart for the supplied birth data.

**Request JSON** (inherits from `ChartInput`):
```jsonc
{
  "system": "western",            // "western" | "vedic"
  "date": "YYYY-MM-DD",
  "time": "HH:MM:SS",
  "time_known": true,
  "place": {
    "lat": 0.0,
    "lon": 0.0,
    "tz": "Area/City",
    "query": "Optional free-form label"
  },
  "options": {                      // optional, e.g. {"house_system": "whole_sign"}
    "house_system": "placidus",
    "ayanamsha": "lahiri"
  }
}
```

**Response JSON**:
```jsonc
{
  "chart_id": "cht_xxxxxxxxxxxxxxxx",
  "meta": {
    "engine": "wh-ephemeris",
    "engine_version": "<semver>",
    "zodiac": "tropical",         // or "sidereal"
    "house_system": "placidus",
    "ayanamsha": "lahiri",         // present for Vedic charts
    "backend": "swieph",
    "warnings": ["optional warning strings"]
  },
  "angles": {                       // omitted when time is unknown
    "ascendant": 123.4567,
    "mc": 234.5678
  },
  "houses": [
    { "num": 1, "cusp_lon": 123.4567 },
    { "num": 2, "cusp_lon": 153.4567 }
  ],
  "bodies": [
    {
      "name": "Sun",
      "lon": 123.4567,
      "sign": "Leo",
      "house": 10,
      "retro": false,
      "speed": 0.9856,
      "nakshatra": { "name": "Ashlesha" } // Vedic-only
    }
  ],
  "aspects": [ { "p1": "Sun", "p2": "Moon", "type": "trine", "orb": 1.2, "applying": true } ]
}
```

## Transit engine

### `POST /v1/transits/compute`
Produces daily transit hits for a natal chart within a requested date range.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput as above */ },
  "options": {
    "from_date": "2025-01-01",
    "to_date": "2025-01-31",
    "step_days": 1,
    "transit_bodies": ["Sun", "Mercury", "Venus"],
    "natal_targets": ["Sun", "Moon"],
    "aspects": {
      "types": ["conjunction", "square", "trine", "opposition", "sextile"],
      "orb_deg": 3.0
    }
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "step_days": 1 },
  "events": [
    {
      "date": "2025-01-02",
      "transit_body": "Mercury",
      "natal_body": "Sun",
      "aspect": "sextile",
      "orb": 0.42,
      "applying": true,
      "score": 0.7,
      "note": "optional",
      "transit_sign": "Aquarius",
      "natal_sign": "Leo",
      "zodiac": "tropical"
    }
  ]
}
```

## Forecast endpoints

### `POST /v1/forecasts/daily`
Generates the structured payload used by the daily horoscope experiences.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": {
    "date": "2025-01-15",
    "user_id": "optional",
    "profile_name": "Asha",
    "use_ai": false,
    "generation_mode": "template",    // optional future switch
    "step_days": 1,
    "window_days": 1,
    "areas": ["career", "love", "health", "finance"],
    "transit_bodies": ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"],
    "natal_targets": null,
    "aspects": {
      "types": ["conjunction", "square", "trine", "opposition", "sextile"],
      "orb_deg": 3.0
    }
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "profile_name": "Asha", "date": "2025-01-15" },
  "summary": "Day overview...",
  "mood": "energized",
  "focus_areas": [
    {
      "area": "career",
      "score": 0.8,
      "headline": "Professional wins",
      "guidance": "Lean into collaboration",
      "events": [ /* ForecastEvent items */ ]
    }
  ],
  "events": [ /* ForecastEvent list */ ],
  "top_events": [ /* ForecastEvent list */ ],
  "lucky": {
    "color": "emerald",
    "time_window": "10:00-12:00",
    "direction": "north",
    "affirmation": "I trust my instincts"
  }
}
```

### `POST /v1/forecasts/daily/forecast`
Wraps the daily payload in a templated narrative layout. Request body is identical to `/daily`. Response swaps in AI/template copy fields.

**Response JSON**:
```jsonc
{
  "profile_name": "Asha",
  "date": "2025-01-15",
  "mood": "energized",
  "theme": "Embrace bold moves",
  "opening_summary": "...",
  "morning_mindset": { "paragraph": "...", "mantra": "I lead with heart" },
  "career": { "paragraph": "...", "bullets": ["Action item"] },
  "love": { "paragraph": "...", "attached": "...", "single": "..." },
  "health": { "paragraph": "...", "good_options": ["Yoga"] },
  "finance": { "paragraph": "...", "bullets": [] },
  "do_today": ["Reach out to a mentor"],
  "avoid_today": ["Overcommitting"],
  "caution_window": { "time_window": "18:00-20:00", "note": "Double-check details" },
  "remedies": ["Light a sandalwood incense"],
  "lucky": { "color": "emerald", "time_window": "10:00-12:00", "direction": "north", "affirmation": "I trust my instincts" },
  "one_line_summary": "Opportunities reward courage today."
}
```

### `POST /v1/forecasts/monthly`
Delivers the lightweight event feed that powers the monthly experience.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": {
    "year": 2025,
    "month": 9,
    "user_id": "optional",
    "profile_name": "Asha",
    "step_days": 1,
    "transit_bodies": ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Moon"],
    "aspects": {
      "types": ["conjunction", "square", "trine", "opposition"],
      "orb_deg": 3.0
    }
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "year": 2025, "month": 9 },
  "events": [ /* ForecastEvent list */ ],
  "highlights": [ /* ForecastEvent list */ ],
  "pdf_download_url": "optional presigned link"
}
```

### `POST /v1/forecasts/yearly`
Builds the annual transit digest.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": {
    "year": 2025,
    "user_id": "optional",
    "profile_name": "Asha",
    "step_days": 1,
    "include_progressions": true,
    "transit_bodies": ["Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"],
    "aspects": {
      "types": ["conjunction", "opposition", "square", "trine", "sextile"],
      "orb_deg": 3.0
    }
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "year": 2025 },
  "months": {
    "2025-01": [ /* ForecastEvent list */ ],
    "2025-02": [ /* ForecastEvent list */ ]
  },
  "top_events": [ /* ForecastEvent list */ ],
  "pdf_download_url": "optional"
}
```

## Interpretation endpoints

### `POST /v1/interpret/natal`
Returns narrative paragraphs for a natal chart.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": {
    "tone": "professional",
    "length": "medium",
    "language": "en",
    "domains": ["love", "career", "health", "spiritual"]
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "tone": "professional", "length": "medium" },
  "sections": {
    "love": "...",
    "career": "..."
  },
  "highlights": ["Top insight", "Another key takeaway"]
}
```

### `POST /v1/interpret/transits`
Produces written guidance for a date window of transit activity.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "window": {
    "from": "2025-01-01",
    "to": "2025-06-30"
  },
  "options": {
    "tone": "professional",
    "length": "short"
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "tone": "professional", "length": "short" },
  "month_summaries": {
    "2025-01": "January overview",
    "2025-02": "February overview"
  },
  "key_dates": [
    { "date": "2025-03-05", "headline": "Focus day" }
  ]
}
```

### `POST /v1/interpret/compatibility`
Narrative compatibility write-up for two charts.

**Request JSON**:
```jsonc
{
  "person_a": { /* ChartInput */ },
  "person_b": { /* ChartInput */ },
  "options": {
    "tone": "professional",
    "length": "short",
    "focus": ["romance", "communication"]
  }
}
```

**Response JSON**:
```jsonc
{
  "summary": "Overall compatibility synopsis",
  "strengths": ["Shared values"],
  "challenges": ["Communication styles differ"],
  "score": 78
}
```

## Compatibility analytics

### `POST /v1/compatibility/compute`
Calculates synastry aspects, aggregate score, and optional composite chart.

**Request JSON**:
```jsonc
{
  "person_a": { /* ChartInput */ },
  "person_b": { /* ChartInput */ },
  "options": {
    "aspects": {
      "types": ["conjunction", "opposition", "square", "trine", "sextile"],
      "orb_deg": 4.0
    },
    "include_composite": true
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "orb_deg": 4.0 },
  "synastry": [
    { "p1": "Sun", "p2": "Moon", "type": "trine", "orb": 2.1, "weight": 1.0 }
  ],
  "score": 78.5,
  "strengths": ["Sun trine Moon"],
  "challenges": ["Mars square Saturn"],
  "composite": [
    { "name": "Sun", "lon": 123.45, "sign": "Leo", "house": 10 }
  ]
}
```

## Remedies

### `POST /v1/remedies/compute`
Suggests chart-based remediation actions.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": {
    "allow_gemstones": true
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "allow_gemstones": true },
  "remedies": [
    {
      "planet": "Saturn",
      "issue": "Discipline lessons",
      "recommendation": "Saturday fasting",
      "gemstone": "Blue sapphire",
      "cautions": ["Consult a guru"]
    }
  ]
}
```

## Report rendering

### `POST /v1/reports`
Enqueues a background job to render a PDF report.

**Request JSON**:
```jsonc
{
  "product": "western_natal_pdf",
  "chart_input": { /* ChartInput */ },
  "partner_chart_input": { /* ChartInput */ },       // optional for compatibility reports
  "options": { "language": "en" },                 // product-specific overrides
  "branding": {
    "logo_url": "https://...",
    "primary_hex": "#4A3AFF"
  },
  "idempotency_key": "optional unique token"
}
```

**Response JSON**:
```jsonc
{
  "report_id": "rep_xxxxxxxxxxxxxxxx",
  "status": "queued",
  "download_url": null,
  "error": null
}
```

### `GET /v1/reports/{report_id}`
Fetches job status and, when complete, a relative download link.

**Response JSON**:
```jsonc
{
  "report_id": "rep_xxxxxxxxxxxxxxxx",
  "status": "done",                  // queued | processing | done | error
  "download_url": "/dev-assets/reports/rep_xxxxx.pdf",
  "error": null
}
```

## Full report viewmodels

### `POST /v1/natal/full`
Composes the full natal viewmodel used by the PDF renderer and app detail screens.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "name": "Optional display name",
  "place_label": "Optional location label",
  "include_interpretation": true,
  "include_remedies": true,
  "include_dasha": true
}
```

**Response JSON** (top-level shape):
```jsonc
{
  "header": {
    "name": "Asha",
    "system": "vedic",
    "zodiac": "sidereal",
    "house_system": "whole_sign",
    "ayanamsha": "lahiri",
    "time_known": true,
    "place_label": "Hyderabad"
  },
  "core_chart": {
    "angles": { "ascendant": 123.45, "mc": 210.11 },
    "houses": [ { "num": 1, "cusp_lon": 123.45 } ],
    "bodies": [ { "name": "Sun", "sign": "Leo", "house": 10, "lon": 123.45 } ],
    "aspects": [ { "p1": "Sun", "p2": "Moon", "type": "trine", "orb": 2.1, "applying": true } ],
    "warnings": []
  },
  "analysis": {
    "elements_balance": { "fire": 3 },
    "modalities_balance": { "fixed": 4 },
    "dignities": [ { "planet": "Sun", "status": "domicile" } ],
    "retrogrades": ["Saturn"],
    "chart_notes": ["Key note"],
    "strengths": ["Leadership"],
    "growth": ["Patience"]
  },
  "interpretation": {
    "summary": "High-level takeaway",
    "domains": { "career": "..." },
    "highlights": ["Important pattern"]
  },
  "vedic_extras": {
    "moon_nakshatra": { "name": "Ashlesha" },
    "current_dasha": { "maha": "Moon", "antar": "Mars", "start": "2023-01-01", "end": "2023-12-31" }
  },
  "remedies": [
    {
      "planet": "Saturn",
      "issue": "Discipline lessons",
      "recommendation": "Saturday fasting",
      "gemstone": "Blue sapphire",
      "cautions": ["Consult a guru"]
    }
  ],
  "assets": {
    "wheel_svg": "data:image/svg+xml;base64,...",
    "pdf_download_url": "/dev-assets/reports/rep_xxxxx.pdf"
  }
}
```

### `POST /v1/natal/full/report`
Same request body as `/v1/natal/full`, but queues PDF generation instead of returning the viewmodel immediately.

**Response JSON**:
```json
{ "report_id": "rep_xxxxxxxxxxxxxxxx", "status": "queued" }
```

### `POST /v1/yearly/full`
Builds the high-fidelity yearly forecast viewmodel (distinct from `/v1/forecasts/yearly`).

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": { /* arbitrary controls forwarded to the orchestrator */ },
  "name": "Optional",
  "place_label": "Optional",
  "include_interpretation": true,
  "include_dasha": true
}
```

**Response JSON**:
```jsonc
{
  "header": {
    "name": "Asha",
    "year": 2025,
    "system": "vedic",
    "zodiac": "sidereal",
    "ayanamsha": "lahiri",
    "house_system": "whole_sign",
    "time_known": true,
    "place_label": "Hyderabad"
  },
  "overview": {
    "key_themes": ["Growth"],
    "domains_summary": { "career": "Promotions likely" },
    "totals": { "supportive": 12 },
    "planet_activity": { "Saturn": 5 }
  },
  "months": {
    "Jan": {
      "summary": "January focus",
      "tone": "supportive",
      "top_events": [ { "title": "Sun trine Jupiter", "transit_body": "Sun", "natal_body": "Jupiter", "aspect": "trine", "orb": 1.2, "severity": "strong" } ],
      "calendar": [ { "date": "2025-01-05", "label": "Opportunity", "domains": ["career"] } ]
    }
  },
  "key_dates": [ { "date": "2025-03-10", "label": "Career peak", "domains": ["career"] } ],
  "vedic_extras": {
    "active_periods": [ { "level": 1, "lord": "Saturn", "start": "2024-08-01", "end": "2027-08-01" } ],
    "emphasis_notes": ["Focus on patience"]
  },
  "assets": {
    "timeline_svg": "data:image/svg+xml;base64,...",
    "calendar_svg": "data:image/svg+xml;base64,...",
    "pdf_download_url": "/dev-assets/reports/rep_xxxxx.pdf"
  }
}
```

### `POST /v1/yearly/full/report`
Queues PDF rendering for the yearly viewmodel. Response matches `/v1/natal/full/report`.

### `POST /v1/monthly/full`
Produces the detailed monthly viewmodel for premium surfaces.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": { /* orchestrator controls */ },
  "name": "Optional",
  "place_label": "Optional",
  "include_interpretation": true,
  "include_dasha": true
}
```

**Response JSON**:
```jsonc
{
  "header": {
    "name": "Asha",
    "year": 2025,
    "month": 9,
    "system": "vedic",
    "zodiac": "sidereal",
    "ayanamsha": "lahiri",
    "house_system": "whole_sign",
    "time_known": true,
    "place_label": "Hyderabad"
  },
  "overview": {
    "month_summary": "Key trends",
    "tone": "supportive",
    "key_themes": ["Relationships"],
    "totals": { "supportive": 8, "challenging": 2 },
    "planet_activity": { "Venus": 4 }
  },
  "weeks": {
    "W1": {
      "summary": "Week 1 focus",
      "tone": "supportive",
      "top_events": [ { "title": "Venus sextile Mars", "date": "2025-09-03", "transit_body": "Venus", "natal_body": "Mars", "aspect": "sextile", "orb": 0.8, "severity": "notable" } ],
      "calendar": [ { "date": "2025-09-04", "label": "Opportunity", "domains": ["love"] } ]
    }
  },
  "key_dates": [ { "date": "2025-09-18", "label": "Important call", "domains": ["career"] } ],
  "vedic_extras": {
    "active_periods": [ { "start": "2025-08-20", "end": "2025-09-15", "lord": "Mercury" } ],
    "emphasis_notes": ["Communication is highlighted"]
  },
  "assets": {
    "mini_calendar_svg": "data:image/svg+xml;base64,...",
    "pdf_download_url": "/dev-assets/reports/rep_xxxxx.pdf"
  }
}
```

### `POST /v1/monthly/full/report`
Queues PDF generation for the monthly viewmodel. Response mirrors `/v1/natal/full/report`.

## Panchang suite

### `POST /v1/panchang/compute`
Computes a full Panchang for a specific date/location.

**Request JSON**:
```jsonc
{
  "system": "vedic",
  "date": "2024-06-01",          // optional; defaults to today when omitted
  "place": {
    "lat": 17.385,
    "lon": 78.4867,
    "tz": "Asia/Kolkata",
    "query": "Hyderabad, India",
    "elevation": 500               // optional
  },
  "options": {
    "ayanamsha": "lahiri",
    "include_muhurta": true,
    "include_hora": false,
    "lang": "en",
    "script": "latin",
    "show_bilingual": false
  }
}
```

**Response JSON** (top-level keys):
```jsonc
{
  "header": { "date_local": "2024-06-01", "weekday": { "display_name": "Saturday", "aliases": { "en": "Saturday" } }, "tz": "Asia/Kolkata", "place_label": "Hyderabad", "system": "vedic", "ayanamsha": "lahiri", "locale": { "lang": "en", "script": "latin" } },
  "solar": { "sunrise": "2024-06-01T05:55:00+05:30", "sunset": "2024-06-01T19:07:00+05:30", "solar_noon": "2024-06-01T12:31:00+05:30", "day_length": "13:12:00" },
  "lunar": { "moonrise": "2024-06-01T03:12:00+05:30", "moonset": "2024-06-01T16:05:00+05:30", "lunar_day_no": 14, "paksha": "shukla" },
  "tithi": { "number": 14, "display_name": "Shukla Chaturdashi", "aliases": { "en": "Shukla Chaturdashi" }, "start_ts": "2024-05-31T22:40:00+05:30", "end_ts": "2024-06-01T21:58:00+05:30", "span_note": null },
  "nakshatra": { "display_name": "Magha", "aliases": { "en": "Magha" }, "start_ts": "2024-06-01T04:30:00+05:30", "end_ts": "2024-06-02T03:12:00+05:30", "pada": 2 },
  "yoga": { "display_name": "Siddhi", "aliases": { "en": "Siddhi" }, "start_ts": "2024-06-01T00:05:00+05:30", "end_ts": "2024-06-01T20:41:00+05:30" },
  "karana": { "display_name": "Vishti (Bhadra)", "aliases": { "en": "Vishti (Bhadra)" }, "start_ts": "2024-06-01T15:20:00+05:30", "end_ts": "2024-06-01T21:30:00+05:30" },
  "masa": { "amanta": { "display_name": "Vaishakha" }, "purnimanta": { "display_name": "Vaishakha" } },
  "windows": { "auspicious": [ { "kind": "abhijit", "start_ts": "2024-06-01T12:05:00+05:30", "end_ts": "2024-06-01T12:55:00+05:30" } ], "inauspicious": [ /* ... */ ] },
  "context": { "samvatsara": { "vikram": 2081, "shaka": 1946 }, "masa": { "amanta_name": "Vaishakha", "purnimanta_name": "Vaishakha" }, "ritu": { "drik": "Vasant", "vedic": "Vasant" }, "ayana": "uttarayan", "zodiac": { "sun_sign": "Taurus", "moon_sign": "Leo" } },
  "observances": [ { "title": "Ekadashi", "type": "vrat" } ],
  "notes": ["All times are local with standard refraction."],
  "assets": { "day_strip_svg": "data:image/svg+xml;base64,...", "pdf_download_url": null },
  "changes": { "tithi_periods": [ { "start_ts": "2024-05-31T22:40:00+05:30", "end_ts": "2024-06-01T21:58:00+05:30" } ] },
  "calendars_extended": null,
  "ritu_extended": null,
  "muhurtas_extra": null,
  "yoga_extended": null,
  "nivas_and_shool": null,
  "balam": null,
  "panchaka_and_lagna": null,
  "ritual_notes": [],
  "horas": null,
  "griha_pravesh": null
}
```

### `GET /v1/panchang/today`
Convenience wrapper around `/compute`. Query parameters (`lat`, `lon`, `tz`, `ayanamsha`, `include_muhurta`, `include_hora`, `lang`, `script`, `show_bilingual`, `place_label`) override defaults. Response matches `/compute`.

### `GET /v1/panchang/week`
Returns a week-long array of simplified daily Panchang summaries.

**Response JSON**:
```jsonc
{
  "meta": {
    "start_date": "2024-06-03",
    "end_date": "2024-06-09",
    "place_label": "Hyderabad",
    "tz": "Asia/Kolkata",
    "ayanamsha": "lahiri",
    "locale": { "lang": "en", "script": "latin" }
  },
  "days": [
    {
      "date_local": "2024-06-03",
      "weekday": { "display_name": "Monday", "aliases": { "en": "Monday" } },
      "solar": { "sunrise": "...", "sunset": "...", "day_length": "..." },
      "lunar": { "moonrise": "...", "moonset": "...", "lunar_day_no": 17, "paksha": "krishna" },
      "tithi": { "number": 18, "display_name": "Krishna Ashtami", "aliases": { "en": "Krishna Ashtami" } },
      "nakshatra": { "display_name": "Purva Phalguni" },
      "yoga": { "display_name": "Shubha" },
      "karana": { "display_name": "Bava" },
      "paksha": "krishna",
      "changes": { /* segment change windows */ }
    }
  ],
  "notes": ["Simplified view - muhurta details excluded for performance."]
}
```

### `GET /v1/panchang/month`
Monthly version of the weekly payload. Response schema matches `/week` with `meta` containing `year`, `month`, and `month_name`, and `days` covering the entire month.

### `POST /v1/panchang/report`
Generates an on-demand Panchang PDF.

**Request JSON**:
```jsonc
{
  "place": { "lat": 17.385, "lon": 78.4867, "tz": "Asia/Kolkata", "query": "Hyderabad" },
  "date": "2024-06-01",                // optional
  "options": { "ayanamsha": "lahiri", "include_muhurta": true },
  "branding": { "logo_url": "https://..." }
}
```

**Response JSON**: returns the rendered report payload (same structure as `/compute`) with embedded PDF metadata.

## Dasha forecasts

### `POST /v1/dashas/compute`
Computes Vimshottari dasha periods.

**Request JSON**:
```jsonc
{
  "chart_input": { /* ChartInput */ },
  "options": {
    "levels": 2,              // 1 = maha only, 2 = maha + antar
    "ayanamsha": "lahiri"
  }
}
```

**Response JSON**:
```jsonc
{
  "meta": { "system": "vedic", "ayanamsha": "lahiri", "levels": 2 },
  "periods": [
    {
      "level": 1,
      "lord": "Moon",
      "start": "2020-05-01",
      "end": "2030-05-01",
      "parent": null
    },
    {
      "level": 2,
      "lord": "Mars",
      "start": "2020-05-01",
      "end": "2021-02-01",
      "parent": "Moon"
    }
  ]
}
```

## Yearly and monthly orchestration PDFs

### `POST /v1/yearly/full/report`
### `POST /v1/monthly/full/report`
These endpoints share the same request payloads as their `/full` counterparts and respond with `{ "report_id": "...", "status": "queued" }`.

---

This document should be kept in sync with the FastAPI routers and Pydantic schema definitions whenever new endpoints or fields are introduced.
