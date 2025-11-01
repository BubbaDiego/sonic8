from pathlib import Path
from typing import Dict, Iterable, List, Tuple

try:
    from rapidfuzz import fuzz  # optional but recommended
except Exception:  # pragma: no cover
    fuzz = None

# Heuristics for heavy API tests (we skip these unless topic says otherwise)
HEAVY_MARKERS = (
    "import fastapi",
    "from fastapi",
    "import starlette",
    "from starlette",
    "import pydantic",
    "from pydantic",
)
API_INTENT_TOKENS = {"api", "fastapi", "openapi", "route", "routes", "bp", "blueprint"}


def _fuzzy_hit(text: str, query: str, threshold: int) -> bool:
    if not fuzz:
        return query.lower() in text.lower()
    return fuzz.WRatio(query, text) >= threshold


def _read_text_safe(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def _iter_test_files(extra_paths: List[str]) -> List[Path]:
    """
    Return a de-duped list of test files from the given roots (or default).
    We avoid pytest's import-time collection to keep unrelated deps from exploding.
    """
    candidates: List[Path] = []
    roots = [Path(p) for p in (extra_paths or [])]
    if not roots:
        roots = [Path("test_core/tests")]
    for root in roots:
        if root.is_file() and root.suffix == ".py":
            candidates.append(root)
        elif root.is_dir():
            candidates.extend(root.rglob("test_*.py"))
            candidates.extend(root.rglob("*_test.py"))
    # de-dupe while preserving order
    seen, out = set(), []
    for f in candidates:
        if f not in seen:
            out.append(f)
            seen.add(f)
    return out


def _build_k_expr(tokens: Iterable[str]) -> str:
    toks = sorted({t for t in tokens if t})
    return " or ".join(toks)


def expand_with_synonyms(topics: List[str], synonyms: Dict[str, List[str]]) -> List[str]:
    expanded = set()
    for t in topics:
        expanded.add(t)
        for syn in synonyms.get(t, []):
            expanded.add(syn)
    # Quality of life: add a couple common variants
    if "launch" in expanded:
        expanded.update({"launch_pad", "launchpad", "lp"})
    return sorted(expanded)


def plan(
    topic_words: List[str],
    fuzzy: int,
    topics_meta: Dict,
    extra_paths: List[str],
) -> Tuple[List[str], str, List[str]]:
    """
    File-system scan:
      - Gather test files under extra_paths (or test_core/tests by default)
      - Pick files whose filename/content match any topic term (fuzzy or substring)
      - Skip heavy API tests unless topic clearly intends API work
      - Return file paths (strict discovery), a helpful -k expression, and the file hit list
    """
    topic_terms = expand_with_synonyms(topic_words, topics_meta.get("synonyms", {}))
    test_files = _iter_test_files(extra_paths)
    include_api = any(tok.lower() in API_INTENT_TOKENS for tok in topic_terms)

    hits: List[str] = []
    for f in test_files:
        text = _read_text_safe(f)
        # default: skip heavy tests unless user intent says API
        if not include_api:
            lower = text.lower()
            if any(hint in lower for hint in HEAVY_MARKERS):
                continue
        hay = f.name + "\n" + text
        for t in topic_terms:
            if _fuzzy_hit(hay, t, threshold=fuzzy):
                hits.append(str(f))
                break

    # If nothing matched: return empty to let caller show a friendly message.
    if not hits:
        return [], _build_k_expr(topic_terms), []

    tokens = set(topic_terms) | {Path(p).stem for p in hits}
    k_expr = _build_k_expr(tokens)
    return hits, k_expr, hits
