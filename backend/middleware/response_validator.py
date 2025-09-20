from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Iterable
from fastapi import Request, APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse
from starlette.types import ASGIApp

try:
    from jsonschema.validators import Draft202012Validator as _VAL
except Exception:
    try:
        from jsonschema import Draft7Validator as _VAL  # type: ignore
    except Exception:
        _VAL = None

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"

_allowed_hdrs = {
    "content-type", "cache-control", "etag", "last-modified",
    "vary", "expires", "content-language", "content-encoding",
}

def _safe_header_value(val: str, max_len: int = 180) -> str:
    s = str(val).replace("\r", " ").replace("\n", " ")
    # Replace any non-ASCII with '?'
    s = "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in s)
    # Trim and use ASCII-only ellipsis
    if len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s

def _copy_allowed_headers(src) -> Dict[str,str]:
    out: Dict[str,str] = {}
    for k, v in src.items():
        lk = k.lower()
        if lk in _allowed_hdrs:
            out[k] = _safe_header_value(v)
    return out

def _load_manifest_map() -> Dict[Tuple[str, str], str]:
    import yaml
    if not MANIFEST.exists():
        return {}
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    out: Dict[Tuple[str, str], str] = {}
    for api in (data.get("apis") or []):
        method = str(api.get("method") or "").lower().strip()
        path = str(api.get("path") or "").strip()
        schema_id = api.get("response_schema")
        if not (method and path and schema_id):
            continue
        sch_path = None
        for sch in (data.get("schemas") or []):
            if sch.get("id") == schema_id and sch.get("path"):
                sch_path = sch["path"]; break
        out[(method, path)] = sch_path or schema_id
    return out

def _load_schema(full_path: Path) -> Optional[Dict[str, Any]]:
    if not full_path.exists():
        return None
    try:
        return json.loads(full_path.read_text(encoding="utf-8"))
    except Exception:
        return None

class ResponseValidatorMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.enabled = os.getenv("VALIDATE_RESPONSES") == "1" and _VAL is not None
        self.route_to_schema: Dict[Tuple[str, str], Dict[str, Any]] = {}
        if self.enabled:
            manifest_map = _load_manifest_map()
            for (method, path), rel in manifest_map.items():
                sch = _load_schema((ROOT / rel) if not rel.startswith("docs/") else (ROOT / rel))
                if sch:
                    self.route_to_schema[(method, path)] = sch

    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)

        if not self.enabled:
            return resp

        # Only validate for JSON 2xx
        if resp.status_code // 100 != 2 or "application/json" not in (resp.headers.get("content-type","").lower()):
            # still tag visibility on successful responses
            resp.headers["X-Validator-Enabled"] = "1"
            return resp

        # Determine templated path (e.g., "/positions/")
        try:
            route_path = request.scope.get("route").path  # type: ignore[attr-defined]
        except Exception:
            route_path = request.url.path

        key = (request.method.lower(), route_path)
        schema = self.route_to_schema.get(key)

        # Read body safely and rebuild response with a CLEAN header set
        body = b"".join([chunk async for chunk in resp.body_iterator])  # type: ignore
        base_headers = _copy_allowed_headers(resp.headers)
        base_headers["X-Validator-Enabled"] = "1"

        if not schema:
            # mark skip reason but keep it short + safe
            base_headers["X-Validator-Skip"] = _safe_header_value("no-mapping")
            return StarletteResponse(content=body, status_code=resp.status_code,
                                     headers=base_headers, media_type=resp.media_type)

        # Validate JSON
        try:
            data = json.loads(body.decode(resp.charset or "utf-8"))
            _VAL.check_schema(schema)  # type: ignore
            _VAL(schema).validate(data)  # type: ignore
            # success → no X-Schema-Invalid
            return StarletteResponse(content=body, status_code=resp.status_code,
                                     headers=base_headers, media_type=resp.media_type)
        except Exception as e:
            base_headers["X-Schema-Invalid"] = _safe_header_value(str(e))
            return StarletteResponse(content=body, status_code=resp.status_code,
                                     headers=base_headers, media_type=resp.media_type)


def install_response_validator(app) -> None:
    app.add_middleware(ResponseValidatorMiddleware)


def schema_map_router() -> APIRouter:
    """
    Dev-only helper: GET /__schema-map shows whether validation is enabled and
    which (method, path) pairs have schema mappings (from the manifest).
    This does NOT depend on internal middleware state, so it's safe to include anytime.
    """
    r = APIRouter()

    @r.get("/__schema-map")
    def _map():
        enabled = os.getenv("VALIDATE_RESPONSES") == "1" and _VAL is not None
        manifest_map = _load_manifest_map()
        mappings = {f"{m} {p}": rel for (m, p), rel in manifest_map.items()}
        return {"enabled": enabled, "mappings": mappings}

    return r
