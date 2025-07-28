from backend.models.monitor_status import MonitorType


def test_get_last_entry_accepts_enum(dl_tmp):
    dl_tmp.ledger.insert_ledger_entry("sonic_monitor", status="Success", metadata={})
    result = dl_tmp.ledger.get_last_entry(MonitorType.SONIC)
    assert result["status"] == "Success"
