"""Background worker that renders PDF reports in-process."""

import threading
import traceback
from pathlib import Path
from typing import Dict, Any

from ..services.inproc_queue import Q
from ..services.job_store import STORE
from ..services.pdf_renderer import render_western_natal_pdf
from ..services.wheel_svg import simple_wheel_svg

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
            product = payload["product"]
            ci = payload["chart_input"]
            brand = payload.get("branding") or {}
            out = _ASSETS_BASE / f"{rid}.pdf"
            if product == "western_natal_pdf":
                data = _build_payload(payload)
                render_western_natal_pdf(data, str(out), branding=brand)
            elif product == "yearly_forecast_pdf":
                from ..services.forecast_builders import yearly_payload
                data = yearly_payload(ci, payload.get("options", {"year": 2025}))
                render_western_natal_pdf(
                    data,
                    str(out),
                    branding=brand,
                    template_name="yearly_forecast.html.j2",
                )
            elif product == "monthly_horoscope_pdf":
                from ..services.forecast_builders import monthly_payload
                data = monthly_payload(ci, payload.get("options", {"year": 2025, "month": 8}))
                render_western_natal_pdf(
                    data,
                    str(out),
                    branding=brand,
                    template_name="monthly_horoscope.html.j2",
                )
            elif product == "compatibility_pdf":
                from ..services.compatibility_engine import (
                    synastry,
                    midpoint_composite,
                    aggregate_score,
                )
                other = payload["partner_chart_input"]
                types = ["conjunction", "opposition", "square", "trine", "sextile"]
                syn = synastry(ci, other, types, 4.0)
                score = aggregate_score(syn)
                comp = midpoint_composite(ci, other)
                data = {"synastry": syn, "score": score, "composite": comp}
                render_western_natal_pdf(
                    data,
                    str(out),
                    branding=brand,
                    template_name="compatibility.html.j2",
                )
            elif product == "remedies_pdf":
                from ..services.remedies_engine import compute_remedies
                data = {"items": compute_remedies(ci, allow_gemstones=True)}
                render_western_natal_pdf(
                    data,
                    str(out),
                    branding=brand,
                    template_name="remedies.html.j2",
                )
            elif product == "spiritual_mission_pdf":
                data = {
                    "themes": [
                        "Growth via service and learning",
                        "Letting go of past attachments",
                    ],
                    "notes": [],
                }
                render_western_natal_pdf(
                    data,
                    str(out),
                    branding=brand,
                    template_name="spiritual_mission.html.j2",
                )
            else:
                raise ValueError("UNKNOWN_PRODUCT")
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


if __name__ == "__main__":
    ensure_worker_started()
