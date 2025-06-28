"""Minimal fuzzy matching utilities for tests."""

def fuzzy_match_key(key, choices, threshold=0.0):
    """Return the closest key from choices based on simple equality check."""
    key = str(key).upper()
    for choice in choices:
        if key == choice.upper():
            return choice
    return None
