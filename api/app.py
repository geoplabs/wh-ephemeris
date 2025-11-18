import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
from .routers import yearly as yearly_router
from .routers import monthly as monthly_router
from .routers import panchang as panchang_router
from .jobs.render_report import ensure_worker_started
from .middleware.auth import APIKeyMiddleware
from .middleware.ratelimit import RateLimitMiddleware
from .middleware.logging import LoggingMiddleware



app = FastAPI(title="wh-ephemeris (dev)", version="0.2.0")

# Configure CORS - localhost for development, production domains for production
app_env = os.getenv("APP_ENV")
is_dev = app_env is None or app_env.lower() in {"dev", "development"}

if is_dev:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Length","Content-Type"],
        max_age=86400,
    )
else:
    allowed = [
        "https://whathoroscope.com",
        "https://www.whathoroscope.com",
        "https://api.whathoroscope.com",
    ]
    preview = os.getenv("PREVIEW_ORIGIN")  # e.g., your Vercel preview URL
    if preview:
        allowed.append(preview)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Length","Content-Type"],
        max_age=86400,
    )

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
app.include_router(yearly_router.router)
app.include_router(monthly_router.router)
app.include_router(panchang_router.router)

# Start worker immediately to support tests that instantiate TestClient
# without lifespan events.
ensure_worker_started()


@app.on_event("startup")
def _start_worker() -> None:
    ensure_worker_started()



@app.get("/__health")
def health():
    return {"ok": True}


# Dev assets static serve (for quick PDF/SVG previews saved under data/dev-assets)
import os
DEV_ASSETS_DIR = Path(os.getenv("HOME", "/opt/app")) / "data" / "dev-assets"
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
