from pathlib import Path
from typing import Iterable, List, Dict, Tuple, Set
import subprocess

try:
    # Optional, faster fuzzy matching. Falls back to substring if missing.
    from rapidfuzz import fuzz, process
except Exception:  # pragma: no cover
    fuzz = None
    process = None


def collect_nodeids(pytest_args: List[str]) -> List[str]:
    """
    Return nodeids via `pytest --collect-only -q`.
    Example nodeid: test_core/tests/test_launch_pad_web.py::TestWeb::test_health
    """
    cmd = ["pytest", "--collect-only", "-q"] + pytest_args
    out = subprocess.run(cmd, capture_output=True, text=True, check=False)
    nodeids = []
    for line in out.stdout.splitlines():
        s = line.strip()
        if "::" in s or s.endswith(".py"):
            nodeids.append(s)
    return nodeids


def _fuzzy_candidates(cands: List[str], query: str, threshold: int) -> Set[str]:
    if not process:
        # Substring fallback
        q = query.lower()
        return {c for c in cands if q in c.lower()}

    matches = process.extract(query, cands, scorer=fuzz.WRatio, limit=None)
    return {cand for cand, score, _ in matches if score >= threshold}


def expand_with_synonyms(terms: Iterable[str], synonyms: Dict[str, List[str]]) -> List[str]:
    expanded = set()
    for t in terms:
        expanded.add(t)
        expanded.update(synonyms.get(t, []))
    return sorted(expanded)


def build_k_expr(tokens: Iterable[str]) -> str:
    toks = [t for t in set(tokens) if t]
    return " or ".join(sorted(toks))


def plan(
    topic_words: List[str],
    fuzzy: int,
    topics_meta: Dict,
    extra_paths: List[str]
) -> Tuple[List[str], str, List[str]]:
    """
    Returns:
      paths (list[str]): files to pass to pytest for faster discovery
      k_expr (str): pytest -k expression
      hits (list[str]): matching nodeids
    """
    nodeids = collect_nodeids(extra_paths)

    topic_terms = expand_with_synonyms(topic_words, topics_meta.get("synonyms", {}))

    # Match on nodeids and file basenames
    hits: Set[str] = set()
    basenames = [Path(n.split("::")[0]).name for n in nodeids]
    pairs = list(zip(nodeids, basenames))

    for t in topic_terms:
        hits.update(_fuzzy_candidates([n for n, _ in pairs], t, threshold=fuzzy))
        hits.update(_fuzzy_candidates([b for _, b in pairs], t, threshold=fuzzy))

    # Derive -k tokens from terms and matched filenames without .py
    tokens = set(topic_terms)
    tokens.update(Path(h.split("::")[0]).stem for h in hits)

    k_expr = build_k_expr(tokens)
    paths = sorted({h.split("::")[0] for h in hits})
    return paths, k_expr, sorted(hits)
