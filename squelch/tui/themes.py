"""
Custom themes for Squelch.

Add new themes here and they'll automatically appear in the command palette.
"""

from textual.theme import Theme


CHRISTMAS_THEME = Theme(
    name="christmas",
    primary="#c41e3a",  # Christmas red
    secondary="#1a472a",  # Christmas green
    accent="#ffd700",  # Gold
    foreground="#f5f5f5",  # Snow white
    background="#0c1911",  # Dark evergreen
    success="#228b22",  # Forest green
    warning="#ffd700",  # Gold
    error="#c41e3a",  # Red
    surface="#1a2f23",  # Dark green surface
    panel="#243d2e",  # Slightly lighter green
    dark=True,
)


ORANGE_THEME = Theme(
    name="orange",
    primary="#ff8c00",  # Orange - main UI color
    secondary="#e40303",  # Red - secondary elements
    accent="#ffed00",  # Yellow - highlights
    foreground="#ffffff",  # White text
    background="#1a0a0a",  # Very dark red/warm black
    success="#008026",  # Green
    warning="#ffed00",  # Yellow
    error="#e40303",  # Red
    surface="#2d1215",  # Dark warm surface
    panel="#3d1a1f",  # Warmer panel
    dark=True,
)


CUSTOM_THEMES = [
    CHRISTMAS_THEME,
    ORANGE_THEME,
]
