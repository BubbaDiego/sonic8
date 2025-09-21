from typing import Any, Dict
from .cli_client import run_cli, PerpsCLIError as _PerpsCLIError

PerpsCLIError = _PerpsCLIError


def dry_run_increase(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    payload: matches the IncreaseInput JSON expected by the CLI.
    We deliberately do *not* read or mutate .env here. Caller must pass rpcUrl etc. if needed.
    """
    # guardrails: you control secrets/config outside this function
    data = run_cli("dry-run:increase", payload)
    return data
