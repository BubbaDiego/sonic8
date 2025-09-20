from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import yaml

ROOT = Path(__file__).resolve().parents[2]
FRONTEND_SRC = ROOT / "frontend" / "src"
MANIFEST = ROOT / "docs" / "spec" / "ui.manifest.yaml"

# -- Route parsing -------------------------------------------------------------
ROUTE_TAG_RE = re.compile(r"<Route[^>]*>", re.IGNORECASE)
PATH_ATTR_RE = re.compile(r"path\s*=\s*['\"]([^'\"]+)['\"]")
ELEMENT_ATTR_RE = re.compile(r"element\s*=\s*\{?\s*<\s*([A-Z][A-Za-z0-9_]*)", re.MULTILINE)
COMPONENT_ATTR_RE = re.compile(r"Component\s*=\s*\{\s*([A-Z][A-Za-z0-9_]*)\s*\}")

ROUTE_OBJECT_PATH_RE = re.compile(r"path\s*:\s*['\"]([^'\"]+)['\"]")
ROUTE_OBJECT_ELEMENT_RE = re.compile(r"element\s*:\s*<\s*([A-Z][A-Za-z0-9_]*)", re.MULTILINE)
ROUTE_OBJECT_COMPONENT_RE = re.compile(r"Component\s*:\s*([A-Z][A-Za-z0-9_]*)")

# -- Component parsing ---------------------------------------------------------
FUNCTION_COMPONENT_RE = re.compile(
    r"(?:export\s+)?function\s+([A-Z][A-Za-z0-9_]*)\s*\(([^)]*)\)", re.MULTILINE
)
CONST_COMPONENT_RE = re.compile(
    r"(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*(?::\s*React\.(?:FC|FunctionComponent)<([A-Za-z0-9_]+)>)?\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>",
    re.MULTILINE,
)

PROPTYPES_RE = re.compile(
    r"([A-Z][A-Za-z0-9_]*)\.propTypes\s*=\s*{(.*?)}",
    re.MULTILINE | re.DOTALL,
)
TS_PROPS_RE = re.compile(
    r"(?:export\s+)?(?:interface|type)\s+([A-Za-z0-9_]+)\s*=\s*{(.*?)}",
    re.MULTILINE | re.DOTALL,
)


@dataclass
class ComponentDef:
    name: str
    file: Path
    props_type: Optional[str]


@dataclass
class ComponentInfo:
    id: str
    file: str
    props: List[Dict[str, object]]
    emits: List[str]
    state: List[str]


def iter_frontend_files() -> Iterable[Path]:
    if not FRONTEND_SRC.exists():
        return []
    for path in FRONTEND_SRC.rglob("*"):
        if path.suffix not in {".tsx", ".ts", ".jsx", ".js"}:
            continue
        # Skip build / external directories inside src
        if any(part.startswith(".") for part in path.parts):
            continue
        yield path


def read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def safe_page_id(path: str) -> str:
    slug = path.strip()
    if not slug or slug == "/":
        slug = "root"
    slug = slug.strip("/") or "root"
    slug = re.sub(r"[^A-Za-z0-9]+", "_", slug).strip("_") or "root"
    return f"PAGE_{slug.upper()}"


def parse_route_tags(text: str) -> List[Tuple[str, Optional[str]]]:
    routes: List[Tuple[str, Optional[str]]] = []
    for match in ROUTE_TAG_RE.finditer(text):
        snippet = match.group(0)
        path_match = PATH_ATTR_RE.search(snippet)
        if not path_match:
            continue
        path = path_match.group(1)
        component = None
        element_match = ELEMENT_ATTR_RE.search(snippet)
        if element_match:
            component = element_match.group(1)
        else:
            comp_match = COMPONENT_ATTR_RE.search(snippet)
            if comp_match:
                component = comp_match.group(1)
        routes.append((path, component))
    return routes


def parse_route_objects(text: str) -> List[Tuple[str, Optional[str]]]:
    routes: List[Tuple[str, Optional[str]]] = []
    for match in ROUTE_OBJECT_PATH_RE.finditer(text):
        path = match.group(1)
        component = None
        tail = text[match.end() : match.end() + 200]
        element_match = ROUTE_OBJECT_ELEMENT_RE.search(tail)
        if element_match:
            component = element_match.group(1)
        else:
            component_match = ROUTE_OBJECT_COMPONENT_RE.search(tail)
            if component_match:
                component = component_match.group(1)
        routes.append((path, component))
    return routes


def extract_props_type(param_section: str) -> Optional[str]:
    if not param_section:
        return None
    type_match = re.search(r":\s*([A-Za-z0-9_]+Props?)\b", param_section)
    if type_match:
        name = type_match.group(1)
        if not name.endswith("Props"):
            name = f"{name}Props"
        return name
    return None


def parse_components(path: Path, text: str) -> List[ComponentDef]:
    components: List[ComponentDef] = []
    for match in FUNCTION_COMPONENT_RE.finditer(text):
        name = match.group(1)
        params = match.group(2)
        props_type = extract_props_type(params)
        components.append(ComponentDef(name=name, file=path, props_type=props_type))
    for match in CONST_COMPONENT_RE.finditer(text):
        name = match.group(1)
        declared_type = match.group(2)
        params = match.group(3)
        props_type = declared_type or extract_props_type(params)
        if props_type and not props_type.endswith("Props"):
            props_type = f"{props_type}Props"
        components.append(ComponentDef(name=name, file=path, props_type=props_type))
    return components


