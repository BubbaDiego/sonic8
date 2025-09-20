from __future__ import annotations
import json, os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from fastapi import APIRouter, Request, Response
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
SCHEMAS_DIR = ROOT / "docs" / "spec" / "schemas"

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
                sch_path = sch["path"]
                break
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
        self.raw_map: Dict[Tuple[str, str], str] = {}
        if self.enabled:
            manifest_map = _load_manifest_map()
            self.raw_map = manifest_map
            for (method, path), rel in manifest_map.items():
                schema_path = (ROOT / rel) if not rel.startswith("docs/") else (ROOT / rel)
                schema = _load_schema(schema_path)
                if schema:
                    self.route_to_schema[(method, path)] = schema

    async def dispatch(self, request: Request, call_next):
        resp: StarletteResponse = await call_next(request)
        if not self.enabled:
            return resp

        # Always tag when enabled so it's visible
        resp.headers["X-Validator-Enabled"] = "1"

        # Only validate successful JSON responses
        if resp.status_code // 100 != 2:
            return resp
        ctype = resp.headers.get("content-type", "").lower()
        if "application/json" not in ctype:
            return resp

        # Get templated route path (e.g. "/positions/{id}")
        try:
            route_path = request.scope.get("route").path  # type: ignore[attr-defined]
        except Exception:
            route_path = request.url.path

        key = (request.method.lower(), route_path)
        schema = self.route_to_schema.get(key)
        if not schema:
            # No mapping — mark why
            resp.headers.setdefault("X-Schema-Invalid", "no-mapping")
            return resp

        # Safely read and restore body
        try:
            body = b"".join([chunk async for chunk in resp.body_iterator])  # type: ignore
            # Recreate a fresh Response with same props so body isn't lost
            new_resp = StarletteResponse(
                content=body,
                status_code=resp.status_code,
                headers=dict(resp.headers),
                media_type=resp.media_type
            )
            # Validate JSON
            data = json.loads(body.decode(resp.charset or "utf-8"))
            _VAL.check_schema(schema)  # type: ignore
            _VAL(schema).validate(data)  # type: ignore
            return new_resp
        except Exception as e:
            # Put first line of error in header
            msg = str(e).splitlines()[0][:200]
            resp.headers["X-Schema-Invalid"] = msg or "validation-error"
            # Rebuild response with original body if we have it
            try:
                body  # type: ignore
                return StarletteResponse(
                    content=body,
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    media_type=resp.media_type
                )
            except Exception:
                return resp

def install_response_validator(app) -> None:
    app.add_middleware(ResponseValidatorMiddleware)

# Debug helper: a router that reveals what mappings are loaded (dev only)
def schema_map_router(mw: ResponseValidatorMiddleware):
    r = APIRouter()
    @r.get("/__schema-map")
    def _map():
        return {
            "enabled": mw.enabled,
            "mappings": {f"{k[0]} {k[1]}": v for k,v in mw.raw_map.items()},
            "validated": list({f"{k[0]} {k[1]}" for k in mw.route_to_schema.keys()}),
        }
    return r
