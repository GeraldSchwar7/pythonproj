import tkinter as tk
from settings import BG
from asset_browser import AssetBrowser
from display_panel import DisplayPanel
from tool_panel import ToolPanel
from timeline_panel import TimelinePanel
from layer_panel import LayerPanel

class Workspace(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)

        self.grid_columnconfigure(0, weight=1, minsize=220)
        self.grid_columnconfigure(1, weight=4)
        self.grid_columnconfigure(2, weight=1, minsize=220)
        self.grid_rowconfigure(0, weight=4)
        self.grid_rowconfigure(1, weight=2)

        self.display = DisplayPanel(self)
        self.display.grid(row=0, column=1, columnspan=2, sticky="nsew", padx=3, pady=3)

        self.timeline = TimelinePanel(self, on_clip_added=self._on_clip_added)
        self.timeline.grid(row=1, column=1, sticky="nsew", padx=3, pady=3)

        self.layers = LayerPanel(self, on_layers_changed=self._on_layers_changed)
        self.layers.grid(row=1, column=2, sticky="nsew", padx=3, pady=3)

        self.assets = AssetBrowser(self, on_asset_drop=self._on_asset_drop)
        self.assets.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        self.tools = ToolPanel(self)
        self.tools.grid(row=1, column=0, sticky="nsew", padx=3, pady=3)

        # LayerPanel creates its defaults before the callback can see the
        # completed Workspace, so perform one explicit initial sync.
        self._on_layers_changed(self.layers.layers)

    def _on_layers_changed(self, layers):
        if hasattr(self, "timeline"):
            self.timeline.set_layers(layers)
        if hasattr(self, "display"):
            self.display.set_viewport_layers(layers)

    def _on_asset_drop(self, file_path, x_root, y_root):
        self.timeline.drop_asset_at_screen(file_path, x_root, y_root)

    def _on_clip_added(self, layer, file_path):
        self.display.set_viewport_layers(self.layers.layers)
        # Automatically reveal the result of a successful timeline drop.
        self.display.notebook.select(self.display.viewport_tab)
