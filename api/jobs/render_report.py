"""Background worker that renders PDF reports in-process."""

import threading
import traceback
from pathlib import Path
from typing import Dict, Any

from ..services.inproc_queue import Q
from ..services.job_store import STORE
from ..services.pdf_renderer import render_western_natal_pdf
from ..services.wheel_svg import simple_wheel_svg

# Reuse compute logic from charts router
from ..routers.charts import compute_chart
from ..schemas import ComputeRequest

_ASSETS_BASE = Path("/app/data/dev-assets/reports")


def _build_payload(chart_req: Dict[str, Any]) -> Dict[str, Any]:
    """Build payload for PDF renderer by computing chart data."""

    res = compute_chart(ComputeRequest(**chart_req["chart_input"]))
    data = res.model_dump() if hasattr(res, "model_dump") else res
    data["chart_input"] = chart_req["chart_input"]
    data["wheel_svg"] = simple_wheel_svg("Western Natal")
    return data


def worker_loop() -> None:
    while True:
        rid = Q.get()
        try:
            STORE.update(rid, status="processing")
            job = STORE.get(rid)
            payload = job["payload"]
            data = _build_payload(payload)
            out = _ASSETS_BASE / f"{rid}.pdf"
            render_western_natal_pdf(
                data, str(out), branding=(payload.get("branding") or {})
            )
            STORE.update(rid, status="done", file_path=str(out))
        except Exception:
            traceback.print_exc()
            STORE.update(rid, status="error", error="RENDER_FAILED")
        finally:
            Q.task_done()


_worker_thread = None


def ensure_worker_started() -> None:
    """Ensure a worker thread is running for rendering jobs."""

    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return

    _ASSETS_BASE.mkdir(parents=True, exist_ok=True)
    _worker_thread = threading.Thread(target=worker_loop, daemon=True)
    _worker_thread.start()