def parse_ts_props(text: str) -> Dict[str, List[Dict[str, object]]]:
    props_map: Dict[str, List[Dict[str, object]]] = {}
    for match in TS_PROPS_RE.finditer(text):
        name = match.group(1)
        body = match.group(2)
        if not name.endswith("Props"):
            continue
        props: List[Dict[str, object]] = []
        for line in body.splitlines():
            line = line.strip().rstrip(",;")
            if not line or ":" not in line or line.startswith("//"):
                continue
            prop_name, type_part = [segment.strip() for segment in line.split(":", 1)]
            required = not prop_name.endswith("?")
            prop_name = prop_name.replace("?", "")
            type_token = type_part.split()[0]
            props.append({
                "name": prop_name,
                "type": type_token,
                "required": required,
            })
        props_map[name] = props
    return props_map


def parse_prop_types(text: str) -> Dict[str, List[Dict[str, object]]]:
    props_map: Dict[str, List[Dict[str, object]]] = {}
    for match in PROPTYPES_RE.finditer(text):
        name = match.group(1)
        body = match.group(2)
        props: List[Dict[str, object]] = []
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if not line or ":" not in line or line.startswith("//"):
                continue
            prop_name, rhs = [segment.strip() for segment in line.split(":", 1)]
            required = ".isRequired" in rhs
            type_match = re.search(r"PropTypes\.([A-Za-z0-9_]+)", rhs)
            prop_type = type_match.group(1) if type_match else "any"
            props.append({
                "name": prop_name,
                "type": prop_type,
                "required": required,
            })
        props_map[name] = props
    return props_map


def load_manifest() -> Dict[str, object]:
    if MANIFEST.exists():
        try:
            return yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) or {}
        except Exception:
            return {}
    return {}


def save_manifest(data: Dict[str, object]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"[ui_sweeper] wrote {MANIFEST}")


def update_routes(manifest: Dict[str, object], texts: Dict[Path, str], component_files: Dict[str, Path]) -> None:
    seen: Dict[Tuple[str, Optional[str]], Dict[str, object]] = {}
    for path, text in texts.items():
        for route_path, component_name in parse_route_tags(text) + parse_route_objects(text):
            key = (route_path, component_name)
            if key in seen:
                continue
            component_file = component_files.get(component_name) if component_name else None
            component_file_str: Optional[str] = None
            if component_file:
                try:
                    component_file_str = str(component_file.relative_to(ROOT))
                except ValueError:
                    component_file_str = component_file.as_posix()
            seen[key] = {
                "path": route_path,
                "page_id": safe_page_id(route_path),
                "component": component_name,
                "file": component_file_str,
                "uses": [],
            }
    manifest["routes"] = list(seen.values())


def update_components(
    manifest: Dict[str, object],
    component_defs: Dict[str, ComponentDef],
    props_sources: Dict[str, Dict[str, List[Dict[str, object]]]],
) -> None:
    components: List[ComponentInfo] = []
    for name, comp_def in component_defs.items():
        props: List[Dict[str, object]] = []
        props_type = comp_def.props_type
        if props_type and props_type in props_sources["ts"]:
            props = props_sources["ts"][props_type]
        elif name in props_sources["prop_types"]:
            props = props_sources["prop_types"][name]
        components.append(
            ComponentInfo(
                id=f"COMP_{name.upper()}",
                file=str(comp_def.file.relative_to(ROOT)),
                props=props,
                emits=[],
                state=[],
            )
        )
    manifest["components"] = [
        {
            "id": comp.id,
            "file": comp.file,
            "props": comp.props,
            "emits": comp.emits,
            "state": comp.state,
        }
        for comp in sorted(components, key=lambda item: item.id)
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the UI manifest from the frontend source tree")
    parser.add_argument("--entry", default=None, help="Override the frontend entry file path")
    parser.add_argument("--routes-only", action="store_true", help="Only refresh routes")
    parser.add_argument("--components-only", action="store_true", help="Only refresh components")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to disk; print manifest")
    args = parser.parse_args()

    manifest = load_manifest()
    manifest.setdefault("ui_spec_version", 1)
    frontend = manifest.setdefault("frontend", {})
    frontend.setdefault("framework", "react")
    frontend.setdefault("bundler", "vite")
    frontend["entry"] = args.entry or frontend.get("entry", "frontend/src/main.tsx")
    frontend.setdefault("router", "react-router")
    frontend.setdefault("base_url_hint", "http://127.0.0.1:5173")

    files = list(iter_frontend_files())
    texts = {path: read_file(path) for path in files}

    component_defs: Dict[str, ComponentDef] = {}
    for path, text in texts.items():
        for comp in parse_components(path, text):
            component_defs.setdefault(comp.name, comp)

    component_files = {name: comp.file for name, comp in component_defs.items()}

    if not args.components_only:
        update_routes(manifest, texts, component_files)

    if not args.routes_only:
        ts_props: Dict[str, List[Dict[str, object]]] = {}
        prop_types_props: Dict[str, List[Dict[str, object]]] = {}
        for path, text in texts.items():
            ts_props.update(parse_ts_props(text))
            prop_types_props.update(parse_prop_types(text))
        update_components(manifest, component_defs, {"ts": ts_props, "prop_types": prop_types_props})

    if args.dry_run:
        print(yaml.safe_dump(manifest, sort_keys=False))
    else:
        save_manifest(manifest)


if __name__ == "__main__":
    main()
