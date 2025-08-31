import uuid
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue
from threading import Thread
from typing import Dict, Any, Tuple

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schemas import ReportCreateRequest, ReportStatusEnum
from .routers import charts as charts_router
from .services.pdf_renderer import render as render_pdf
from .services.wheel_svg import render_wheel

DEV_ASSETS_DIR = Path("/app/data/dev-assets")
REPORTS_DIR = DEV_ASSETS_DIR / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

queue: Queue = Queue()


class JobStore:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.idempo: Dict[Tuple[str, str, str], str] = {}

    def create_job(self, req: ReportCreateRequest, fingerprint: str) -> Tuple[str, Dict[str, Any], bool]:
        """Create a job; return (id, job, existed)"""
        if req.idempotency_key:
            key = (req.product, fingerprint, req.idempotency_key)
            if key in self.idempo:
                rid = self.idempo[key]
                return rid, self.jobs[rid], True
        rid = f"rpt_{uuid.uuid4().hex[:24]}"
        job = {
            "status": ReportStatusEnum.queued,
            "queued_at": datetime.now(timezone.utc),
            "payload": req.model_dump(),
            "file_path": None,
            "error": None,
        }
        self.jobs[rid] = job
        if req.idempotency_key:
            self.idempo[(req.product, fingerprint, req.idempotency_key)] = rid
        queue.put(rid)
        return rid, job, False


job_store = JobStore()


def worker_loop():
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates" / "reports"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("western_natal.html.j2")
    css_tmpl = env.get_template("report.css")
    while True:
        rid = queue.get()
        job = job_store.jobs.get(rid)
        if not job:
            queue.task_done()
            continue
        job["status"] = ReportStatusEnum.processing
        try:
            req = ReportCreateRequest(**job["payload"])
            chart = charts_router.compute_chart(req.chart_input)
            bodies = [b.model_dump() for b in chart.bodies]
            wheel = render_wheel(bodies)
            css = css_tmpl.render(branding=req.branding)
            html = template.render(chart=chart, req=req, wheel_svg=wheel, css=css)
            pdf_path = REPORTS_DIR / f"{rid}.pdf"
            render_pdf(html, css, pdf_path)
            job["status"] = ReportStatusEnum.done
            job["file_path"] = pdf_path.name
        except Exception:
            job["status"] = ReportStatusEnum.error
            job["error"] = "RENDER_FAILED"
        finally:
            queue.task_done()


# Start background worker thread on import for dev/testing
Thread(target=worker_loop, daemon=True).start()
