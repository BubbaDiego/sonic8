import json, os, subprocess, sys, shutil
from typing import Any, Dict

NODE_BIN = os.getenv("NODE_BIN", "node")
REPO_PERPS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "jupiter-perps-anchor-idl-parsing"))
CLI_PATH = os.path.join(REPO_PERPS, "dist", "cli", "perps.js")

class PerpsCLIError(RuntimeError):
    def __init__(self, msg:str, payload:Dict[str,Any]|None=None):
        super().__init__(msg)
        self.payload = payload or {}

def _ensure_cli():
    if not shutil.which(NODE_BIN):
        raise PerpsCLIError("node not found in PATH; set NODE_BIN")
    if not os.path.isfile(CLI_PATH):
        raise PerpsCLIError(f"perps CLI not built at {CLI_PATH}. Run `npm run build` in the TS repo.")

def run_cli(command: str, payload: Dict[str, Any], timeout_sec: int = 20) -> Dict[str, Any]:
    _ensure_cli()
    proc = subprocess.Popen(
        [NODE_BIN, CLI_PATH, command],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=REPO_PERPS
    )
    try:
        out, err = proc.communicate(json.dumps(payload), timeout=timeout_sec)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise PerpsCLIError(f"CLI timeout after {timeout_sec}s", {"command": command})
    if err:
        # pretty debug from CLI arrives on stderr; forward to our console
        sys.stderr.write(err)

    try:
        data = json.loads(out) if out else {}
    except Exception as e:
        raise PerpsCLIError(f"CLI returned non-JSON: {e}", {"stdout": out, "stderr": err})

    if proc.returncode != 0 or not data.get("ok", False):
        raise PerpsCLIError("CLI reported failure", data)
    return data
