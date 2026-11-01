import tkinter as tk

from settings import BG

from asset_browser import (
    AssetBrowser
)

from display_panel import (
    DisplayPanel
)

from tool_panel import (
    ToolPanel
)

from timeline_panel import (
    TimelinePanel
)

from layer_panel import (
    LayerPanel
)


class Workspace(tk.Frame):

    def __init__(
        self,
        parent
    ):

        super().__init__(
            parent,
            bg=BG
        )

        # ==================================================
        # GRID
        # ==================================================

        # Assets / tools
        self.grid_columnconfigure(
            0,
            weight=1,
            minsize=220
        )

        # Main editor
        self.grid_columnconfigure(
            1,
            weight=4
        )

        # Layers
        self.grid_columnconfigure(
            2,
            weight=1,
            minsize=220
        )

        # Display
        self.grid_rowconfigure(
            0,
            weight=4
        )

        # Timeline / tools / layers
        self.grid_rowconfigure(
            1,
            weight=2
        )

        # ==================================================
        # DISPLAY
        # ==================================================

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

        # ==================================================
        # TIMELINE
        # ==================================================

        self.timeline = TimelinePanel(
            self,

            on_clip_added=
                self._on_clip_added,

            on_time_changed=
                self._on_time_changed
        )

        self.timeline.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # ==================================================
        # LAYERS
        # ==================================================

        self.layers = LayerPanel(
            self,

            on_layers_changed=
                self._on_layers_changed
        )

        self.layers.grid(
            row=1,
            column=2,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # ==================================================
        # ASSETS
        # ==================================================

        self.assets = AssetBrowser(
            self,

            on_asset_drop=
                self._on_asset_drop
        )

        self.assets.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # ==================================================
        # TOOLS
        # ==================================================

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

        # ==================================================
        # INITIAL SYNCHRONIZATION
        # ==================================================

        self._on_layers_changed(
            self.layers.layers
        )

        self.display.set_viewport_time(
            self.timeline.current_time
        )

    # ======================================================
    # LAYERS CHANGED
    # ======================================================

    def _on_layers_changed(
        self,
        layers
    ):

        if hasattr(
            self,
            "timeline"
        ):

            self.timeline.set_layers(
                layers
            )

        if hasattr(
            self,
            "display"
        ):

            self.display.set_viewport_layers(
                layers
            )

    # ======================================================
    # ASSET DROPPED
    # ======================================================

    def _on_asset_drop(
        self,
        file_path,
        x_root,
        y_root
    ):

        self.timeline.drop_asset_at_screen(
            file_path,
            x_root,
            y_root
        )

    # ======================================================
    # CLIP ADDED
    # ======================================================

    def _on_clip_added(
        self,
        layer,
        clip
    ):

        # Refresh the layer stack used by
        # the viewport.

        self.display.set_viewport_layers(
            self.layers.layers
        )

        # Render the current playhead time.
        self.display.set_viewport_time(
            self.timeline.current_time
        )

        # Automatically show the viewport
        # after dropping media.

        self.display.notebook.select(
            self.display.viewport_tab
        )

    # ======================================================
    # PLAYHEAD MOVED
    # ======================================================

    def _on_time_changed(
        self,
        current_time
    ):

        self.display.set_viewport_time(
            current_time
        )