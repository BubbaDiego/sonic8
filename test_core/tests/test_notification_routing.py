from alert_core.infrastructure.notifiers import default_router, SMSNotifier, WindowsToastNotifier


def test_default_router_contains_notifiers():
    router = default_router()
    assert any(isinstance(n, SMSNotifier) for n in router)
    assert any(isinstance(n, WindowsToastNotifier) for n in router)
