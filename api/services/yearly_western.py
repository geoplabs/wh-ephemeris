"""Western yearly forecast builder with advanced detection and scoring.

This module implements the extended yearly pipeline that powers the
``/v1/forecasts/yearly`` endpoint when western/tropical charts are
requested.  The design intentionally mirrors the product spec from the
business requirements so each step is easy to reason about and debug.

The implementation focuses on orchestrating existing ephemeris helpers
while layering new behaviour:

* Orb tables that honour per-body and per-angle overrides.
* Month-level caching for the detection grid so repeated requests are
  inexpensive.
* Enhanced scoring that respects applying/separating status, angle
  weighting, and campaign grouping for retrograde runs.
* A structured output including timeline, thematic clusters, fortunate
  windows, cautions, and raw debug payloads when requested.

Most calculations ultimately rely on :mod:`api.services.transits_engine`
for transit detection.  The western pipeline reshapes and scores those
results, enriches them with progressions/solar-return placeholders, and
produces canonical event identifiers for downstream caching.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, MutableMapping, Optional, Sequence, Tuple

from zoneinfo import ZoneInfo

try:  # Swiss ephemeris is optional in some test environments
    from . import houses as houses_svc
except ModuleNotFoundError:  # pragma: no cover - dependency missing fallback
    houses_svc = None  # type: ignore

try:
    from . import progressions as progressions_svc
except ModuleNotFoundError:  # pragma: no cover - dependency missing fallback
    progressions_svc = None  # type: ignore
from . import advanced_transits
from .transits_engine import (
    PLANET_EXPRESSIONS,
    _calculate_exact_hit_time,
    _transit_positions,
    compute_transits,
)
from . import aspects as aspects_svc
from .constants import SIGN_NAMES, sign_index_from_lon
from .houses import house_of

# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


WESTERN_SYSTEM = "western"
TROPICAL_ZODIAC = "tropical"
SUPPORTED_HOUSES = {"WholeSign", "Placidus"}


def is_western_enabled(chart_input: Dict[str, Any]) -> bool:
    """Return ``True`` when the western pipeline should be enabled.

    The API currently stores ``house_system`` in two possible locations
    (top-level ``chart_input`` or the nested ``options`` payload).  The
    gating helper therefore checks both to provide the most forgiving
    behaviour.
    """

    if chart_input.get("system") != WESTERN_SYSTEM:
        return False
    if chart_input.get("zodiac", TROPICAL_ZODIAC) != TROPICAL_ZODIAC:
        return False
    house_system = chart_input.get("house_system")
    if not house_system:
        house_system = (chart_input.get("options") or {}).get("house_system")
    if not house_system:
        # Default to Placidus for western charts when not provided.
        house_system = "Placidus"
    return house_system in SUPPORTED_HOUSES


# ---------------------------------------------------------------------------
# Configuration structures
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DetectionConfig:
    scan_step_hours: int = 6
    refine_exact: bool = True
    min_strength: float = 0.6
    window_merge_minutes: int = 20
    group_retrograde_campaigns: bool = False


@dataclass(slots=True)
class ScoringConfig:
    aspect_weight: Dict[str, float] = dataclasses.field(default_factory=lambda: {
        "conjunction": 1.0,
        "opposition": 0.9,
        "square": 0.85,
        "trine": 0.7,
        "sextile": 0.5,
        "quincunx": 0.4,
    })
    planet_weight: Dict[str, float] = dataclasses.field(default_factory=lambda: {
        "luminary": 1.0,
        "inner": 0.7,
        "outer": 1.2,
        "chiron": 0.6,
        "node": 0.8,
        "extras": 0.4,
    })
    angle_bonus: float = 0.3
    angle_weights: Dict[str, float] = dataclasses.field(
        default_factory=lambda: {"ASC": 1.0, "MC": 0.95, "DSC": 0.95, "IC": 0.9}
    )
    house_change_bonus: float = 0.2
    progressed_bonus: float = 0.4
    eclipse_bonus: float = 0.6
    midpoint_bonus: float = 0.25
    declination_bonus: float = 0.2
    applying_bonus: float = 0.08
    separating_penalty: float = -0.04


@dataclass(slots=True)
class PerformanceConfig:
    early_drop_below_score: float = 0.35
    month_cache_ttl_days: int = 7
    max_grid_points: int = 2000


@dataclass(slots=True)
class OutputConfig:
    sections: Sequence[str] = ("themes", "timeline", "windows", "cautions", "summary")
    max_events_per_month: int = 12
    raw_events: bool = True
    include_calendar_ics: bool = False
    include_pdf: bool = False
    debug: bool = False
    pdf: Dict[str, Any] = dataclasses.field(default_factory=dict)
    s3: Dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclass(slots=True)
class TimeConfig:
    timezone: Optional[str] = None
    tz_resolution: str = "strict"  # "strict" | "heuristic" | "fallback"


@dataclass(slots=True)
class IDConfig:
    canonical_fields: Sequence[str] = (
        "type",
        "p1",
        "p2",
        "aspect",
        "house",
        "deg",
        "ts_minute",
        "system",
        "house_system",
        "loc_key",
    )


@dataclass(slots=True)
class OrbTable:
    default: float
    body: Dict[str, float] = field(default_factory=dict)
    pair: Dict[str, float] = field(default_factory=dict)
    angle: Dict[str, float] = field(default_factory=dict)
    outer: Optional[float] = None

    def resolve(self, transit_body: str, natal_body: Optional[str], angle: Optional[str]) -> float:
        if natal_body and transit_body:
            key = f"{transit_body}|{natal_body}"
            if key in self.pair:
                return self.pair[key]
        if angle and angle in self.angle:
            return self.angle[angle]
        if transit_body in self.body:
            return self.body[transit_body]
        if natal_body in self.body:
            return self.body[natal_body]
        if self.outer is not None and _is_outer(transit_body):
            return self.outer
        return self.default


@dataclass(slots=True)
class YearlyWesternConfig:
    year: int
    timezone: str
    tz_resolution: str
    detection: DetectionConfig
    scoring: ScoringConfig
    performance: PerformanceConfig
    outputs: OutputConfig
    orb_table: OrbTable
    node_type: str
    applying_only: bool
    angle_targets: Sequence[str]
    filters: Dict[str, Any]
    midpoints: Dict[str, Any]
    declination_aspects: Dict[str, Any]
    progressions: Dict[str, bool]
    solar_return: Dict[str, Any]
    houses: Dict[str, Any]
    angles_extra: Sequence[str]
    options_raw: Dict[str, Any]
    versioning: Dict[str, str]
    seed: int
    canonical_ids: IDConfig


# ---------------------------------------------------------------------------
# Internal caches & constants
# ---------------------------------------------------------------------------


_MONTH_CACHE: MutableMapping[str, Dict[str, Any]] = {}


PLANET_CLASS = {
    "Sun": "luminary",
    "Moon": "luminary",
    "Mercury": "inner",
    "Venus": "inner",
    "Mars": "inner",
    "Jupiter": "outer",
    "Saturn": "outer",
    "Uranus": "outer",
    "Neptune": "outer",
    "Pluto": "outer",
    "TrueNode": "node",
    "MeanNode": "node",
    "Chiron": "chiron",
}

MALEFIC_BODIES = {"Mars", "Saturn", "Pluto"}
SUPPORTIVE_ASPECTS = {"trine", "sextile", "conjunction"}
TENSION_ASPECTS = {"square", "opposition"}

ANGLE_NAME_MAP = {
    "Ascendant": "ASC",
    "Midheaven": "MC",
    "Descendant": "DSC",
    "IC": "IC",
}

THEME_TEMPLATES = {
    "conjunction": [
        "{body} aligns closely with natal {target}, spotlighting {theme}.",
        "A fused {body}–{target} focus heightens {theme} for the year.",
    ],
    "trine": [
        "Supportive flow between {body} and {target} opens {theme} doors.",
        "Graceful {body} trine {target} eases growth around {theme}.",
    ],
    "sextile": [
        "{body} sextile {target} sparks collaborative {theme} opportunities.",
        "Fresh chances arise as {body} sextiles {target}, energising {theme}.",
    ],
    "square": [
        "Pressure from {body} square {target} demands work in {theme}.",
        "{body} squares {target}, challenging habits tied to {theme}.",
    ],
    "opposition": [
        "{body} opposing {target} calls for balance across {theme} matters.",
        "Polarised pulls from {body} and {target} test {theme} equilibrium.",
    ],
    "quincunx": [
        "Adjustments surface as {body} quincunx {target} reshapes {theme}.",
        "{body} quincunx {target} nudges creative pivots around {theme}.",
    ],
}

DEFAULT_THEME_TEMPLATE = "{body} {aspect} {target} keeps {theme} in focus."


# ---------------------------------------------------------------------------
# High level builder
# ---------------------------------------------------------------------------


def build_yearly_western_payload(
    chart_input: Dict[str, Any], options: Dict[str, Any]
) -> Dict[str, Any]:
    config = _build_config(chart_input, options)
    engine = _WesternYearlyEngine(chart_input, config)
    return engine.run()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------


def _build_config(chart_input: Dict[str, Any], options: Dict[str, Any]) -> YearlyWesternConfig:
    year = int(options["year"])
    options_raw = json.loads(json.dumps(options))  # deep copy for debug/meta
    detection_opts = options.get("detection") or {}
    scoring_opts = options.get("scoring") or {}
    performance_opts = options.get("performance") or {}
    outputs_opts = options.get("outputs") or {}
    time_opts = options.get("time") or {}
    ids_opts = options.get("ids") or {}
    aspects_opts = options.get("aspects") or {}
    progressions_opts = options.get("progressions") or {}
    solar_return_opts = options.get("solar_return") or {}
    filters_opts = options.get("filters") or {}
    midpoints_opts = options.get("midpoints") or {}
    declination_opts = options.get("declination_aspects") or {}
    houses_opts = options.get("houses") or {}
    angles_extra = options.get("angles_extra") or []
    versioning_opts = options.get("versioning") or {}

    detection = DetectionConfig(
        scan_step_hours=int(detection_opts.get("scan_step_hours", 6)),
        refine_exact=bool(detection_opts.get("refine_exact", True)),
        min_strength=float(detection_opts.get("min_strength", 0.6)),
        window_merge_minutes=int(detection_opts.get("window_merge_minutes", 20)),
        group_retrograde_campaigns=bool(detection_opts.get("group_retrograde_campaigns", False)),
    )

    scoring = ScoringConfig()
    scoring.aspect_weight.update(scoring_opts.get("aspect_weight", {}))
    scoring.planet_weight.update(scoring_opts.get("planet_weight", {}))
    scoring.angle_bonus = float(scoring_opts.get("angle_bonus", scoring.angle_bonus))
    scoring.house_change_bonus = float(
        scoring_opts.get("house_change_bonus", scoring.house_change_bonus)
    )
    scoring.progressed_bonus = float(
        scoring_opts.get("progressed_bonus", scoring.progressed_bonus)
    )
    scoring.eclipse_bonus = float(scoring_opts.get("eclipse_bonus", scoring.eclipse_bonus))
    scoring.midpoint_bonus = float(scoring_opts.get("midpoint_bonus", scoring.midpoint_bonus))
    scoring.declination_bonus = float(
        scoring_opts.get("declination_bonus", scoring.declination_bonus)
    )
    scoring.applying_bonus = float(scoring_opts.get("applying_bonus", scoring.applying_bonus))
    scoring.separating_penalty = float(
        scoring_opts.get("separating_penalty", scoring.separating_penalty)
    )
    scoring.angle_weights.update(scoring_opts.get("angle_weights", {}))

    performance = PerformanceConfig(
        early_drop_below_score=float(
            performance_opts.get("early_drop_below_score", 0.35)
        ),
        month_cache_ttl_days=int(performance_opts.get("month_cache_ttl_days", 7)),
        max_grid_points=int(performance_opts.get("max_grid_points", 2000)),
    )

    outputs = OutputConfig(
        sections=tuple(outputs_opts.get("sections", OutputConfig.sections)),
        max_events_per_month=int(outputs_opts.get("max_events_per_month", 12)),
        raw_events=bool(outputs_opts.get("raw_events", True)),
        include_calendar_ics=bool(outputs_opts.get("include_calendar_ics", False)),
        include_pdf=bool(outputs_opts.get("include_pdf", False)),
        debug=bool(outputs_opts.get("debug", False)),
        pdf=outputs_opts.get("pdf", {}),
        s3=outputs_opts.get("s3", {}),
    )

    timezone = (
        time_opts.get("timezone")
        or options.get("timezone")
        or chart_input["place"].get("tz")
    )
    tz_resolution = time_opts.get("tz_resolution", "strict")

    canonical_fields = ids_opts.get("canonical_fields") or (
        "type",
        "p1",
        "p2",
        "aspect",
        "house",
        "deg",
        "ts_minute",
        "system",
        "house_system",
        "loc_key",
    )

    orb_table = _compile_orb_table(aspects_opts)
    node_type = (options.get("transits") or {}).get("node_type", "True")
    applying_only = bool(aspects_opts.get("applying_only", False))
    angle_targets = tuple((aspects_opts.get("to_angles") or []))

    seed = _seed_for(chart_input, year)

    return YearlyWesternConfig(
        year=year,
        timezone=timezone,
        tz_resolution=tz_resolution,
        detection=detection,
        scoring=scoring,
        performance=performance,
        outputs=outputs,
        orb_table=orb_table,
        node_type=node_type,
        applying_only=applying_only,
        angle_targets=angle_targets,
        filters=filters_opts,
        midpoints=midpoints_opts,
        declination_aspects=declination_opts,
        progressions=progressions_opts,
        solar_return=solar_return_opts,
        houses=houses_opts,
        angles_extra=tuple(angles_extra),
        options_raw=options_raw,
        versioning=versioning_opts,
        seed=seed,
        canonical_ids=IDConfig(tuple(canonical_fields)),
    )


def _compile_orb_table(aspects_opts: Dict[str, Any]) -> OrbTable:
    orb = aspects_opts.get("orb") or {}
    default = float(orb.get("default", aspects_opts.get("orb_deg", 3.0)))
    body_overrides = {k: float(v) for k, v in orb.items() if k not in {"default", "outer"}}
    pair_overrides = {
        k: float(v)
        for k, v in (aspects_opts.get("pair_overrides") or {}).items()
    }
    angle_orbs = {k: float(v) for k, v in (aspects_opts.get("angle_orbs") or {}).items()}
    outer = orb.get("outer")
    outer_val = float(outer) if outer is not None else None
    return OrbTable(
        default=default,
        body=body_overrides,
        pair=pair_overrides,
        angle=angle_orbs,
        outer=outer_val,
    )


def _seed_for(chart_input: Dict[str, Any], year: int) -> int:
    place = chart_input.get("place", {})
    lat = place.get("lat")
    lon = place.get("lon")
    system = chart_input.get("system", "")
    house_system = chart_input.get("house_system") or (
        (chart_input.get("options") or {}).get("house_system")
    )
    payload = f"{chart_input.get('user_id','')}|{year}|{lat}|{lon}|{system}|{house_system}"
    digest = hashlib.blake2b(payload.encode("utf-8"), digest_size=4).digest()
    return int.from_bytes(digest, "big", signed=False)


# ---------------------------------------------------------------------------
# Engine implementation
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class _Event:
    stream: str
    type: str
    timestamp: datetime
    transit_body: str
    natal_body: Optional[str]
    aspect: str
    orb: float
    orb_limit: float
    score: float
    applying: bool
    tags: set
    info: Dict[str, Any]
    house: Optional[str] = None
    angle: Optional[str] = None
    house_change: bool = False
    canonical: Dict[str, Any] = dataclasses.field(default_factory=dict)
    event_id: Optional[str] = None

    def for_month_bucket(self) -> Dict[str, Any]:
        """Return a JSON-ready payload for legacy ``months`` output."""

        date_str = self.timestamp.astimezone(UTC).date().isoformat()
        note = self.info.get("note")
        if self.tags:
            tag_line = ", ".join(sorted(self.tags))
            note = f"{note} [{tag_line}]" if note else f"[{tag_line}]"
        payload = {
            "date": date_str,
            "transit_body": self.transit_body,
            "natal_body": self.natal_body or "—",
            "aspect": self.aspect,
            "orb": round(self.orb, 2),
            "score": round(self.score, 4),
            "note": note,
            "transit_sign": self.info.get("transit_sign"),
            "natal_sign": self.info.get("natal_sign"),
            "zodiac": self.info.get("zodiac"),
            "exact_hit_time_utc": self.info.get("exact_hit_time_utc"),
            "transit_motion": self.info.get("transit_motion"),
            "natal_point_type": self.info.get("natal_point_type"),
            "event_id": self.event_id,
        }
        if self.angle:
            payload["angle"] = self.angle
        if self.house:
            payload["house"] = self.house
        return payload

    def for_timeline(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "stream": self.stream,
            "type": self.type,
            "score": round(self.score, 4),
            "transit_body": self.transit_body,
            "natal_body": self.natal_body,
            "aspect": self.aspect,
            "tags": sorted(self.tags),
            "details": self.info,
            "angle": self.angle,
            "house": self.house,
        }


class _WesternYearlyEngine:
    def __init__(self, chart_input: Dict[str, Any], config: YearlyWesternConfig) -> None:
        self.chart_input = chart_input
        self.config = config
        self._meta_warnings: List[str] = []
        self._tzinfo: ZoneInfo = _resolve_timezone(
            config.timezone, config.tz_resolution, self._meta_warnings
        )
        self._retrograde_tracker: Dict[str, str] = {}
        self._retrograde_windows: Dict[str, Dict[str, Any]] = {}
        self._natal_cache: Optional[Dict[str, Dict[str, float]]] = None
        self._natal_decl_cache: Optional[Dict[str, float]] = None
        if self._tzinfo is None:
            # Fall back to UTC while tracking warning.
            self._meta_warnings.append("timezone_resolved_to_utc")
            self._tzinfo = ZoneInfo("UTC")

    # ------------------------------------------------------------------
    # Orchestration
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, Any]:
        transits = self._collect_transits()
        progressed = self._build_progressions()
        solar = self._build_solar_return()
        house_events = self._house_contours()

        events = transits + progressed + solar + house_events

        if self.config.detection.group_retrograde_campaigns:
            events = self._group_retrograde_campaigns(events)

        events = self._deduplicate(events)
        events.sort(key=lambda ev: (ev.timestamp, -ev.score, ev.event_id or ""))

        months, top_events = self._build_month_index(events)
        sections = self._synthesise_sections(events)

        payload: Dict[str, Any] = {
            "months": months,
            "top_events": top_events,
            "timeline": sections.get("timeline", []),
            "themes": sections.get("themes", []),
            "windows": sections.get("windows", []),
            "cautions": sections.get("cautions", []),
            "summary": sections.get("summary"),
        }

        meta = self._build_meta(len(events))
        payload["meta"] = meta

        if self.config.outputs.raw_events:
            payload["raw_events"] = [ev.for_timeline() for ev in events]

        if self.config.outputs.debug:
            payload["debug"] = self._debug_payload(events)

        return payload

    # ------------------------------------------------------------------
    # Data collection helpers
    # ------------------------------------------------------------------

    def _collect_transits(self) -> List[_Event]:
        year = self.config.year
        result: List[_Event] = []
        scan_step_hours = max(1, self.config.detection.scan_step_hours)
        node_name = "TrueNode" if self.config.node_type.lower() == "true" else "MeanNode"

        bodies = self._transit_bodies(node_name)
        natal_targets = None  # default behaviour from engine

        for month in range(1, 13):
            cache_key = _month_cache_key(
                self.chart_input,
                self.config,
                month,
                bodies,
                scan_step_hours,
            )
            cached = _MONTH_CACHE.get(cache_key)
            now = datetime.now(tz=UTC)
            if cached and cached["expires"] > now:
                month_events = cached["events"]
            else:
                month_events = self._compute_month(
                    month, scan_step_hours, bodies, natal_targets
                )
                month_events = self._augment_transit_events(
                    month_events, month, scan_step_hours, bodies
                )
                _MONTH_CACHE[cache_key] = {
                    "events": month_events,
                    "expires": now + timedelta(days=self.config.performance.month_cache_ttl_days),
                }

            for raw_event in month_events:
                evt = self._transform_transit(raw_event)
                if evt:
                    result.append(evt)

        return result

    def _compute_month(
        self,
        month: int,
        step_hours: int,
        bodies: Sequence[str],
        natal_targets: Optional[Sequence[str]],
    ) -> List[Dict[str, Any]]:
        start = datetime(self.config.year, month, 1)
        if month == 12:
            end = datetime(self.config.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = datetime(self.config.year, month + 1, 1) - timedelta(days=1)

        opts = {
            "from_date": start.date().isoformat(),
            "to_date": end.date().isoformat(),
            "step_days": max(1, step_hours // 24),
            "step_hours": step_hours,
            "transit_bodies": list(bodies),
            "aspects": self.config.options_raw.get("aspects"),
        }
        if natal_targets:
            opts["natal_targets"] = list(natal_targets)

        # Guard against enormous grids (performance fail-safe #18).
        total_hours = max(
            1,
            int(((end - start).total_seconds() / 3600) + step_hours),
        )
        grid_points = max(1, total_hours // step_hours) * max(1, len(bodies))
        if grid_points > self.config.performance.max_grid_points:
            self._meta_warnings.append("grid_points_capped")
            ratio = max(1, round(grid_points / self.config.performance.max_grid_points))
            step_hours = max(step_hours, step_hours * ratio)
            opts["step_hours"] = step_hours
            opts["step_days"] = max(1, step_hours // 24)

        events = compute_transits(self.chart_input, opts)
        return events

    def _augment_transit_events(
        self,
        month_events: List[Dict[str, Any]],
        month: int,
        step_hours: int,
        bodies: Sequence[str],
    ) -> List[Dict[str, Any]]:
        transits_cfg = self.config.options_raw.get("transits") or {}
        include_ingresses = bool(transits_cfg.get("include_ingresses", False))
        include_retrogrades = bool(transits_cfg.get("include_retrogrades", False))
        include_stations = bool(transits_cfg.get("include_stations", False))

        if not (include_ingresses or include_retrogrades or include_stations):
            return month_events

        start = datetime(self.config.year, month, 1, tzinfo=UTC)
        if month == 12:
            end = datetime(self.config.year + 1, 1, 1, tzinfo=UTC)
        else:
            end = datetime(self.config.year, month + 1, 1, tzinfo=UTC)

        ayan = None
        if self.chart_input.get("system") == "vedic":
            ayan = (self.chart_input.get("options") or {}).get("ayanamsha")

        timeline: List[Tuple[datetime, Dict[str, Dict[str, float]]]] = []
        dt = start
        step = timedelta(hours=step_hours)
        while dt <= end:
            positions = _transit_positions(dt, self.chart_input.get("system", "western"), ayan)
            timeline.append((dt, positions))
            dt += step
        if not timeline or timeline[-1][0] < end:
            positions = _transit_positions(end, self.chart_input.get("system", "western"), ayan)
            timeline.append((end, positions))

        for body in bodies:
            prev_sign: Optional[int] = None
            prev_motion: Optional[str] = None
            prev_dt: Optional[datetime] = None
            prev_pos: Optional[Dict[str, float]] = None
            for ts, pos_map in timeline:
                pos = pos_map.get(body)
                if not pos:
                    continue
                sign_idx = sign_index_from_lon(pos["lon"])
                motion = "retrograde" if pos.get("speed_lon", 0.0) < 0 else "direct"

                if (
                    include_ingresses
                    and prev_sign is not None
                    and sign_idx != prev_sign
                    and prev_pos is not None
                    and prev_dt is not None
                ):
                    boundary = sign_idx * 30.0
                    ingress_ts = _interpolate_longitude_crossing(
                        prev_pos["lon"], pos["lon"], prev_dt, ts, boundary
                    )
                    month_events.append(
                        {
                            "event_type": "ingress",
                            "transit_body": body,
                            "aspect": "ingress",
                            "orb": 0.0,
                            "date": ingress_ts.date().isoformat(),
                            "exact_hit_time_utc": ingress_ts.isoformat().replace("+00:00", "Z"),
                            "ingress_info": {
                                "from_sign": SIGN_NAMES[prev_sign],
                                "to_sign": SIGN_NAMES[sign_idx],
                            },
                            "note": f"{body} enters {SIGN_NAMES[sign_idx]}",
                        }
                    )

                if (
                    include_stations
                    and prev_motion is not None
                    and motion != prev_motion
                    and prev_pos is not None
                    and prev_dt is not None
                ):
                    station_ts = _interpolate_station(
                        prev_pos.get("speed_lon", 0.0), pos.get("speed_lon", 0.0), prev_dt, ts
                    )
                    month_events.append(
                        {
                            "event_type": "station",
                            "transit_body": body,
                            "aspect": "station",
                            "orb": 0.0,
                            "date": station_ts.date().isoformat(),
                            "exact_hit_time_utc": station_ts.isoformat().replace("+00:00", "Z"),
                            "station_phase": "station_retrograde"
                            if motion == "retrograde"
                            else "station_direct",
                            "note": f"{body} station {'retrograde' if motion == 'retrograde' else 'direct'}",
                        }
                    )

                if include_retrogrades:
                    state = self._retrograde_tracker.get(body, "direct")
                    if motion == "retrograde" and state != "retrograde":
                        self._retrograde_tracker[body] = "retrograde"
                        self._retrograde_windows[body] = {
                            "start": ts,
                            "phase": "retrograde",
                        }
                    elif motion == "direct" and state == "retrograde":
                        self._retrograde_tracker[body] = "direct"
                        window = self._retrograde_windows.get(body)
                        if window:
                            window["end"] = ts

                prev_sign = sign_idx
                prev_motion = motion
                prev_dt = ts
                prev_pos = pos

        month_events.extend(
            self._detect_midpoint_events(timeline, bodies, step)
        )
        month_events.extend(self._detect_declination_events(timeline, bodies))

        return month_events

    def _detect_midpoint_events(
        self,
        timeline: List[Tuple[datetime, Dict[str, Dict[str, float]]]],
        bodies: Sequence[str],
        step: timedelta,
    ) -> List[Dict[str, Any]]:
        cfg = self.config.midpoints or {}
        if not cfg.get("enabled"):
            return []
        pairs = cfg.get("pairs") or []
        if not pairs:
            return []
        natal_positions = self._natal_positions_cached()
        midpoint_orb = float(cfg.get("orb", 1.5))
        midpoints: Dict[str, float] = {}
        for raw_pair in pairs:
            try:
                left, right = raw_pair.split("/")
            except ValueError:
                continue
            left_pos = natal_positions.get(left)
            right_pos = natal_positions.get(right)
            if not left_pos or not right_pos:
                continue
            midpoints[raw_pair] = _midpoint_longitude(left_pos["lon"], right_pos["lon"])

        if not midpoints:
            return []

        events: List[Dict[str, Any]] = []
        last_emit: Dict[Tuple[str, str], datetime] = {}

        for body in bodies:
            state: Dict[str, Optional[float]] = {pair: None for pair in midpoints}
            prev_lon: Dict[str, Optional[float]] = {pair: None for pair in midpoints}
            prev_dt: Dict[str, Optional[datetime]] = {pair: None for pair in midpoints}
            for ts, positions in timeline:
                pos = positions.get(body)
                if not pos:
                    continue
                for pair, midpoint in midpoints.items():
                    diff = aspects_svc._angle_diff(pos["lon"], midpoint)
                    previous = state[pair]
                    if previous is None:
                        state[pair] = diff
                        prev_lon[pair] = pos["lon"]
                        prev_dt[pair] = ts
                        continue

                    crossed = previous <= 0 <= diff or previous >= 0 >= diff
                    within_orb = abs(diff) <= midpoint_orb
                    if crossed or within_orb:
                        start_dt = prev_dt[pair] or ts
                        start_lon = prev_lon[pair] if prev_lon[pair] is not None else pos["lon"]
                        hit_dt = _interpolate_longitude_crossing(
                            start_lon,
                            pos["lon"],
                            start_dt,
                            ts,
                            midpoint,
                        )
                        last_key = (body, pair)
                        last_time = last_emit.get(last_key)
                        if last_time and abs((hit_dt - last_time).total_seconds()) < step.total_seconds() / 2:
                            state[pair] = diff
                            prev_lon[pair] = pos["lon"]
                            prev_dt[pair] = ts
                            continue

                        event = {
                            "event_type": "midpoint",
                            "transit_body": body,
                            "natal_body": pair,
                            "aspect": "conjunction",
                            "orb": round(abs(diff), 2),
                            "exact_hit_time_utc": hit_dt.isoformat().replace("+00:00", "Z"),
                            "date": hit_dt.date().isoformat(),
                            "note": f"{body} activates {pair} midpoint",
                            "midpoint_of": pair,
                        }
                        events.append(event)
                        last_emit[last_key] = hit_dt
                    state[pair] = diff
                    prev_lon[pair] = pos["lon"]
                    prev_dt[pair] = ts

        return events

    def _detect_declination_events(
        self,
        timeline: List[Tuple[datetime, Dict[str, Dict[str, float]]]],
        bodies: Sequence[str],
    ) -> List[Dict[str, Any]]:
        cfg = self.config.declination_aspects or {}
        if not (cfg.get("parallels") or cfg.get("contraparallels")):
            return []

        natal_dec = self._natal_declinations()
        if not natal_dec:
            return []

        events: List[Dict[str, Any]] = []
        for ts, positions in timeline:
            for body in bodies:
                pos = positions.get(body)
                if not pos:
                    continue
                decl = pos.get("decl") or pos.get("declination") or pos.get("lat")
                if decl is None:
                    continue
                info = advanced_transits.calculate_declination_parallel(
                    decl,
                    natal_dec.get("Sun"),
                    natal_dec.get("Moon"),
                )
                if not info.get("has_declination_aspect"):
                    continue
                for aspect in info.get("aspects", []):
                    if aspect["type"] == "parallel" and not cfg.get("parallels", True):
                        continue
                    if aspect["type"] == "contra_parallel" and not cfg.get("contraparallels", True):
                        continue
                    event = {
                        "event_type": "declination_aspect",
                        "transit_body": body,
                        "natal_body": aspect.get("to"),
                        "aspect": aspect.get("type"),
                        "orb": round(aspect.get("orb", 0.0), 2),
                        "exact_hit_time_utc": ts.isoformat().replace("+00:00", "Z"),
                        "date": ts.date().isoformat(),
                        "note": f"{body} {aspect.get('type').replace('_', ' ')} natal {aspect.get('to')}",
                        "declination_bias": info.get("total_bias"),
                    }
                    events.append(event)
        return events

    def _transform_transit(self, raw_event: Dict[str, Any]) -> Optional[_Event]:
        # Filtering toggles
        transits_cfg = self.config.options_raw.get("transits") or {}
        if (
            self.config.filters.get("exclude_void_moon_windows")
            and raw_event.get("aspect") == "void_of_course"
        ):
            return None
        if (
            raw_event.get("event_type") == "lunar_phase"
            and transits_cfg.get("include_lunations", True) is False
        ):
            return None
        if raw_event.get("event_type") == "eclipse" and not transits_cfg.get(
            "include_eclipses", True
        ):
            return None
        if raw_event.get("event_type") == "station" and not transits_cfg.get(
            "include_stations", False
        ):
            return None
        if raw_event.get("event_type") == "ingress" and not transits_cfg.get(
            "include_ingresses", False
        ):
            return None

        # Determine timestamp (refine if available)
        ts = self._timestamp_for(raw_event)
        orb_limit = self.config.orb_table.resolve(
            raw_event.get("transit_body", ""),
            raw_event.get("natal_body"),
            _angle_name(raw_event.get("natal_body")),
        )
        orb = float(raw_event.get("orb", 0.0))
        orb_strength = max(0.0, 1.0 - min(orb / max(orb_limit, 1e-6), 1.0))
        if orb_strength < float(self.config.filters.get("min_orb_strength", 0.0)):
            return None

        applying = bool(raw_event.get("applying"))

        event = _Event(
            stream="transit",
            type=raw_event.get("event_type", "transit"),
            timestamp=ts,
            transit_body=raw_event.get("transit_body", ""),
            natal_body=raw_event.get("natal_body"),
            aspect=raw_event.get("aspect", ""),
            orb=orb,
            orb_limit=orb_limit,
            score=0.0,  # filled below
            applying=applying,
            tags=set(),
            info=dict(raw_event),
        )

        event.angle = _angle_name(event.natal_body)
        event.house_change = bool(raw_event.get("ingress_info"))

        if event.type == "eclipse":
            event.tags.add("eclipse")
        if raw_event.get("retrograde_bias", {}).get("has_bias"):
            event.tags.add("retrograde")
        if raw_event.get("transit_motion") == "retrograde":
            event.tags.add("retrograde")
        if raw_event.get("midpoint_of"):
            event.tags.add("midpoint")
        if raw_event.get("event_type") == "declination_aspect":
            event.tags.add("declination")
        if event.house_change:
            event.tags.add("house_change")
        if event.angle:
            event.tags.add("angle")
        if raw_event.get("event_type") == "station":
            event.tags.update({"retrograde", "station"})
            event.info.setdefault("station_phase", raw_event.get("station_phase"))
        if raw_event.get("event_type") == "lunar_phase":
            event.tags.add(raw_event.get("phase_name", "lunar_phase"))

        score = self._score_event(event)
        if score < self.config.performance.early_drop_below_score:
            return None

        event.score = score
        event.canonical = self._canonical_payload(event)
        event.event_id = _build_event_id(event.canonical)

        return event

    def _transit_bodies(self, node_name: str) -> Sequence[str]:
        transits_cfg = self.config.options_raw.get("transits") or {}
        bodies = list(transits_cfg.get("bodies") or [])
        bodies_extras = list(transits_cfg.get("bodies_extras") or [])
        if node_name and node_name not in bodies:
            bodies.append(node_name)
        if not bodies:
            bodies = [
                "Sun",
                "Moon",
                "Mercury",
                "Venus",
                "Mars",
                "Jupiter",
                "Saturn",
            ]
        return bodies + bodies_extras

    def _natal_positions_cached(self) -> Dict[str, Dict[str, float]]:
        if self._natal_cache is None:
            try:
                self._natal_cache = _natal_positions(self.chart_input)
            except ModuleNotFoundError:
                self._meta_warnings.append("ephem_unavailable")
                self._natal_cache = {}
        return self._natal_cache

    def _natal_declinations(self) -> Dict[str, float]:
        if self._natal_decl_cache is None:
            natal = self._natal_positions_cached()
            self._natal_decl_cache = {
                body: values.get("lat", 0.0)
                for body, values in natal.items()
                if values is not None
            }
        return self._natal_decl_cache

    def _timestamp_for(self, raw_event: Dict[str, Any]) -> datetime:
        exact = raw_event.get("exact_hit_time_utc")
        if exact:
            try:
                dt = datetime.fromisoformat(exact.replace("Z", "+00:00"))
                return dt.astimezone(self._tzinfo)
            except ValueError:
                pass
        if self.config.detection.refine_exact:
            refined = self._refine_exact_timestamp(raw_event)
            if refined is not None:
                return refined
        date_str = raw_event.get("date")
        if date_str:
            dt = datetime.fromisoformat(f"{date_str}T12:00:00+00:00")
        else:
            dt = datetime(self.config.year, 1, 1, tzinfo=UTC)
        return dt.astimezone(self._tzinfo)

    def _refine_exact_timestamp(self, raw_event: Dict[str, Any]) -> Optional[datetime]:
        transit_body = raw_event.get("transit_body")
        natal_body = raw_event.get("natal_body")
        aspect_name = raw_event.get("aspect")
        date_str = raw_event.get("date")
        if not (transit_body and aspect_name and date_str):
            return None
        canonical_aspect = aspects_svc.canonical_aspect(aspect_name)
        aspect_angle = aspects_svc.MAJOR.get(canonical_aspect)
        if aspect_angle is None:
            return None
        natal_positions = self._natal_positions_cached()
        if natal_body:
            natal = natal_positions.get(natal_body)
        else:
            natal = None
        if natal is None:
            return None
        approx = datetime.fromisoformat(f"{date_str}T12:00:00+00:00")
        ayan = None
        if self.chart_input.get("system") == "vedic":
            ayan = (self.chart_input.get("options") or {}).get("ayanamsha")
        positions = _transit_positions(approx, self.chart_input.get("system", "western"), ayan)
        transit = positions.get(transit_body)
        if not transit:
            return None
        exact_iso = _calculate_exact_hit_time(
            transit.get("lon", 0.0),
            transit.get("speed_lon", 0.0),
            natal.get("lon", 0.0),
            aspect_angle,
            approx,
        )
        if not exact_iso:
            return None
        try:
            dt = datetime.fromisoformat(exact_iso.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt.astimezone(self._tzinfo)

    # ------------------------------------------------------------------
    # Additional streams
    # ------------------------------------------------------------------

    def _build_progressions(self) -> List[_Event]:
        if not any(self.config.progressions.values()):
            return []
        if progressions_svc is None:
            self._meta_warnings.append("progressions_unavailable")
            return []

        progressed_positions = progressions_svc.progressed_positions(
            self.chart_input, self.config.year
        )
        try:
            natal_positions = _natal_positions(self.chart_input)
        except ModuleNotFoundError:
            self._meta_warnings.append("ephem_unavailable")
            return []
        events: List[_Event] = []

        aspects_cfg = self.config.options_raw.get("aspects") or {}
        aspect_types = aspects_cfg.get("types") or list(aspects_svc.MAJOR.keys())
        ts_base = datetime(self.config.year, 7, 1, tzinfo=UTC).astimezone(self._tzinfo)

        for prog_body, prog in progressed_positions.items():
            for natal_body, natal in natal_positions.items():
                for aspect_name in aspect_types:
                    canonical = aspects_svc.canonical_aspect(aspect_name)
                    aspect_angle = aspects_svc.MAJOR.get(canonical)
                    if aspect_angle is None:
                        continue
                    orb_limit = self.config.orb_table.resolve(
                        prog_body, natal_body, _angle_name(natal_body)
                    )
                    diff = aspects_svc._angle_diff(prog["lon"], natal["lon"])
                    orb = abs(diff - aspect_angle)
                    if orb > orb_limit:
                        continue
                    info = {
                        "note": f"Progressed {prog_body} {canonical} {natal_body}",
                        "progressed_lon": prog["lon"],
                        "natal_lon": natal["lon"],
                        "orb": round(orb, 2),
                    }
                    event = _Event(
                        stream="progressed",
                        type="progression",
                        timestamp=ts_base,
                        transit_body=prog_body,
                        natal_body=natal_body,
                        aspect=canonical,
                        orb=round(orb, 2),
                        orb_limit=orb_limit,
                        score=0.0,
                        applying=prog.get("speed_lon", 0.0) >= natal.get("speed_lon", 0.0),
                        tags={"progressed"},
                        info=info,
                    )
                    event.score = self._score_event(event)
                    if event.score < self.config.performance.early_drop_below_score:
                        continue
                    event.canonical = self._canonical_payload(event)
                    event.event_id = _build_event_id(event.canonical)
                    events.append(event)

        if self.config.progressions.get("solar_arc"):
            events.extend(self._solar_arc_events(natal_positions, progressed_positions))

        return events

    def _solar_arc_events(
        self,
        natal_positions: Dict[str, Dict[str, float]],
        progressed_positions: Dict[str, Dict[str, float]],
    ) -> List[_Event]:
        if progressions_svc is None:
            return []
        sun_prog = progressed_positions.get("Sun")
        sun_natal = natal_positions.get("Sun")
        if not sun_prog or not sun_natal:
            return []
        arc = (sun_prog["lon"] - sun_natal["lon"]) % 360
        events: List[_Event] = []
        ts = datetime(self.config.year, 8, 1, tzinfo=UTC).astimezone(self._tzinfo)

        for body, natal in natal_positions.items():
            if body == "Sun":
                continue
            arc_lon = (natal["lon"] + arc) % 360
            info = {
                "note": f"Solar arc progression for {body}",
                "solar_arc": arc,
                "arc_lon": arc_lon,
            }
            event = _Event(
                stream="progressed",
                type="solar_arc",
                timestamp=ts,
                transit_body=body,
                natal_body=body,
                aspect="solar_arc",
                orb=0.0,
                orb_limit=1.0,
                score=0.0,
                applying=True,
                tags={"progressed", "solar_arc"},
                info=info,
            )
            event.score = self._score_event(event)
            if event.score < self.config.performance.early_drop_below_score:
                continue
            event.canonical = self._canonical_payload(event)
            event.event_id = _build_event_id(event.canonical)
            events.append(event)
        return events

    def _build_solar_return(self) -> List[_Event]:
        if not self.config.solar_return.get("enabled"):
            return []
        loc = self.config.solar_return.get("location") or self.chart_input.get("place", {})
        natal_positions = self._natal_positions_cached()
        sun_natal = natal_positions.get("Sun")
        if not sun_natal:
            return []

        sr_dt = self._solve_solar_return_time(sun_natal["lon"], loc)
        if sr_dt is None:
            return []

        location_tz = _resolve_timezone(
            loc.get("tz"), self.config.tz_resolution, self._meta_warnings
        ) or self._tzinfo
        sr_local = sr_dt.astimezone(location_tz)
        sr_display = sr_local.astimezone(self._tzinfo)

        info = {
            "note": "Solar return snapshot",
            "location": loc,
            "exact_local": sr_local.isoformat(),
        }

        events: List[_Event] = []
        main_event = _Event(
            stream="solar_return",
            type="solar_return",
            timestamp=sr_display,
            transit_body="Sun",
            natal_body="Sun",
            aspect="solar_return",
            orb=0.0,
            orb_limit=1.0,
            score=0.85,
            applying=True,
            tags={"solar_return"},
            info=info,
        )
        main_event.score = self._score_event(main_event)
        main_event.canonical = self._canonical_payload(main_event)
        main_event.event_id = _build_event_id(main_event.canonical)
        events.append(main_event)

        aspects_cfg = self.config.options_raw.get("aspects") or {}
        aspect_types = aspects_cfg.get("types") or list(aspects_svc.MAJOR.keys())
        ayan = None
        if self.chart_input.get("system") == "vedic":
            ayan = (self.chart_input.get("options") or {}).get("ayanamsha")
        sr_positions = _transit_positions(
            sr_dt.astimezone(UTC), self.chart_input.get("system", "western"), ayan
        )

        for body, pos in sr_positions.items():
            for natal_body, natal in natal_positions.items():
                for aspect_name in aspect_types:
                    canonical = aspects_svc.canonical_aspect(aspect_name)
                    aspect_angle = aspects_svc.MAJOR.get(canonical)
                    if aspect_angle is None:
                        continue
                    orb_limit = self.config.orb_table.resolve(
                        body, natal_body, _angle_name(natal_body)
                    )
                    diff = aspects_svc._angle_diff(pos["lon"], natal["lon"])
                    orb = abs(diff - aspect_angle)
                    if orb > orb_limit:
                        continue
                    ev = _Event(
                        stream="solar_return",
                        type="solar_return_aspect",
                        timestamp=sr_display,
                        transit_body=body,
                        natal_body=natal_body,
                        aspect=canonical,
                        orb=round(orb, 2),
                        orb_limit=orb_limit,
                        score=0.0,
                        applying=pos.get("speed_lon", 0.0) >= natal.get("speed_lon", 0.0),
                        tags={"solar_return"},
                        info={
                            "note": f"Solar return {body} {canonical} {natal_body}",
                            "orb": round(orb, 2),
                        },
                    )
                    ev.score = self._score_event(ev)
                    if ev.score < self.config.performance.early_drop_below_score:
                        continue
                    ev.canonical = self._canonical_payload(ev)
                    ev.event_id = _build_event_id(ev.canonical)
                    events.append(ev)

        return events

    def _solve_solar_return_time(
        self, target_lon: float, location: Dict[str, Any]
    ) -> Optional[datetime]:
        birth_date = self.chart_input.get("date")
        if not birth_date:
            return None
        try:
            year = self.config.year
            month = int(birth_date.split("-")[1])
            day = int(birth_date.split("-")[2])
        except (ValueError, IndexError):
            return None
        tz_name = (
            location.get("tz")
            or self.config.timezone
            or self.chart_input.get("place", {}).get("tz", "UTC")
        )
        tz = _resolve_timezone(tz_name, self.config.tz_resolution) or ZoneInfo("UTC")
        start_local = datetime(year, month, min(day, 28), 0, tzinfo=tz)
        start = start_local.astimezone(UTC)
        end = start + timedelta(days=3)
        system = self.chart_input.get("system", "western")
        ayan = None
        if system == "vedic":
            ayan = (self.chart_input.get("options") or {}).get("ayanamsha")

        def diff_at(dt: datetime) -> Optional[float]:
            sun_pos = _transit_positions(dt, system, ayan).get("Sun")
            if not sun_pos:
                return None
            return _signed_angle_diff(sun_pos["lon"], target_lon)

        step = timedelta(hours=6)
        prev_dt = start
        prev_diff = diff_at(prev_dt)
        bracket: Optional[Tuple[datetime, datetime]] = None
        dt = start + step
        while dt <= end:
            cur_diff = diff_at(dt)
            if cur_diff is None:
                dt += step
                continue
            if prev_diff is not None and prev_diff * cur_diff <= 0:
                bracket = (prev_dt, dt)
                break
            prev_dt = dt
            prev_diff = cur_diff
            dt += step

        if not bracket:
            bracket = (start, start + timedelta(hours=12))
            prev_diff = diff_at(bracket[0])
            cur_diff = diff_at(bracket[1])
        else:
            cur_diff = diff_at(bracket[1])

        left, right = bracket
        diff_left = prev_diff if prev_diff is not None else diff_at(left) or 0.0
        diff_right = cur_diff if cur_diff is not None else diff_at(right) or 0.0

        for _ in range(12):
            mid = left + (right - left) / 2
            diff_mid_opt = diff_at(mid)
            if diff_mid_opt is None:
                break
            diff_mid = diff_mid_opt
            if abs(diff_mid) < 1e-3 or (right - left).total_seconds() <= 60:
                return mid
            if diff_left * diff_mid <= 0:
                right = mid
                diff_right = diff_mid
            else:
                left = mid
                diff_left = diff_mid

        return left + (right - left) / 2

    def _house_contours(self) -> List[_Event]:
        if not self.config.houses.get("track_entries") and not self.config.houses.get("track_exits"):
            return []
        if not self.chart_input.get("time_known", True):
            return []
        if houses_svc is None:
            self._meta_warnings.append("houses_unavailable")
            return []

        house_system = (
            self.chart_input.get("house_system")
            or (self.chart_input.get("options") or {}).get("house_system")
            or "Placidus"
        )
        if house_system not in SUPPORTED_HOUSES:
            return []

        try:
            jd = _jd_for_birth(self.chart_input)
        except ModuleNotFoundError:
            self._meta_warnings.append("ephem_unavailable")
            return []
        hs_key = house_system.lower().replace("-", "_")
        if hs_key == "wholesign":
            hs_key = "whole_sign"
        houses_data = houses_svc.houses(
            jd,
            self.chart_input["place"]["lat"],
            self.chart_input["place"]["lon"],
            hs_key,
        )
        cusp_values = list(houses_data.get("cusps", []))
        events: List[_Event] = []

        # Build simple entry snapshot for metadata purposes.
        info = {
            "note": "House blueprint established",
            "cusps": houses_data,
        }
        ts = datetime(self.config.year, 1, 1, tzinfo=UTC).astimezone(self._tzinfo)
        blueprint = _Event(
            stream="houses",
            type="house_blueprint",
            timestamp=ts,
            transit_body="Ascendant",
            natal_body=None,
            aspect="house_setup",
            orb=0.0,
            orb_limit=1.0,
            score=self.config.scoring.house_change_bonus,
            applying=True,
            tags={"houses"},
            info=info,
        )
        blueprint.canonical = self._canonical_payload(blueprint)
        blueprint.event_id = _build_event_id(blueprint.canonical)
        events.append(blueprint)

        track_entries = bool(self.config.houses.get("track_entries"))
        track_exits = bool(self.config.houses.get("track_exits"))
        if not (track_entries or track_exits):
            return events

        step_hours = max(1, self.config.detection.scan_step_hours)
        ayan = None
        if self.chart_input.get("system") == "vedic":
            ayan = (self.chart_input.get("options") or {}).get("ayanamsha")

        bodies = self._transit_bodies("TrueNode")
        start = datetime(self.config.year, 1, 1, tzinfo=UTC)
        end = datetime(self.config.year + 1, 1, 1, tzinfo=UTC)
        step = timedelta(hours=step_hours)

        for body in bodies:
            prev_house: Optional[int] = None
            prev_dt: Optional[datetime] = None
            dt = start
            while dt <= end:
                positions = _transit_positions(dt, self.chart_input.get("system", "western"), ayan)
                pos = positions.get(body)
                if not pos:
                    dt += step
                    continue
                house_num = house_of(pos["lon"], cusp_values)
                if prev_house is None:
                    prev_house = house_num
                    prev_dt = dt
                    dt += step
                    continue
                if house_num != prev_house and prev_dt is not None:
                    change_dt = _refine_house_crossing(
                        prev_dt,
                        dt,
                        body,
                        house_num,
                        cusp_values,
                        self.chart_input.get("system", "western"),
                        ayan,
                    ).astimezone(self._tzinfo)
                    info = {
                        "note": f"{body} moves from house {prev_house} to {house_num}",
                        "from_house": prev_house,
                        "to_house": house_num,
                    }
                    event = _Event(
                        stream="houses",
                        type="house_change",
                        timestamp=change_dt,
                        transit_body=body,
                        natal_body=None,
                        aspect="house_change",
                        orb=0.0,
                        orb_limit=1.0,
                        score=self.config.scoring.house_change_bonus,
                        applying=True,
                        tags={"houses", "house_change"},
                        info=info,
                        house=str(house_num),
                        house_change=True,
                    )
                    event.score = self._score_event(event)
                    if event.score >= self.config.performance.early_drop_below_score:
                        event.canonical = self._canonical_payload(event)
                        event.event_id = _build_event_id(event.canonical)
                        events.append(event)
                    prev_house = house_num
                    prev_dt = dt
                else:
                    prev_house = house_num
                    prev_dt = dt
                dt += step

        return events

    # ------------------------------------------------------------------
    # Scoring & canonical payloads
    # ------------------------------------------------------------------

    def _score_event(self, event: _Event) -> float:
        scoring = self.config.scoring
        aspect_weight = scoring.aspect_weight.get(event.aspect, 0.5)
        planet_class = PLANET_CLASS.get(event.transit_body, "extras")
        planet_weight = scoring.planet_weight.get(planet_class, 0.4)

        orb_factor = max(0.0, 1.0 - min(event.orb / max(event.orb_limit, 1e-6), 1.0))
        base = aspect_weight * planet_weight * orb_factor
        score = base
        breakdown = {"base": round(base, 4), "orb_factor": round(orb_factor, 4)}

        if event.angle and event.angle in self.config.angle_targets:
            score += scoring.angle_bonus
            score *= scoring.angle_weights.get(event.angle, 1.0)
            breakdown["angle_bonus"] = scoring.angle_bonus
            breakdown["angle_weight"] = round(
                scoring.angle_weights.get(event.angle, 1.0), 4
            )

        if event.house_change:
            score += scoring.house_change_bonus
            breakdown["house_change_bonus"] = scoring.house_change_bonus

        if "progressed" in event.tags:
            score += scoring.progressed_bonus
            breakdown["progressed_bonus"] = scoring.progressed_bonus

        if "eclipse" in event.tags:
            score += scoring.eclipse_bonus
            breakdown["eclipse_bonus"] = scoring.eclipse_bonus

        if "midpoint" in event.tags:
            score += scoring.midpoint_bonus
            breakdown["midpoint_bonus"] = scoring.midpoint_bonus

        if "declination" in event.tags:
            score += scoring.declination_bonus
            breakdown["declination_bonus"] = scoring.declination_bonus

        if "solar_return" in event.tags:
            score = max(score, 0.75)
            breakdown["solar_return_floor"] = 0.75

        if "houses" in event.tags:
            score = max(score, max(0.6, scoring.house_change_bonus))
            breakdown["house_floor"] = max(0.6, scoring.house_change_bonus)

        if event.applying:
            score += scoring.applying_bonus
            breakdown["applying_bonus"] = scoring.applying_bonus
        elif not self.config.applying_only:
            score += scoring.separating_penalty
            breakdown["separating_penalty"] = scoring.separating_penalty

        score = max(0.0, min(1.0, score))
        if score < self.config.detection.min_strength:
            return 0.0
        event.info.setdefault("score_breakdown", breakdown)
        return score

    def _canonical_payload(self, event: _Event) -> Dict[str, Any]:
        place = self.chart_input.get("place", {})
        loc_key = f"{round(place.get('lat', 0.0), 3)},{round(place.get('lon', 0.0), 3)}"
        ts_minute = event.timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M")
        payload = {
            "type": event.type,
            "p1": event.transit_body,
            "p2": event.natal_body or "",
            "aspect": event.aspect,
            "house": event.house or "",
            "deg": round(event.orb_limit - event.orb, 2),
            "ts_minute": ts_minute,
            "system": self.chart_input.get("system"),
            "house_system": self.chart_input.get("house_system")
            or (self.chart_input.get("options") or {}).get("house_system"),
            "loc_key": loc_key,
        }
        ordered = {
            key: payload.get(key, "")
            for key in self.config.canonical_ids.canonical_fields
        }
        return ordered

    # ------------------------------------------------------------------
    # Post processing helpers
    # ------------------------------------------------------------------

    def _group_retrograde_campaigns(self, events: List[_Event]) -> List[_Event]:
        buckets: Dict[Tuple[str, str, str], List[_Event]] = defaultdict(list)
        for ev in events:
            if ev.stream != "transit":
                buckets[(ev.transit_body, ev.natal_body or "", ev.aspect)].append(ev)
                continue
            if "retrograde" not in ev.tags:
                buckets[(ev.transit_body, ev.natal_body or "", ev.aspect)].append(ev)
                continue
            buckets[(ev.transit_body, ev.natal_body or "", ev.aspect)].append(ev)

        combined: List[_Event] = []
        for key, bucket in buckets.items():
            retro_events = [ev for ev in bucket if "retrograde" in ev.tags]
            if len(retro_events) < 3:
                combined.extend(bucket)
                continue

            bucket.sort(key=lambda ev: ev.timestamp)
            phases = [
                "approach",
                "exact-1",
                "retro-phase",
                "exact-2",
                "direct-phase",
                "exact-3",
                "decay",
            ]
            for idx, ev in enumerate(bucket):
                phase = phases[min(idx, len(phases) - 1)]
                ev.info.setdefault("campaign_phase", phase)

            start = bucket[0].timestamp
            end = bucket[-1].timestamp
            window = self._retrograde_windows.get(key[0], {})
            campaign_info = {
                "start": window.get("start", start).isoformat(),
                "end": window.get("end", end).isoformat(),
            }
            score = min(1.0, max(ev.score for ev in retro_events) * 1.15)
            info = {
                "note": "Retrograde campaign",
                "phases": [ev.info.get("campaign_phase") for ev in bucket],
                "children": [ev.for_timeline() for ev in bucket],
                "campaign": campaign_info,
            }
            event = _Event(
                stream="transit",
                type="retrograde_campaign",
                timestamp=start,
                transit_body=key[0],
                natal_body=key[1] or None,
                aspect=key[2],
                orb=0.0,
                orb_limit=1.0,
                score=score,
                applying=True,
                tags={"retrograde", "campaign"},
                info=info,
            )
            event.canonical = self._canonical_payload(event)
            event.event_id = _build_event_id(event.canonical)
            combined.append(event)

        return combined

    def _deduplicate(self, events: List[_Event]) -> List[_Event]:
        deduped: List[_Event] = []
        tolerance = timedelta(hours=48)

        for ev in events:
            placed = False
            for existing in deduped:
                if not _events_compatible(existing, ev, tolerance):
                    continue
                placed = True
                if ev.score > existing.score:
                    existing.timestamp = ev.timestamp
                    existing.score = ev.score
                    existing.info = {**existing.info, **ev.info}
                    existing.event_id = ev.event_id
                    existing.canonical = ev.canonical
                existing.tags |= ev.tags
                existing.info.setdefault("sources", []).append(ev.for_timeline())
                break
            if not placed:
                deduped.append(ev)

        return deduped

    def _build_month_index(self, events: List[_Event]) -> Tuple[Dict[str, List[Dict[str, Any]]], List[Dict[str, Any]]]:
        months: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        transits_only = [ev for ev in events if ev.stream == "transit"]
        for ev in transits_only:
            bucket_key = ev.timestamp.strftime("%Y-%m")
            months[bucket_key].append(ev.for_month_bucket())

        limit = self.config.outputs.max_events_per_month
        for key, evs in list(months.items()):
            # Select the highest scoring events for the month, then restore
            # chronological ordering for presentation.  The previous
            # implementation truncated the list while it was sorted by date,
            # which meant only the earliest events survived even if later
            # transits carried higher scores.  This manifested as monthly
            # payloads dominated by events from the first couple of days.
            ranked = sorted(evs, key=lambda item: item.get("score", 0), reverse=True)
            if limit and len(ranked) > limit:
                ranked = ranked[:limit]
            ranked.sort(key=lambda item: (item.get("date"), -item.get("score", 0)))
            months[key] = ranked

        top_events = sorted(transits_only, key=lambda e: -e.score)[:20]
        return dict(months), [ev.for_month_bucket() for ev in top_events]

    def _synthesise_sections(self, events: List[_Event]) -> Dict[str, Any]:
        sections: Dict[str, Any] = {}

        if "timeline" in self.config.outputs.sections:
            sections["timeline"] = [ev.for_timeline() for ev in events]

        if "themes" in self.config.outputs.sections:
            grouped: Dict[Tuple[str, str, str], List[_Event]] = defaultdict(list)
            for ev in events:
                target = ev.natal_body or ev.angle or ev.house or ""
                grouped[(ev.transit_body, ev.aspect, target)].append(ev)

            theme_entries: List[Dict[str, Any]] = []
            for (body, aspect_name, target), bucket in grouped.items():
                if not bucket:
                    continue
                avg_score = sum(ev.score for ev in bucket) / max(len(bucket), 1)
                aspect_key = aspect_name or "conjunction"
                templates = THEME_TEMPLATES.get(aspect_key, [DEFAULT_THEME_TEMPLATE])
                seed_material = f"{body}|{aspect_key}|{target}|{self.config.seed}"
                rng_seed = int(
                    hashlib.blake2b(seed_material.encode("utf-8"), digest_size=4).hexdigest(),
                    16,
                )
                rng = random.Random(rng_seed)
                template = rng.choice(templates)
                target_theme = _theme_keyword(target)
                summary = template.format(
                    body=_pretty_name(body),
                    target=_pretty_name(target or "natal focus"),
                    theme=target_theme,
                    aspect=aspect_key.replace("_", " "),
                )
                theme_entries.append(
                    {
                        "key": f"{body}:{aspect_key}:{target}",
                        "score": round(avg_score, 4),
                        "summary": summary,
                    }
                )

            sections["themes"] = sorted(
                theme_entries, key=lambda item: (-item["score"], item["key"])
            )

        if "windows" in self.config.outputs.sections:
            sections["windows"] = _build_windows(events, threshold=0.65)

        if "cautions" in self.config.outputs.sections:
            sections["cautions"] = _build_cautions(events)

        if "summary" in self.config.outputs.sections:
            sections["summary"] = _build_summary(events)

        return sections

    def _build_meta(self, total_events: int) -> Dict[str, Any]:
        meta = {
            "year": self.config.year,
            "timezone": {
                "resolved": str(self._tzinfo.key if hasattr(self._tzinfo, "key") else self._tzinfo),
                "input": self.config.timezone,
                "resolution": self.config.tz_resolution,
                "offset_minutes": int(
                    (self._tzinfo.utcoffset(datetime.now(UTC)) or timedelta(0)).total_seconds()
                    / 60
                ),
            },
            "western_enabled": True,
            "versioning": self.config.versioning,
            "options": self.config.options_raw,
            "warnings": self._meta_warnings,
            "event_count": total_events,
        }
        return meta

    def _debug_payload(self, events: List[_Event]) -> Dict[str, Any]:
        return {
            "config": dataclasses.asdict(self.config),
            "events": [ev.for_timeline() for ev in events],
            "cache_size": len(_MONTH_CACHE),
            "retrograde_windows": {
                body: {
                    k: (v.isoformat() if isinstance(v, datetime) else v)
                    for k, v in window.items()
                }
                for body, window in self._retrograde_windows.items()
            },
            "warnings": list(self._meta_warnings),
        }


# ---------------------------------------------------------------------------
# Standalone helpers
# ---------------------------------------------------------------------------


def _angle_name(natal_body: Optional[str]) -> Optional[str]:
    if not natal_body:
        return None
    return ANGLE_NAME_MAP.get(natal_body)


def _is_outer(body: str) -> bool:
    return PLANET_CLASS.get(body) == "outer"


def _build_event_id(canonical: Dict[str, Any]) -> str:
    blob = json.dumps(canonical, sort_keys=True).encode("utf-8")
    return hashlib.blake2b(blob, digest_size=6).hexdigest()


def _pretty_name(name: str) -> str:
    return name.replace("_", " ").replace("/", " / ") if name else "general"


def _theme_keyword(target: str) -> str:
    if not target:
        return "core priorities"
    expr = PLANET_EXPRESSIONS.get(target)
    if expr:
        return expr.get("theme", "core priorities")
    upper = target.upper()
    if upper in {"ASC", "DSC", "MC", "IC"}:
        mapping = {
            "ASC": "self-expression",
            "DSC": "partnership dynamics",
            "MC": "public ambitions",
            "IC": "foundational roots",
        }
        return mapping.get(upper, "core priorities")
    lower = target.lower()
    if lower.startswith("house"):
        return f"house {lower.replace('house', '').strip()} matters"
    return target.replace("_", " ").lower()


def _interpolate_longitude_crossing(
    prev_lon: float,
    current_lon: float,
    prev_dt: datetime,
    current_dt: datetime,
    boundary: float,
) -> datetime:
    prev_norm = prev_lon % 360.0
    curr_norm = current_lon % 360.0
    boundary_norm = boundary % 360.0

    if curr_norm < prev_norm and prev_norm - curr_norm > 180:
        curr_norm += 360.0
    if boundary_norm < prev_norm:
        boundary_norm += 360.0
    if boundary_norm > curr_norm and (boundary_norm - 360.0) >= prev_norm:
        boundary_norm -= 360.0

    denom = curr_norm - prev_norm
    if abs(denom) < 1e-6:
        return current_dt

    ratio = (boundary_norm - prev_norm) / denom
    ratio = max(0.0, min(1.0, ratio))
    delta = current_dt - prev_dt
    return prev_dt + timedelta(seconds=delta.total_seconds() * ratio)


def _midpoint_longitude(a: float, b: float) -> float:
    diff = ((b - a + 360.0) % 360.0)
    return (a + diff / 2.0) % 360.0


def _interpolate_station(
    prev_speed: float,
    current_speed: float,
    prev_dt: datetime,
    current_dt: datetime,
) -> datetime:
    denom = (abs(prev_speed) + abs(current_speed))
    if denom == 0:
        return current_dt
    ratio = abs(prev_speed) / denom
    ratio = max(0.0, min(1.0, ratio))
    delta = current_dt - prev_dt
    return prev_dt + timedelta(seconds=delta.total_seconds() * ratio)


def _refine_house_crossing(
    start: datetime,
    end: datetime,
    body: str,
    target_house: int,
    cusps: Sequence[float],
    system: str,
    ayan: Optional[str],
) -> datetime:
    left = start
    right = end
    for _ in range(8):
        mid = left + (right - left) / 2
        if (right - left).total_seconds() <= 60:
            break
        pos = _transit_positions(mid, system, ayan).get(body)
        if not pos:
            break
        house = house_of(pos["lon"], cusps)
        if house == target_house:
            right = mid
        else:
            left = mid
    return right


def _events_compatible(a: _Event, b: _Event, tolerance: timedelta) -> bool:
    if a.transit_body != b.transit_body:
        return False
    if (a.natal_body or "") != (b.natal_body or ""):
        return False
    if a.aspect != b.aspect:
        return False
    if a.house and b.house and a.house != b.house:
        return False
    if a.angle and b.angle and a.angle != b.angle:
        return False
    delta = abs((a.timestamp - b.timestamp).total_seconds())
    if delta > tolerance.total_seconds():
        return False
    return True


def _finalise_caution_window(window: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "start": window["start_dt"].isoformat(),
        "end": window["end_dt"].isoformat(),
        "score": round(window["score"], 4),
        "events": window["events"],
        "notes": sorted(window["notes"]),
    }


def _is_supportive_window_event(event: _Event) -> bool:
    if event.aspect in SUPPORTIVE_ASPECTS:
        return True
    if "solar_return" in event.tags:
        return True
    if event.type in {"house_change", "midpoint"} and event.score >= 0.6:
        return True
    return False


def _is_red_flag_event(event: _Event) -> bool:
    if event.aspect in TENSION_ASPECTS and (
        event.transit_body in MALEFIC_BODIES or "retrograde" in event.tags
    ):
        return True
    if "station" in event.tags:
        return True
    if event.type == "retrograde_campaign":
        return True
    if "eclipse" in event.tags and event.score >= 0.6:
        return True
    if event.aspect == "contra_parallel":
        return True
    return False


def _signed_angle_diff(a: float, b: float) -> float:
    return ((a - b + 180.0) % 360.0) - 180.0


def _parse_utc_offset(value: str) -> Optional[timedelta]:
    text = value.strip().upper()
    if text.startswith("UTC") or text.startswith("GMT"):
        text = text[3:]
    if not text:
        return timedelta(0)
    if text[0] not in {"+", "-"}:
        return None
    sign = 1 if text[0] == "+" else -1
    text = text[1:]
    if ":" in text:
        hours_part, minutes_part = text.split(":", 1)
    else:
        hours_part = text[:2]
        minutes_part = text[2:] if len(text) > 2 else "0"
    try:
        hours = int(hours_part or "0")
        minutes = int(minutes_part or "0")
    except ValueError:
        return None
    return timedelta(hours=sign * hours, minutes=sign * minutes)


def _month_cache_key(
    chart_input: Dict[str, Any],
    config: YearlyWesternConfig,
    month: int,
    bodies: Sequence[str],
    step_hours: int,
) -> str:
    place = chart_input.get("place", {})
    key_payload = {
        "year": config.year,
        "month": month,
        "lat": round(place.get("lat", 0.0), 3),
        "lon": round(place.get("lon", 0.0), 3),
        "house_system": chart_input.get("house_system")
        or (chart_input.get("options") or {}).get("house_system"),
        "bodies": list(bodies),
        "scan_step_hours": step_hours,
        "zodiac": chart_input.get("zodiac", TROPICAL_ZODIAC),
        "orb": dataclasses.asdict(config.orb_table),
    }
    blob = json.dumps(key_payload, sort_keys=True).encode("utf-8")
    return hashlib.blake2b(blob, digest_size=8).hexdigest()


def _resolve_timezone(
    tz: Optional[str], mode: str, warnings: Optional[List[str]] = None
) -> Optional[ZoneInfo]:
    if not tz:
        return ZoneInfo("UTC")

    candidates = [tz]
    if " " in tz:
        candidates.append(tz.replace(" ", "_"))
    if "-" in tz:
        candidates.append(tz.replace("-", "/"))
    if tz.upper() != tz:
        candidates.append(tz.upper())

    for candidate in candidates:
        try:
            return ZoneInfo(candidate)
        except Exception:
            continue

    if warnings is not None:
        warnings.append("timezone_fallback")

    if mode == "strict":
        return None

    offset = _parse_utc_offset(tz)
    if offset is not None:
        return timezone(offset)

    if mode in {"heuristic", "fallback"}:
        return ZoneInfo("UTC")

    return None


def _natal_positions(chart_input: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    from . import ephem

    jd = _jd_for_birth(chart_input)
    sidereal = chart_input.get("system") == "vedic"
    ayan = (chart_input.get("options") or {}).get("ayanamsha") if sidereal else None
    positions = ephem.positions_ecliptic(jd, sidereal=sidereal, ayanamsha=ayan)
    return {
        k: {
            "lon": v["lon"],
            "speed_lon": v.get("speed_lon", 0.0),
            "lat": v.get("lat", 0.0),
        }
        for k, v in positions.items()
    }


def _jd_for_birth(chart_input: Dict[str, Any]) -> float:
    from . import ephem

    place = chart_input.get("place", {})
    return ephem.to_jd_utc(
        chart_input.get("date"),
        chart_input.get("time", "12:00:00"),
        place.get("tz", "UTC"),
    )


def _build_windows(events: List[_Event], threshold: float) -> List[Dict[str, Any]]:
    windows: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    last_ts: Optional[datetime] = None
    for ev in events:
        if _is_red_flag_event(ev):
            if current:
                current["end"] = current["events"][-1]["timestamp"]
                windows.append(current)
                current = None
            last_ts = None
            continue
        if not _is_supportive_window_event(ev) or ev.score < threshold:
            if (
                current
                and last_ts
                and (ev.timestamp - last_ts) > timedelta(hours=24)
            ):
                current["end"] = current["events"][-1]["timestamp"]
                windows.append(current)
                current = None
            continue
        payload = ev.for_timeline()
        if not current:
            current = {
                "start": ev.timestamp.isoformat(),
                "score": round(ev.score, 4),
                "events": [payload],
            }
        else:
            current["score"] = max(current["score"], round(ev.score, 4))
            current.setdefault("events", []).append(payload)
        last_ts = ev.timestamp
    if current:
        current["end"] = current["events"][-1]["timestamp"]
        windows.append(current)
    return windows


def _build_cautions(events: List[_Event]) -> List[Dict[str, Any]]:
    cautions: List[Dict[str, Any]] = []
    window: Optional[Dict[str, Any]] = None
    for ev in events:
        if not _is_red_flag_event(ev):
            continue
        entry = ev.for_timeline()
        if window and (ev.timestamp - window["end_dt"]) <= timedelta(hours=24):
            window["events"].append(entry)
            window["end_dt"] = ev.timestamp
            window["score"] = max(window["score"], round(ev.score, 4))
            if entry.get("details", {}).get("note"):
                window["notes"].add(entry["details"]["note"])
            continue
        if window:
            cautions.append(_finalise_caution_window(window))
        notes = set()
        note = entry.get("details", {}).get("note")
        if note:
            notes.add(note)
        window = {
            "start_dt": ev.timestamp,
            "end_dt": ev.timestamp,
            "score": round(ev.score, 4),
            "events": [entry],
            "notes": notes,
        }
    if window:
        cautions.append(_finalise_caution_window(window))
    return cautions


def _build_summary(events: List[_Event]) -> str:
    if not events:
        return "A quiet year with minimal notable alignments."
    high = sum(1 for ev in events if ev.score >= 0.75)
    support = sum(1 for ev in events if ev.aspect in {"trine", "sextile"})
    tension = sum(1 for ev in events if ev.aspect in {"square", "opposition"})
    return (
        f"{len(events)} notable alignments detected. "
        f"{high} peak moments, {support} supportive influences, "
        f"and {tension} tension checkpoints."
    )
