from .calc_services import CalcServices

class CalculationCore:
    """Minimal calculation core used for tests."""

    def __init__(self, data_locker=None):
        self.dl = data_locker
        self.calc_services = CalcServices()

    def get_travel_percent(self, position_type, entry_price, current_price, liquidation_price):
        try:
            entry_price = float(entry_price)
            current_price = float(current_price)
        except Exception:
            return 0.0
        if entry_price == 0:
            return 0.0
        if str(position_type).upper() == "LONG":
            movement = current_price - entry_price
        else:
            movement = entry_price - current_price
        return (movement / entry_price) * 100

    def get_heat_index(self, position):
        return abs(float(position.get("travel_percent", 0)))
