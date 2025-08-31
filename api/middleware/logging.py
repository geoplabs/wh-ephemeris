import os
import json
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.getenv("LOGGING_ENABLED", "false").lower() != "true":
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        elapsed = round((time.time() - start) * 1000, 2)
        log = {
            "ts": time.time(),
            "ip": request.client.host,
            "api_key": getattr(request.state, "api_key", None),
            "endpoint": request.url.path,
            "status": response.status_code,
            "latency_ms": elapsed,
        }
        print(json.dumps(log))
        return response
