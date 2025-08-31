from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse
from pathlib import Path
from .routers import charts as charts_router

app = FastAPI(title="wh-ephemeris (dev)", version="0.1.0")
app.include_router(charts_router.router)

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
