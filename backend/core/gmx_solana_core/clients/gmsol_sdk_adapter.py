"""
Optional SDK adapter placeholder.

If you decide to run an external Node/Rust microservice using the official
GMX-Solana SDK, place client glue here. Phase S-1 leaves this file as a stub.
"""
class GmsolSdkAdapter:
    def __init__(self, url: str):
        self.url = url

    def get_markets(self):
        raise NotImplementedError("Optional adapter to SDK; implement if you run a separate service.")
