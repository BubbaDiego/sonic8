from typing import Dict

from .oracle_data_service import OracleDataService
from backend.models.portfolio import PortfolioSnapshot


class PortfolioTopicHandler:
    """Provide portfolio context for GPT."""

    output_key = "portfolio"
    system_message = "You are a portfolio analysis assistant."

    def __init__(self, data_locker):
        self.data_service = OracleDataService(data_locker)

    def get_context(self) -> Dict:
        snapshot = self.data_service.fetch_portfolio()
        if isinstance(snapshot, PortfolioSnapshot):
            if hasattr(snapshot, "model_dump"):
                snapshot = snapshot.model_dump()
            elif hasattr(snapshot, "dict"):
                snapshot = snapshot.dict()
            else:
                snapshot = snapshot.__dict__
        return {self.output_key: snapshot}
