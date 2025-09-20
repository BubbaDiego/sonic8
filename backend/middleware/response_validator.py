from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# jsonschema version-flexible import
try:
    from jsonschema.validators import Draft202012Validator as _VAL
except Exception:  # pragma: no cover
    try:
        from jsonschema import Draft7Validator as _VAL  # type: ignore
    except Exception as e:  # pragma: no cover
        _VAL = None

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"
SCHEMAS_DIR = ROOT / "docs" / "spec" / "schemas"

def _load_manifest_map() -> Dict[Tuple[str, str], str]:
    """
    Returns a dict mapping (method_lower, path_string) -> schema_path (repo-relative).
    Expects manifest.apis[*] entries with fields: method, path, response_schema.
    """
    import yaml
    if not MANIFEST.exists():
        return {}
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
    out: Dict[Tuple[str, str], str] = {}
    for api in (data.get("apis") or []):
        method = str(api.get("method") or "").lower().strip()
        path = str(api.get("endpoint") or api.get("path") or "").strip()
        schema_id = api.get("response_schema")
        if not (method and path and schema_id):
            continue
        # schemas[*].id -> path; fall back to assuming path is given
        sch_path = None
        for sch in (data.get("schemas") or []):
            if sch.get("id") == schema_id and sch.get("path"):
                sch_path = sch["path"]
                break
        sch_path = sch_path or schema_id  # allow direct file path
        out[(method, path)] = sch_path
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
                rel_path = Path(rel)
                if rel_path.is_absolute():
                    try:
                        rel_path = rel_path.relative_to("/")
                    except ValueError:
                        pass
                if not rel_path.parts:
                    continue
                if rel_path.parts[0] == "docs":
                    sch_full = ROOT / rel_path
                else:
                    sch_full = SCHEMAS_DIR / rel_path
                schema = _load_schema(sch_full)
                if schema:
                    self.route_to_schema[(method, path)] = schema

    async def dispatch(self, request: Request, call_next):
        resp: Response = await call_next(request)
        if not self.enabled:
            return resp

        # Only validate JSON and 2xx
        ctype = resp.headers.get("content-type", "")
        if resp.status_code // 100 != 2 or "application/json" not in ctype.lower():
            return resp

        # Normalize path to the templated route (e.g., "/positions/{id}" not "/positions/123")
        # FastAPI stores this as request.scope["route"].path if mounted normally
        try:
            route_path = request.scope.get("route").path  # type: ignore[attr-defined]
        except Exception:
            route_path = request.url.path  # fallback

        key = (request.method.lower(), route_path)
        schema = self.route_to_schema.get(key)
        if not schema:
            # No schema mapping → skip
            return resp

        # Read body (Starlette Response already has body in .body for JSONResponse)
        try:
            raw = b"".join([chunk async for chunk in resp.body_iterator])  # type: ignore
            # rebuild response body iterator because we've consumed it
            resp.body = raw  # type: ignore[assignment]
            data = json.loads(raw.decode(resp.charset or "utf-8"))
        except Exception:
            # If we can't read/parse, signal but don't break prod traffic
            resp.headers["X-Schema-Invalid"] = "unreadable"
            return resp

        # Validate
        try:
            _VAL.check_schema(schema)  # type: ignore
            _VAL(schema).validate(data)  # type: ignore
        except Exception as e:
            # Non-fatal: tag the response so you see it during dev
            resp.headers["X-Schema-Invalid"] = str(e).splitlines()[0][:200]
        return resp

def install_response_validator(app) -> None:
    """
    Call this AFTER you mount routers so the routes are discoverable.
    Enable by setting VALIDATE_RESPONSES=1 in your environment.
    """
    app.add_middleware(ResponseValidatorMiddleware)
