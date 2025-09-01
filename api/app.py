from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from .routers import charts as charts_router

from .routers import dashas as dashas_router
from .routers import transits as transits_router

from .routers import reports as reports_router
from .routers import forecasts as forecasts_router
from .routers import compatibility as compatibility_router
from .routers import remedies as remedies_router
from .routers import interpret as interpret_router
from .routers import natal as natal_router
from .jobs.render_report import ensure_worker_started
from .middleware.auth import APIKeyMiddleware
from .middleware.ratelimit import RateLimitMiddleware
from .middleware.logging import LoggingMiddleware



app = FastAPI(title="wh-ephemeris (dev)", version="0.2.0")

app.add_middleware(APIKeyMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(LoggingMiddleware)

app.include_router(charts_router.router)

app.include_router(dashas_router.router)
app.include_router(transits_router.router)

app.include_router(reports_router.router)
app.include_router(forecasts_router.router)
app.include_router(compatibility_router.router)
app.include_router(remedies_router.router)
app.include_router(interpret_router.router)
app.include_router(natal_router.router)

# Start worker immediately to support tests that instantiate TestClient
# without lifespan events.
ensure_worker_started()


@app.on_event("startup")
def _start_worker() -> None:
    ensure_worker_started()



@app.get("/__health")
def health():
    return {"ok": True}


# Dev assets static serve (for quick PDF/SVG previews saved under /app/data/dev-assets)
DEV_ASSETS_DIR = Path("/app/data/dev-assets")
DEV_ASSETS_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/dev-assets/{path:path}")
def dev_assets(path: str):
    fp = DEV_ASSETS_DIR / path
    if not fp.exists():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(fp)


@app.get("/")
def root():
    return {"message": "wh-ephemeris dev API is running. See /__health and /docs (when implemented)."}
