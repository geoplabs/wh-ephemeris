from ..services.job_store import STORE
from ..services.inproc_queue import Q


def enqueue_report_job(payload: dict) -> str:
    idk = payload.pop("idempotency_key", None)
    rid = STORE.create(payload=payload, idempotency_key=idk)
    Q.put(rid)
    return rid
