from rich import box
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

PRIMARY_COLOR = "#0ea5e9"   # from design_tokens
DANGER_COLOR = "#ef4444"    # from design_tokens

def build_blast_meter(value: float, threshold: float) -> str:
    """
    Render a simple text meter like the one in your screenshot.

    value: current blast radius (e.g. 62.4)
    threshold: alert threshold (e.g. 50.0)
    """
    # clamp 0–100
    pct = max(0.0, min(100.0, value))
    width = 20
    filled = int(width * pct / 100.0)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct:0.2f}%"

def build_blast_panel(blast_row) -> Panel:
    """
    blast_row: a small dict or object with the fields we already print, e.g.:

        {
            "asset": "L - BLAST",
            "enc_pct": 62.40,
            "alert_pct": 50.00,
            "ldist": 1.88,
            "br": 5.00,
            "travel_pct": -20.00,
            "state": "BREACH",
            "meter_value": 62.40,     # or blast_radius["SOL"]
            "meter_threshold": 50.00, # your configured threshold
        }

    Returns a Rich Panel ready to drop into the layout.
    """

    table = Table(
        show_header=True,
        header_style=f"bold {PRIMARY_COLOR}",
        box=box.SIMPLE_HEAD,
        expand=True,
        pad_edge=False,
    )

    table.add_column("Asset", justify="left", style="bold")
    table.add_column("Enc%", justify="right")
    table.add_column("Alert%", justify="right")
    table.add_column("LDist", justify="right")
    table.add_column("BR", justify="right")
    table.add_column("Travel%", justify="right")
    table.add_column("State", justify="center")
    table.add_column("Meter", justify="right", no_wrap=True)

    # choose state color
    state = (blast_row.get("state") or "").upper()
    if state == "BREACH":
        state_style = f"bold {DANGER_COLOR}"
    elif state == "WARN":
        state_style = "bold yellow3"
    elif state == "OK":
        state_style = "bold green3"
    else:
        state_style = "bold grey50"

    travel_pct = blast_row.get("travel_pct", 0.0)
    travel_style = "green3" if travel_pct >= 0 else DANGER_COLOR

    meter_text = build_blast_meter(
        blast_row.get("meter_value", 0.0),
        blast_row.get("meter_threshold", 100.0),
    )

    table.add_row(
        blast_row.get("asset", ""),
        f"{blast_row.get('enc_pct', 0.0):0.2f}%",
        f"{blast_row.get('alert_pct', 0.0):0.2f}%",
        f"{blast_row.get('ldist', 0.0):0.2f}",
        f"{blast_row.get('br', 0.0):0.2f}",
        Text(f"{travel_pct:0.2f}%", style=travel_style),
        Text(state, style=state_style),
        meter_text,
    )

    panel = Panel(
        table,
        title=f"[bold {PRIMARY_COLOR}]🧨 Blast Radius 🧨[/]",
        border_style=PRIMARY_COLOR,
        padding=(0, 1),
    )

    return panel
