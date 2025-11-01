from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple
import subprocess
try:
    from rapidfuzz import fuzz, process  # optional but recommended
except Exception:  # pragma: no cover
    fuzz = None
    process = None


def collect_nodeids(pytest_args: List[str]) -> List[str]:
    """
    Return nodeids via pytest --collect-only -q.
    Example nodeid: test_core/tests/test_launch_pad_web.py::TestWeb::test_health
    """
    cmd = ["pytest", "--collect-only", "-q"] + (pytest_args or [])
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    nodeids = []
    for line in out.stdout.splitlines():
        s = line.strip()
        # keep files and nodeids
        if "::" in s or s.endswith(".py"):
            nodeids.append(s)
    return nodeids


def fuzzy_filter(candidates: List[str], query: str, threshold: int = 75) -> Set[str]:
    if not process:
        # Substring fallback
        q = query.lower()
        return {c for c in candidates if q in c.lower()}
    matches = process.extract(query, candidates, scorer=fuzz.WRatio, limit=None)
    return {cand for cand, score, _ in matches if score >= threshold}


def build_k_expr(tokens: Iterable[str]) -> str:
    parts = [f"{t}" for t in set(tokens)]
    return " or ".join(parts) if parts else ""


def expand_with_synonyms(topics: List[str], synonyms: Dict[str, List[str]]) -> List[str]:
    expanded = []
    for t in topics:
        expanded.append(t)
        expanded.extend(synonyms.get(t, []))
    return sorted(set(expanded))


def plan(topic_words: List[str], fuzzy: int, topics_meta: Dict, extra_paths: List[str]) -> Tuple[List[str], str, List[str]]:
    # 1) gather nodeids
    nodeids = collect_nodeids(extra_paths)
    # 2) expand with synonyms
    topic_terms = expand_with_synonyms(topic_words, topics_meta.get("synonyms", {}))
    # 3) fuzzy match over nodeids and filenames
    hits: Set[str] = set()
    basenames = [Path(n.split("::")[0]).name for n in nodeids]
    pairs = list(zip(nodeids, basenames))

    for t in topic_terms:
        hits |= fuzzy_filter([n for n, _ in pairs], t, threshold=fuzzy)
        hits |= fuzzy_filter([b for _, b in pairs], t, threshold=fuzzy)

    # 4) derive -k tokens (use leaf names + raw tokens)
    tokens = set(topic_terms)
    tokens |= {Path(h).name.split("::")[0].replace(".py", "") for h in hits}
    k_expr = build_k_expr(tokens)

    # 5) restrict paths to speed up; if no hits, default to test_core/tests
    paths = sorted({h.split("::")[0] for h in hits})
    if not paths:
        paths = ["test_core/tests"]
    return paths, k_expr, sorted(hits)
