
from __future__ import annotations
from typing import Callable
from .repository import AlertRepo
from .services.evaluation import evaluate
from .models import AlertState, AlertEvent

class MetricFeedAdapter:
    def __init__(self, metric_fn: Callable):
        self.metric_fn = metric_fn  # metric_fn(cfg) -> float

    def metric_for_alert(self, cfg):
        return self.metric_fn(cfg)

class NotificationRouter:
    def __init__(self, send_fn: Callable[[AlertEvent], None]):
        self.send_fn = send_fn

    def dispatch(self, event: AlertEvent):
        self.send_fn(event)

class AlertOrchestrator:
    def __init__(self, repo: AlertRepo, metrics: MetricFeedAdapter, router: NotificationRouter):
        self.repo = repo
        self.metrics = metrics
        self.router = router

    def run_cycle(self):
        for cfg, state in self.repo.iter_alerts_with_state():
            metric_value = self.metrics.metric_for_alert(cfg)
            th = self.repo.thresholds_for(cfg.alert_type, cfg.alert_class, cfg.condition)
            if th is None:
                continue
            new_state, event = evaluate(cfg, state, metric_value, th)
            self.repo.save_state(new_state)
            if event:
                self.repo.add_event(event)
                self.router.dispatch(event)
