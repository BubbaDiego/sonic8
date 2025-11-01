"""
Funding snapshot service (Phase S-2).
"""
class FundingService:
    def __init__(self, rpc_client):
        self.rpc = rpc_client

    def snapshot(self):
        raise NotImplementedError("Phase S-2")
