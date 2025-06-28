from pathlib import Path
import re


def render_template_raw(name: str) -> str:
    base = Path(__file__).resolve().parents[2] / "templates"
    def load(fname: str) -> str:
        text = (base / fname).read_text(encoding="utf-8")
        return re.sub(r"{% include \"(.*?)\" %}", lambda m: load(m.group(1)), text)
    return load(name)


def test_risk_thresholds_section_present():
    html = render_template_raw("system/alert_thresholds.html")
    assert "Risk Monitor" in html
    assert "travelpercent" in html
