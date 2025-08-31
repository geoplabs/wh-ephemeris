from queue import Queue
from threading import Thread
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML
from typing import Dict, Any

from .schemas import ComputeRequest
from .routers import charts as charts_router

DEV_ASSETS_DIR = Path("/app/data/dev-assets")
DEV_ASSETS_DIR.mkdir(parents=True, exist_ok=True)

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
            pdf_path = DEV_ASSETS_DIR / f"{report_id}.pdf"
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
