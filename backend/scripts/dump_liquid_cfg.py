from backend.data.data_locker import DataLocker
from backend.core.core_constants import MOTHER_DB_PATH
import json


dl = DataLocker.get_instance(str(MOTHER_DB_PATH))
cfg = dl.system.get_var("liquid_monitor") or {}
print(json.dumps(cfg, indent=2))
print("\n— notifications —")
print(json.dumps(cfg.get("notifications") or {}, indent=2))
