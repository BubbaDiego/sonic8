import builtins
import pytest

from test_core.formatter import grade_from_pct

@pytest.mark.parametrize("pct,expected", [
    (100, "A+"),
    (95, "A"),
    (85, "B"),
    (75, "C"),
    (65, "D"),
    (50, "F"),
])
def test_grade_from_pct(pct, expected):
    assert grade_from_pct(pct) == expected


