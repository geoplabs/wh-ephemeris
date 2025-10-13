import sys
import types


class _Router:
    def __init__(self, *args, **kwargs):  # pragma: no cover - simple stub
        pass

    def post(self, *args, **kwargs):  # pragma: no cover - simple stub
        def decorator(func):
            return func

        return decorator


fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.APIRouter = _Router
fastapi_stub.HTTPException = Exception
sys.modules.setdefault("fastapi", fastapi_stub)

pydantic_stub = types.ModuleType("pydantic")
pydantic_stub.BaseModel = object
pydantic_stub.Field = lambda *args, **kwargs: kwargs.get("default")
sys.modules.setdefault("pydantic", pydantic_stub)


from api.services import forecast_reports as fr


def _clear_s3_cache():
    if hasattr(fr._get_s3_client, "cache_clear"):
        fr._get_s3_client.cache_clear()


def test_resolve_download_url_prefers_configured_base(monkeypatch):
    monkeypatch.setenv("REPORTS_BASE_URL", "https://cdn.whathoroscope.com")
    monkeypatch.setenv("REPORTS_USE_S3", "false")
    _clear_s3_cache()

    url = fr._resolve_download_url("report-1", "user-42")

    assert url == "https://cdn.whathoroscope.com/reports/user-42/report-1.pdf"

    monkeypatch.delenv("REPORTS_BASE_URL")
    monkeypatch.delenv("REPORTS_USE_S3")
    _clear_s3_cache()


def test_resolve_download_url_defaults_to_api_when_prod(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("REPORTS_USE_S3", "false")
    _clear_s3_cache()

    url = fr._resolve_download_url("report-2", "user-84")

    assert url == "https://api.whathoroscope.com/reports/user-84/report-2.pdf"

    monkeypatch.delenv("APP_ENV")
    monkeypatch.delenv("REPORTS_USE_S3")
    _clear_s3_cache()
