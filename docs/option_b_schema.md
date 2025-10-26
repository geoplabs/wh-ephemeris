# Option B JSON Schema Reference

This document summarizes the Option B payload structure that feeds the cleaner pipeline.
It is based on the shapes enforced by the forecast schemas and how downstream code
consumes the transit metadata.

## Top-level envelope

| Field | Type | Notes |
| --- | --- | --- |
| `profile_name` | `string` | Preferred user display name. Optional when `meta.profile_name` is provided. |
| `date` | `string` | ISO-8601 date string for the forecast. |
| `mood` | `string` | Pre-computed sentiment label surfaced in the final template. |
| `theme` | `string` | Short descriptor for the day's focus. |
| `opening_summary` | `string` | Raw introduction text that is rewritten before rendering. |
| `morning_mindset` | `object` | Contains the `paragraph` and `mantra` strings used in the morning block. |
| `career`, `love`, `health`, `finance` | `object` | Each section exposes a `paragraph` plus typed bullet lists that are normalized by the cleaner. |
| `do_today`, `avoid_today` | `array[string]` | Action prompts and cautions that are rewritten into second-person imperatives. |
| `one_line_summary` | `string` | Closing statement for the report. |
| `events` | `array[Event]` | Full list of transit events; if omitted, `top_events` is used instead. |
| `top_events` | `array[Event]` | Highlighted subset of the transit list, used as a fallback for dominance logic. |
| `meta` | `object` | Miscellaneous metadata such as `profile_name` or `date`. |

The sample payload in `tests/sample_option_b.json` demonstrates each of the top-level fields, in
cluding the `events` array consumed by the rendering context.【F:tests/sample_option_b.json†L1-L55】

## Event object

Transit events reuse the `ForecastEvent` schema that powers the API responses.【F:api/schemas/forecasts.py†L57-L104】
The core fields are:

| Field | Type | Notes |
| --- | --- | --- |
| `date` | `string` | Calendar date (UTC) when the transit is exact. |
| `transit_body` | `string` | Planet or point making the transit. |
| `natal_body` | `string` | Natal planet/point receiving the aspect. |
| `aspect` | `string` | Aspect type such as `conjunction`, `trine`, `square`, `sextile`, or `opposition`. |
| `orb` | `number` | Orb distance in degrees. |
| `score` | `number` | Signed strength metric used for ranking and tone. |
| `note` | `string` | Human-readable explanation of the transit. Optional. |
| `transit_sign` | `string` | Transit sign label when available. Optional. |
| `natal_sign` | `string` | Natal sign label when available. Optional. |
| `zodiac` | `string` | Indicates `tropical` or `sidereal` labeling when provided. Optional. |

Downstream reporting utilities also expect optional house-aware metadata (for example `natal_house`)
and apply thematic tags when it is present.【F:api/services/forecast_reports.py†L239-L287】

### Benefic/malefic flags

While the upstream schema does not enforce explicit booleans, the classifier recognises the optional
keys `is_benefic`, `transit_benefic`, `is_malefic`, and `transit_malefic` when they are supplied, so
Option B producers can pass benefic/malefic flags without additional wiring. The router falls back to
planet defaults (Jupiter/Venus/Sun/Moon as benefics and Mars/Saturn/Pluto as malefics) when the flags
are absent.【F:src/content/archetype_router.py†L119-L149】

## Normalisation pipeline touchpoints

* `build_context` uses the `events`/`top_events` arrays to derive the dominant transit and sign for
  lucky-block generation and for tone classification.【F:api/services/option_b_cleaner/render.py†L100-L152】
* Section copy (`career`, `love`, `health`, `finance`) is rewritten using consistent tone and
  descriptors before being rendered into `template.json.j2`.【F:api/services/option_b_cleaner/language.py†L81-L175】

This reference provides the baseline for adding new metadata keys to the Option B payload while
maintaining compatibility with the renderer and classifier.
