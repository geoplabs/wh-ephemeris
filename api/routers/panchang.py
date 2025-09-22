"""Panchang API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Body, Query
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from zoneinfo import ZoneInfo

from ..schemas.panchang_viewmodel import PanchangViewModel
from ..services.orchestrators.panchang_full import build_viewmodel
from ..services.panchang_report import generate_panchang_report


router = APIRouter(prefix="/v1/panchang", tags=["panchang"])


class PanchangPlace(BaseModel):
    lat: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    lon: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    tz: Optional[str] = None
    query: Optional[str] = None
    elevation: Optional[float] = None


class PanchangOptions(BaseModel):
    ayanamsha: str = Field(default="lahiri")
    include_muhurta: bool = Field(default=True)
    include_hora: bool = Field(default=False)
    lang: str = Field(default="en")
    script: str = Field(default="latin")
    show_bilingual: bool = Field(default=False)


class PanchangRequest(BaseModel):
    system: str = "vedic"
    date: Optional[str] = None
    place: Optional[PanchangPlace] = None
    options: PanchangOptions = Field(default_factory=PanchangOptions)


@router.post(
    "/compute",
    response_model=PanchangViewModel,
    summary="Compute Panchang for a specific date and location",
)
def panchang_compute(
    req: PanchangRequest = Body(
        ...,
        examples={
            "hyderabad": {
                "summary": "Hyderabad explicit date",
                "description": "Compute Panchang for Hyderabad with Lahiri ayanamsha",
                "value": {
                    "system": "vedic",
                    "date": "2024-06-01",
                    "place": {
                        "lat": 17.385,
                        "lon": 78.4867,
                        "tz": "Asia/Kolkata",
                        "query": "Hyderabad, India",
                    },
                    "options": {
                        "ayanamsha": "lahiri",
                        "include_muhurta": True,
                        "include_hora": False,
                        "lang": "en",
                        "script": "latin",
                    },
                },
            },
            "defaults": {
                "summary": "No place provided",
                "description": "Uses configured defaults when place is omitted",
                "value": {
                    "system": "vedic",
                    "options": {"ayanamsha": "lahiri", "include_muhurta": True},
                },
            },
        },
    ),
):
    place_payload = req.place.model_dump(exclude_none=True) if req.place else None
    place = _clamp_place(place_payload)
    options = req.options.model_dump()
    return build_viewmodel(req.system, req.date, place, options)


@router.get(
    "/today",
    response_model=PanchangViewModel,
    summary="Convenience endpoint for today's Panchang",
    responses={
        200: {
            "description": "Computed Panchang for the requested location",
            "content": {
                "application/json": {
                    "examples": {
                        "mumbai_en": {
                            "summary": "Mumbai (English)",
                            "value": {
                                "header": {
                                    "date_local": "2024-06-01",
                                    "weekday": {
                                        "display_name": "Saturday",
                                        "aliases": {
                                            "en": "Saturday",
                                            "iast": "Śani-vāra",
                                            "deva": "शनिवार",
                                            "hi": "शनिवार",
                                        },
                                    },
                                    "tz": "Asia/Kolkata",
                                    "place_label": "Mumbai",
                                    "system": "vedic",
                                    "ayanamsha": "lahiri",
                                    "locale": {"lang": "en", "script": "latin"},
                                },
                                "solar": {
                                    "sunrise": "2024-06-01T05:55:00+05:30",
                                    "sunset": "2024-06-01T19:07:00+05:30",
                                    "solar_noon": "2024-06-01T12:31:00+05:30",
                                    "day_length": "13:12:00",
                                },
                                "lunar": {
                                    "moonrise": "2024-06-01T03:12:00+05:30",
                                    "moonset": "2024-06-01T16:05:00+05:30",
                                    "lunar_day_no": 14,
                                    "paksha": "shukla",
                                },
                                "tithi": {
                                    "number": 14,
                                    "display_name": "Shukla Chaturdashi",
                                    "aliases": {
                                        "en": "Shukla Chaturdashi",
                                        "iast": "Śukla Caturdaśī",
                                        "deva": "शुक्ल चतुर्दशी",
                                        "hi": "शुक्ल चतुर्दशी",
                                    },
                                    "start_ts": "2024-05-31T22:40:00+05:30",
                                    "end_ts": "2024-06-01T21:58:00+05:30",
                                    "span_note": None,
                                },
                                "nakshatra": {
                                    "number": 10,
                                    "display_name": "Magha",
                                    "aliases": {
                                        "en": "Magha",
                                        "iast": "Maghā",
                                        "deva": "मघा",
                                        "hi": "मघा",
                                    },
                                    "start_ts": "2024-06-01T04:30:00+05:30",
                                    "end_ts": "2024-06-02T03:12:00+05:30",
                                    "pada": 2,
                                },
                                "yoga": {
                                    "number": 16,
                                    "display_name": "Siddhi",
                                    "aliases": {
                                        "en": "Siddhi",
                                        "iast": "Siddhi",
                                        "deva": "सिद्धि",
                                        "hi": "सिद्धि",
                                    },
                                    "start_ts": "2024-06-01T00:05:00+05:30",
                                    "end_ts": "2024-06-01T20:41:00+05:30",
                                },
                                "karana": {
                                    "number": 56,
                                    "display_name": "Vishti (Bhadra)",
                                    "aliases": {
                                        "en": "Vishti (Bhadra)",
                                        "iast": "Viṣṭi (Bhadrā)",
                                        "deva": "विष्टि (भद्रा)",
                                        "hi": "विष्टि (भद्रा)",
                                    },
                                    "start_ts": "2024-06-01T15:20:00+05:30",
                                    "end_ts": "2024-06-01T21:30:00+05:30",
                                },
                                "masa": {
                                    "amanta": {
                                        "display_name": "Vaishakha",
                                        "aliases": {
                                            "en": "Vaishakha",
                                            "iast": "Vaiśākha",
                                            "deva": "वैशाख",
                                            "hi": "वैशाख",
                                        },
                                    },
                                    "purnimanta": {
                                        "display_name": "Vaishakha",
                                        "aliases": {
                                            "en": "Vaishakha",
                                            "iast": "Vaiśākha",
                                            "deva": "वैशाख",
                                            "hi": "वैशाख",
                                        },
                                    },
                                },
                                "windows": {
                                    "auspicious": [
                                        {
                                            "kind": "abhijit",
                                            "start_ts": "2024-06-01T12:18:00+05:30",
                                            "end_ts": "2024-06-01T12:42:00+05:30",
                                        }
                                    ],
                                    "inauspicious": [
                                        {
                                            "kind": "rahu_kalam",
                                            "start_ts": "2024-06-01T08:30:00+05:30",
                                            "end_ts": "2024-06-01T10:00:00+05:30",
                                        }
                                    ],
                                },
                                "context": {
                                    "samvatsara": {"vikram": 2081, "shaka": 1943},
                                    "masa": {
                                        "amanta_name": "Vaishakha",
                                        "purnimanta_name": "Vaishakha",
                                    },
                                    "ritu": {"drik": "Grishma", "vedic": "Grishma"},
                                    "ayana": "Uttarayana",
                                    "zodiac": {"sun_sign": "Taurus", "moon_sign": "Leo"},
                                },
                                "observances": [],
                                "notes": [
                                    "All times are local with standard refraction.",
                                    "Panchang day considered sunrise→next sunrise.",
                                ],
                                "assets": {"day_strip_svg": None, "pdf_download_url": None},
                                "calendars_extended": {
                                    "vikram_samvat": 2082,
                                    "shaka_samvat": 1947,
                                    "gujarati_samvat": 2081,
                                    "kali_ahargana": 1867090,
                                    "julian_day": 2460912.5,
                                    "modified_julian_day": 60912.0,
                                    "national_nirayana_date": {
                                        "year": 1947,
                                        "month": 6,
                                        "day": 3,
                                    },
                                },
                                "ritu_extended": {
                                    "drik_ritu": "Sharad",
                                    "vedic_ritu": "Sharad",
                                    "convention": "drik",
                                    "dinmana": "12:18:42",
                                    "ratrimana": "11:41:20",
                                },
                                "muhurtas_extra": {
                                    "auspicious_extra": [
                                        {
                                            "kind": "brahma",
                                            "start_ts": "2025-09-19T04:20:00+05:30",
                                            "end_ts": "2025-09-19T05:08:00+05:30",
                                        },
                                        {
                                            "kind": "pratah_sandhya",
                                            "start_ts": "2025-09-19T05:52:00+05:30",
                                            "end_ts": "2025-09-19T06:16:00+05:30",
                                        },
                                    ],
                                    "inauspicious_extra": [
                                        {
                                            "kind": "varjyam",
                                            "start_ts": "2025-09-19T14:40:00+05:30",
                                            "end_ts": "2025-09-19T16:10:00+05:30",
                                        },
                                        {
                                            "kind": "durmuhurtam",
                                            "start_ts": "2025-09-19T10:48:00+05:30",
                                            "end_ts": "2025-09-19T11:36:00+05:30",
                                        },
                                    ],
                                },
                                "yoga_extended": {
                                    "anandadi": "Shrivatsa",
                                    "tamil": "Siddha",
                                    "notes": [],
                                },
                                "nivas_and_shool": {
                                    "homahuti": "Venus",
                                    "agnivasa": "Prithvi",
                                    "shivasa": "Smashana",
                                    "disha_shool": "West",
                                    "chandra_vasa": "North",
                                    "rahu_vasa": "South",
                                },
                                "balam": {
                                    "chandrabalam_good": [
                                        "Cancer",
                                        "Scorpio",
                                        "Pisces",
                                    ],
                                    "tarabalam_good": [
                                        "Pushya",
                                        "Anuradha",
                                        "Uttara Bhadrapada",
                                    ],
                                    "valid_until_ts": "2025-09-20T06:00:00+05:30",
                                },
                                "panchaka_and_lagna": {
                                    "panchaka_rahita": [
                                        {
                                            "name": "Raja",
                                            "start_ts": "2025-09-19T06:10:00+05:30",
                                            "end_ts": "2025-09-19T08:00:00+05:30",
                                        }
                                    ],
                                    "udaya_lagna": [
                                        {
                                            "lagna": "Leo",
                                            "start_ts": "2025-09-19T06:05:00+05:30",
                                            "end_ts": "2025-09-19T07:05:00+05:30",
                                        }
                                    ],
                                },
                                "ritual_notes": [
                                    {
                                        "key": "usage",
                                        "text": "Panchang day spans local sunrise to next sunrise.",
                                    }
                                ],
                            },
                        },
                        "delhi_hi": {
                            "summary": "Delhi (Hindi/Devanagari)",
                            "value": {
                                "header": {
                                    "date_local": "2024-06-01",
                                    "weekday": {
                                        "display_name": "शनिवार",
                                        "aliases": {
                                            "en": "Saturday",
                                            "iast": "Śani-vāra",
                                            "deva": "शनिवार",
                                            "hi": "शनिवार",
                                        },
                                    },
                                    "tz": "Asia/Kolkata",
                                    "place_label": "नई दिल्ली",
                                    "system": "vedic",
                                    "ayanamsha": "lahiri",
                                    "locale": {"lang": "hi", "script": "deva"},
                                },
                                "solar": {
                                    "sunrise": "2024-06-01T05:25:00+05:30",
                                    "sunset": "2024-06-01T19:15:00+05:30",
                                    "solar_noon": "2024-06-01T12:20:00+05:30",
                                    "day_length": "13:50:00",
                                },
                                "lunar": {
                                    "moonrise": "2024-06-01T02:58:00+05:30",
                                    "moonset": "2024-06-01T16:22:00+05:30",
                                    "lunar_day_no": 14,
                                    "paksha": "shukla",
                                },
                                "tithi": {
                                    "number": 14,
                                    "display_name": "शुक्ल चतुर्दशी",
                                    "aliases": {
                                        "en": "Shukla Chaturdashi",
                                        "iast": "Śukla Caturdaśī",
                                        "deva": "शुक्ल चतुर्दशी",
                                        "hi": "शुक्ल चतुर्दशी",
                                    },
                                    "start_ts": "2024-05-31T22:32:00+05:30",
                                    "end_ts": "2024-06-01T21:43:00+05:30",
                                    "span_note": None,
                                },
                                "nakshatra": {
                                    "number": 10,
                                    "display_name": "मघा",
                                    "aliases": {
                                        "en": "Magha",
                                        "iast": "Maghā",
                                        "deva": "मघा",
                                        "hi": "मघा",
                                    },
                                    "start_ts": "2024-06-01T04:12:00+05:30",
                                    "end_ts": "2024-06-02T03:00:00+05:30",
                                    "pada": 1,
                                },
                                "yoga": {
                                    "number": 16,
                                    "display_name": "सिद्धि",
                                    "aliases": {
                                        "en": "Siddhi",
                                        "iast": "Siddhi",
                                        "deva": "सिद्धि",
                                        "hi": "सिद्धि",
                                    },
                                    "start_ts": "2024-06-01T00:10:00+05:30",
                                    "end_ts": "2024-06-01T20:50:00+05:30",
                                },
                                "karana": {
                                    "number": 56,
                                    "display_name": "विष्टि (भद्रा)",
                                    "aliases": {
                                        "en": "Vishti (Bhadra)",
                                        "iast": "Viṣṭi (Bhadrā)",
                                        "deva": "विष्टि (भद्रा)",
                                        "hi": "विष्टि (भद्रा)",
                                    },
                                    "start_ts": "2024-06-01T15:05:00+05:30",
                                    "end_ts": "2024-06-01T21:18:00+05:30",
                                },
                                "masa": {
                                    "amanta": {
                                        "display_name": "वैशाख",
                                        "aliases": {
                                            "en": "Vaishakha",
                                            "iast": "Vaiśākha",
                                            "deva": "वैशाख",
                                            "hi": "वैशाख",
                                        },
                                    },
                                    "purnimanta": {
                                        "display_name": "वैशाख",
                                        "aliases": {
                                            "en": "Vaishakha",
                                            "iast": "Vaiśākha",
                                            "deva": "वैशाख",
                                            "hi": "वैशाख",
                                        },
                                    },
                                },
                                "windows": {
                                    "auspicious": [
                                        {
                                            "kind": "abhijit",
                                            "start_ts": "2024-06-01T12:12:00+05:30",
                                            "end_ts": "2024-06-01T12:36:00+05:30",
                                        }
                                    ],
                                    "inauspicious": [
                                        {
                                            "kind": "rahu_kalam",
                                            "start_ts": "2024-06-01T07:30:00+05:30",
                                            "end_ts": "2024-06-01T09:00:00+05:30",
                                        }
                                    ],
                                },
                                "context": {
                                    "samvatsara": {"vikram": 2081, "shaka": 1943},
                                    "masa": {
                                        "amanta_name": "Vaishakha",
                                        "purnimanta_name": "Vaishakha",
                                    },
                                    "ritu": {"drik": "Grishma", "vedic": "Grishma"},
                                    "ayana": "Uttarayana",
                                    "zodiac": {"sun_sign": "Taurus", "moon_sign": "Leo"},
                                },
                                "observances": [],
                                "notes": [
                                    "All times are local with standard refraction.",
                                    "Panchang day considered sunrise→next sunrise.",
                                ],
                                "assets": {"day_strip_svg": None, "pdf_download_url": None},
                            },
                        },
                        "lat_lon_only": {
                            "summary": "Lat/Lon with inferred timezone",
                            "description": "Shows tz inference when tz is omitted",
                            "value": {
                                "header": {
                                    "date_local": "2024-06-01",
                                    "weekday": {
                                        "display_name": "Saturday",
                                        "aliases": {
                                            "en": "Saturday",
                                            "iast": "Śani-vāra",
                                            "deva": "शनिवार",
                                            "hi": "शनिवार",
                                        },
                                    },
                                    "tz": "Asia/Kolkata",
                                    "place_label": "19.0760, 72.8777",
                                    "system": "vedic",
                                    "ayanamsha": "lahiri",
                                    "locale": {"lang": "en", "script": "latin"},
                                    "meta": {
                                        "place_defaults_used": False,
                                        "tz_inferred": True,
                                        "default_reason": "missing_tz",
                                    },
                                }
                            },
                        },
                        "tz_only": {
                            "summary": "Timezone only (defaults for lat/lon)",
                            "description": "Defaults kick in when coordinates are missing",
                            "value": {
                                "header": {
                                    "date_local": "2024-06-01",
                                    "weekday": {
                                        "display_name": "Saturday",
                                        "aliases": {
                                            "en": "Saturday",
                                            "iast": "Śani-vāra",
                                            "deva": "शनिवार",
                                            "hi": "शनिवार",
                                        },
                                    },
                                    "tz": "Asia/Kolkata",
                                    "place_label": "New Delhi, India",
                                    "system": "vedic",
                                    "ayanamsha": "lahiri",
                                    "locale": {"lang": "en", "script": "latin"},
                                    "meta": {
                                        "place_defaults_used": True,
                                        "tz_inferred": False,
                                        "default_reason": "missing_latlon",
                                    },
                                }
                            },
                        },
                    }
                }
            },
        }
    },
)
def panchang_today(
    lat: Optional[float] = Query(
        None, ge=-90.0, le=90.0, example=19.076, description="Latitude"
    ),
    lon: Optional[float] = Query(
        None, ge=-180.0, le=180.0, example=72.8777, description="Longitude"
    ),
    tz: Optional[str] = Query(None, description="IANA timezone"),
    ayanamsha: str = Query("lahiri"),
    include_muhurta: bool = Query(True),
    include_hora: bool = Query(False),
    lang: str = Query("en"),
    script: str = Query("latin"),
    show_bilingual: bool = Query(False),
    place_label: Optional[str] = Query(None, description="Optional place label"),
):
    options = {
        "ayanamsha": ayanamsha,
        "include_muhurta": include_muhurta,
        "include_hora": include_hora,
        "lang": lang,
        "script": script,
        "show_bilingual": show_bilingual,
    }
    place_payload: Dict[str, Any] = {}
    if lat is not None:
        place_payload["lat"] = lat
    if lon is not None:
        place_payload["lon"] = lon
    if tz is not None:
        place_payload["tz"] = tz
    if place_label:
        place_payload["query"] = place_label
    place = _clamp_place(place_payload or None)
    return build_viewmodel("vedic", None, place, options)


class PanchangReportRequest(BaseModel):
    place: Dict[str, Any]
    date: Optional[str] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    branding: Optional[Dict[str, Any]] = None


@router.post("/report")
def panchang_report(req: PanchangReportRequest):
    place = _clamp_place(req.place)
    options = dict(req.options or {})
    vm = build_viewmodel("vedic", req.date, place, options)
    report = generate_panchang_report(vm)
    return report


def _clamp_place(place: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if place is None:
        return None

    clamped = dict(place)

    if "lat" in clamped and clamped["lat"] is not None:
        lat = float(clamped["lat"])
        clamped["lat"] = max(-89.9, min(89.9, lat))

    if "lon" in clamped and clamped["lon"] is not None:
        lon = float(clamped["lon"])
        clamped["lon"] = max(-180.0, min(180.0, lon))

    tz_name = clamped.get("tz")
    if tz_name:
        try:
            ZoneInfo(tz_name)
        except Exception as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid timezone: {tz_name}") from exc

    return clamped

