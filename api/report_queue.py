from queue import Queue
from threading import Thread
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from typing import Dict, Any

from .schemas import ComputeRequest
from .routers import charts as charts_router

# Where generated PDFs are stored during development
DEV_ASSETS_ROOT = Path(__file__).resolve().parents[1] / "data" / "dev-assets"
REPORTS_DIR = DEV_ASSETS_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# simple in-memory report metadata store
reports: Dict[str, Dict[str, Any]] = {}
queue: Queue = Queue()

def _worker_loop():
    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape()
    )
    template = env.get_template("report.html")
    while True:
        report_id, payload = queue.get()
        reports[report_id]["status"] = "processing"
        try:
            chart = charts_router.compute_chart(ComputeRequest(**payload))
            html = template.render(chart=chart)
            pdf_path = REPORTS_DIR / f"{report_id}.pdf"
            HTML(string=html).write_pdf(pdf_path)
            reports[report_id]["status"] = "done"
            reports[report_id]["file"] = pdf_path.name
        except Exception:
            reports[report_id]["status"] = "error"
        finally:
            queue.task_done()

def start_worker():
    thread = Thread(target=_worker_loop, daemon=True)
    thread.start()

# Start worker on import for dev/testing
start_worker()
