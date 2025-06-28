class HedgeCore:
    """Minimal hedge core used in tests."""

    def __init__(self, data_locker=None):
        self.dl = data_locker

    def link_hedges(self):
        return []

    def build_hedges(self):
        return []
