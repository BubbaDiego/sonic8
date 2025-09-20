from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "docs" / "spec" / "spec.manifest.yaml"
SCHEMAS = ROOT / "docs" / "spec" / "schemas"
BASE = os.getenv("SPEC_BASE_URL", "http://127.0.0.1:5000")


def infer_schema(value):
    """Very small inference (object/array/string/number/boolean/null) with recursion."""

    if value is None:
        return {"type": ["null", "string", "number", "object", "array", "boolean"]}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, (int, float)):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        item_schemas = [infer_schema(v) for v in value[:3]] or [{"type": "string"}]
        return {"type": "array", "items": item_schemas[0]}
    if isinstance(value, dict):
        props = {}
        required = []
        for key, val in list(value.items())[:25]:
            props[key] = infer_schema(val)
            if key in {"id", "status", "timestamp"}:
                required.append(key)
        output = {"type": "object", "properties": props}
        if required:
            output["required"] = required
        output["additionalProperties"] = True
        return output
    return {"type": "string"}


def fetch(method: str, path: str):
    url = BASE.rstrip("/") + path
    req = urllib.request.Request(url, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type.lower():
                return None
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            return json.loads(exc.read().decode("utf-8"))
        except Exception:
            return None
    except Exception:
        return None


def main():
    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    apis = manifest.get("apis") or []
    schemas = manifest.get("schemas") or []
    existing_schema_ids = {schema["id"] for schema in schemas if schema.get("id")}
    changed = False

    for api in apis:
        if api.get("response_schema"):
            continue
        method = (api.get("method") or "GET").upper()
        path = api.get("path")
        if not path:
            continue
        sample = fetch(method, path)
        if sample is None:
            continue
        schema = infer_schema(sample)
        schema["$id"] = f"schema/{(path.strip('/') or 'root').replace('/', '_')}.json"
        schema["examples"] = [sample]
        output_name = (path.strip("/") or "root").replace("/", "_") + ".json"
        output_path = SCHEMAS / output_name
        SCHEMAS.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        schema_id = "SCHEMA-" + (path.strip("/") or "ROOT").replace("/", "_").upper()
        if schema_id not in existing_schema_ids:
            schemas.append({"id": schema_id, "path": f"docs/spec/schemas/{output_name}"})
            existing_schema_ids.add(schema_id)
        api["response_schema"] = schema_id
        changed = True
        print(f"[spec_schema_sampler] wrote {output_path.name} and mapped {method} {path}")

    if changed:
        manifest["schemas"] = schemas
        manifest["apis"] = apis
        MANIFEST.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
        print("[spec_schema_sampler] manifest updated.")
    else:
        print("[spec_schema_sampler] no schemas added; nothing sampled or all mapped.")


if __name__ == "__main__":
    main()
