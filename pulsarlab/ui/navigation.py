"""Matplotlib navigation toolbar that stays visible on PulsarLab's dark UI.

Matplotlib's Qt toolbar decides whether to draw its icons in black or white by
looking at the widget *palette* (the operating-system theme).  PulsarLab paints
its own dark theme with a Qt style sheet, which does **not** change the palette.
On a system in light mode (typical macOS default) the toolbar therefore drew
black icons on a near-black background and the zoom/pan/save buttons looked
missing.  This subclass pins a dark palette on the toolbar before the icons are
built so they are always rendered in the light foreground colour.
"""

from __future__ import annotations

from matplotlib.backends.backend_qt import NavigationToolbar2QT
from PySide6.QtGui import QColor, QPalette

from pulsarlab.visualization import theme as T


def dark_toolbar_palette() -> QPalette:
    palette = QPalette()
    background = QColor(T.BG)
    foreground = QColor(T.TEXT)
    for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Base, QPalette.ColorRole.Button):
        palette.setColor(role, background)
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        palette.setColor(role, foreground)
    return palette


class ThemedNavigationToolbar(NavigationToolbar2QT):
    """``NavigationToolbar2QT`` with icons independent of the OS theme."""

    def _icon(self, name):
        # Called by NavigationToolbar2QT.__init__ for every button, right after
        # QToolBar.__init__, so the palette is in place before the first icon.
        self.setPalette(dark_toolbar_palette())
        return super()._icon(name)
