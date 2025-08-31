M3.1 Add schemas: api/schemas/dashas.py, api/schemas/transits.py; export in api/schemas/__init__.py
M3.2 Implement Vimshottari service: api/services/dashas_vimshottari.py (Maha + Antar), using Moon sidereal lon and Lahiri as default; KP via chart_input.options
M3.3 Implement Transit engine: api/services/transits_engine.py with daily stepping, aspect hits, severity scoring
M3.4 Add routers: api/routers/dashas.py (/v1/dashas/compute), api/routers/transits.py (/v1/transits/compute); wire in app.py
M3.5 Tests: tests/test_dashas.py and tests/test_transits.py — must pass in Codex without Docker
M3.6 Keep EPHEMERIS_BACKEND environment switch working (moseph in CI)
M3.7 Update OpenAPI (examples for both endpoints)
CHECKPOINT
