"""
Subsquid GraphQL client (Phase 1 stub).

Phase 3:
- positions, orders, and funding history
- pagination helpers
- reconciliation snapshots
"""
from typing import Dict, Any


class SubsquidClient:
    def __init__(self, graphql_url: str):
        self.graphql_url = graphql_url

    def query(self, q: str, variables: Dict[str, Any] | None = None) -> Dict[str, Any]:
        raise NotImplementedError("Phase 3")
