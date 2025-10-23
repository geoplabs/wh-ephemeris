# Horoscope Cleaner

Transforms fallback "Option B" horoscope JSON into clean, user-ready output. The pipeline, located under `api/services/option_b_cleaner`, removes transit jargon, enforces second-person POV, normalizes bullet voice, and injects a Lucky block derived from the dominant transit.

## Usage

```bash
python cli.py tests/sample_option_b.json out.json
```

Input is raw Option B JSON with transit-heavy strings. Output is normalized UX JSON rendered through the Jinja template. All telemetry stays in `tech_notes` and the Lucky block derives from the dominant transit.

## Testing

```bash
pytest
```
