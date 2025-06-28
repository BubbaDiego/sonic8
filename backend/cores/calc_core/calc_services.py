class CalcServices:
    """Simple calculation utilities used in tests."""

    @staticmethod
    def calculate_leverage(size, collateral):
        try:
            collateral = float(collateral)
            size = float(size)
            return size / collateral if collateral else 0.0
        except Exception:
            return 0.0

    @staticmethod
    def calculate_liquid_distance(current_price, liquidation_price):
        try:
            current_price = float(current_price)
            liquidation_price = float(liquidation_price)
            if current_price == 0:
                return 0.0
            return abs(current_price - liquidation_price) / current_price
        except Exception:
            return 0.0

    def calculate_totals(self, positions):
        totals = {
            "total_size": 0.0,
            "total_value": 0.0,
            "total_collateral": 0.0,
            "avg_leverage": 0.0,
            "avg_travel_percent": 0.0,
            "avg_heat_index": 0.0,
        }
        if not positions:
            return totals
        count = 0
        for p in positions:
            count += 1
            totals["total_size"] += float(p.get("size", 0))
            totals["total_value"] += float(p.get("value", 0))
            totals["total_collateral"] += float(p.get("collateral", 0))
            totals["avg_leverage"] += float(p.get("leverage", 0))
            totals["avg_travel_percent"] += float(p.get("travel_percent", 0))
            totals["avg_heat_index"] += float(p.get("heat_index", 0))
        for key in ["avg_leverage", "avg_travel_percent", "avg_heat_index"]:
            totals[key] /= count
        return totals
