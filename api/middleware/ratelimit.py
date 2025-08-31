import os
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

_counters = defaultdict(list)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.getenv("RATE_LIMIT_ENABLED", "false").lower() != "true":
            return await call_next(request)

        key = getattr(request.state, "api_key", request.client.host)
        limit = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
        now = time.time()

        window = [t for t in _counters[key] if t > now - 60]
        window.append(now)
        _counters[key] = window

        if len(window) > limit:
            return JSONResponse({"detail": "Rate limit exceeded"}, status_code=429)

        return await call_next(request)
