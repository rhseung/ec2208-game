from __future__ import annotations

from textual.widgets import Static


class SidePanel(Static):
    DEFAULT_CSS = """
    SidePanel {
        width: 40;
        height: 1fr;
        border: solid $primary;
        padding: 1 1;
    }
    """


class MessagePanel(Static):
    DEFAULT_CSS = """
    MessagePanel {
        height: 10;
        border: solid $secondary;
        padding: 1 2;
    }
    """
