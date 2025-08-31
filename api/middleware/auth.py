import os
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if os.getenv("AUTH_ENABLED", "false").lower() != "true":
            return await call_next(request)

        keys = os.getenv("API_KEYS", "").split(",")
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Missing API key"}, status_code=401)
        token = auth.replace("Bearer ", "").strip()
        if token not in keys:
            return JSONResponse({"detail": "Invalid API key"}, status_code=403)

        request.state.api_key = token
        return await call_next(request)
