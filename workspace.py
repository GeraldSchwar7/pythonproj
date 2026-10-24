import tkinter as tk
from settings import BG
from asset_browser import AssetBrowser
from display_panel import DisplayPanel
from tool_panel import ToolPanel
from timeline_panel import TimelinePanel
from layer_panel import LayerPanel

# ============================================================
# WORKSPACE
# ============================================================

class Workspace(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=BG
        )

        # Left column
        self.grid_columnconfigure(
            0,
            weight=1,
            minsize=220
        )

        # Main display / timeline
        self.grid_columnconfigure(
            1,
            weight=4
        )

        # Layer panel
        self.grid_columnconfigure(
            2,
            weight=1,
            minsize=220
        )

        # Display row
        self.grid_rowconfigure(
            0,
            weight=4
        )

        # Bottom editor row
        self.grid_rowconfigure(
            1,
            weight=2
        )

        # --------------------------------
        # Assets
        # --------------------------------

        self.assets = AssetBrowser(
            self
        )

        self.assets.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Display
        # --------------------------------

        self.display = DisplayPanel(
            self
        )

        self.display.grid(
            row=0,
            column=1,
            columnspan=2,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Tools
        # --------------------------------

        self.tools = ToolPanel(
            self
        )

        self.tools.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Timeline
        # --------------------------------

        self.timeline = TimelinePanel(
            self
        )

        self.timeline.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Layers
        # --------------------------------

        self.layers = LayerPanel(
            self
        )

        self.layers.grid(
            row=1,
            column=2,
            sticky="nsew",
            padx=3,
            pady=3
        )
