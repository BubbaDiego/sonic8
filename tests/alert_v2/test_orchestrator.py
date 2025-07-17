from backend.alert_v2 import AlertRepo
from backend.alert_v2.orchestrator import AlertOrchestrator, MetricFeedAdapter, NotificationRouter
from backend.alert_v2.models import AlertConfig, Condition, Threshold, AlertLevel

class DummyRepo(AlertRepo):
    def __init__(self):
        super().__init__()
        self.events = []

    def add_event(self, ev):
        super().add_event(ev)
        self.events.append(ev)


def test_orchestrator_creates_event(tmp_path, monkeypatch):
    monkeypatch.setenv("MOTHER_DB_PATH", str(tmp_path / "test.db"))
    repo = DummyRepo()
    repo.ensure_schema()
    cfg = AlertConfig(id="a1", alert_type="Price", alert_class="Position", trigger_value=0, condition=Condition.ABOVE)
    repo.add_config(cfg)
    th = Threshold(id="t1", alert_type="Price", alert_class="Position", metric_key="price", condition=Condition.ABOVE, low=1, medium=2, high=3)
    repo.add_threshold(th)

    metrics = MetricFeedAdapter(metric_fn=lambda c: 5)
    router = NotificationRouter(send_fn=lambda ev: None)
    orch = AlertOrchestrator(repo, metrics, router)

    orch.run_cycle()

    assert repo.events
    assert repo.events[0].level == AlertLevel.HIGH
