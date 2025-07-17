from backend.alert_v2 import AlertRepo
from backend.alert_v2.models import Threshold, Condition
from backend.core.constants import MOTHER_DB_PATH


def main(db_path=str(MOTHER_DB_PATH)):
    repo = AlertRepo()
    repo.ensure_schema()
    repo.add_threshold(
        Threshold(
            id="th_btc_travel",
            alert_type="TravelPercent",
            alert_class="Position",
            metric_key="travel_percent",
            condition=Condition.ABOVE,
            low=50,
            medium=70,
            high=90,
        )
    )


if __name__ == "__main__":
    main()
