import tkinter as tk

from settings import BG, BORDER

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

from layer_effects_panel import (
    LayerEffectsPanel
)

from scene_separation import SceneSeparationWindow
from media_clip import MediaClip
from layer import Layer


def _create_paned_window(parent, orient):
    return tk.PanedWindow(
        parent,
        orient=orient,
        # Defer panel reflow until release to avoid redraw artifacts.
        opaqueresize=False,
        background=BORDER,
        borderwidth=0,
        relief="flat",
        sashwidth=6,
        sashrelief="flat",
    )


class Workspace(tk.Frame):

    def __init__(
        self,
        parent,
        on_status=None,
        on_hand_control_toggle=None,
        on_calibrate=None,
        viewport_resolution=(1920, 1080),
    ):

        super().__init__(
            parent,
            bg=BG
        )

        self.on_status = on_status
        self.scene_separation_windows = []
        self._initial_sashes_set = False
        self._initial_sash_job = None

        self.column_panes = _create_paned_window(
            self,
            tk.HORIZONTAL,
        )
        self.column_panes.pack(fill="both", expand=True)

        self.left_panes = _create_paned_window(
            self.column_panes,
            tk.VERTICAL,
        )
        self.editor_panes = _create_paned_window(
            self.column_panes,
            tk.VERTICAL,
        )
        self.timeline_panes = _create_paned_window(
            self.editor_panes,
            tk.HORIZONTAL,
        )
        self.left_assets_container = tk.Frame(self.left_panes, bg=BG)
        self.left_tools_container = tk.Frame(self.left_panes, bg=BG)
        self.display_container = tk.Frame(self.editor_panes, bg=BG)
        self.left_assets_container.pack_propagate(False)
        self.left_tools_container.pack_propagate(False)
        self.display_container.pack_propagate(False)
        self.column_panes.add(
            self.left_panes,
            minsize=205,
            stretch="always",
        )
        self.column_panes.add(
            self.editor_panes,
            minsize=591,
            stretch="always",
        )
        self.left_panes.add(
            self.left_assets_container,
            minsize=150,
            stretch="always",
        )
        self.left_panes.add(
            self.left_tools_container,
            minsize=180,
            stretch="always",
        )
        self.editor_panes.add(
            self.display_container,
            minsize=220,
            stretch="always",
        )
        self.editor_panes.add(
            self.timeline_panes,
            minsize=210,
            stretch="always",
        )

        # ==================================================
        # DISPLAY
        # ==================================================

        self.display = DisplayPanel(
            self.display_container,
            viewport_resolution=viewport_resolution,
        )

        self.display.pack(
            fill="both",
            expand=True,
            padx=7,
            pady=7,
        )

        # ==================================================
        # TIMELINE
        # ==================================================

        self.timeline_container = tk.Frame(self.timeline_panes, bg=BG)
        self.timeline = TimelinePanel(
            self.timeline_container,

            on_clip_added=
                self._on_clip_added,

            on_time_changed=
                self._on_time_changed,

            on_timeline_changed=
                self._on_timeline_changed,

            on_layer_selected=
                self._on_layer_selected,

            on_status=
                on_status,

            on_hand_control_toggle=
                on_hand_control_toggle,

            on_calibrate=
                on_calibrate
        )

        self.timeline_container.pack_propagate(False)
        self.timeline.pack(
            fill="both",
            expand=True,
            padx=7,
            pady=(0, 7),
        )
        self.timeline_panes.add(
            self.timeline_container,
            minsize=380,
            stretch="always",
        )

        # ==================================================
        # LAYER EFFECTS
        # ==================================================

        self.layer_effects_container = tk.Frame(self.timeline_panes, bg=BG)
        self.layer_effects = LayerEffectsPanel(
            self.layer_effects_container,
            on_scene_separation=self._open_scene_separation,
            on_hue_saturation=self._open_hue_saturation,
        )

        self.layer_effects_container.pack_propagate(False)
        self.layer_effects.pack(
            fill="both",
            expand=True,
            padx=7,
            pady=(0, 7),
        )
        self.timeline_panes.add(
            self.layer_effects_container,
            minsize=205,
            stretch="always",
        )

        # ==================================================
        # ASSETS
        # ==================================================

        self.assets = AssetBrowser(
            self.left_assets_container,

            on_asset_drop=
                self._on_asset_drop
        )

        self.assets.pack(
            fill="both",
            expand=True,
            padx=7,
            pady=7,
        )

        # ==================================================
        # TOOLS
        # ==================================================

        self.tools = ToolPanel(
            self.left_tools_container,
            on_tool_selected=self._on_tool_selected
        )

        self.tools.pack(
            fill="both",
            expand=True,
            padx=7,
            pady=(0, 7),
        )

        self.bind("<Configure>", self._schedule_initial_sashes, add="+")

        # ==================================================
        # INITIAL SYNCHRONIZATION
        # ==================================================

        self.display.set_viewport_layers(
            self.timeline.layers
        )
        self.layer_effects.set_layer(
            self.timeline.selected_layer
        )

        self.display.set_viewport_time(
            self.timeline.current_time
        )

    def _schedule_initial_sashes(self, event):
        if event.widget is self and not self._initial_sashes_set:
            if self._initial_sash_job is not None:
                self.after_cancel(self._initial_sash_job)
            self._initial_sash_job = self.after(
                50,
                self._set_initial_sash_positions,
            )

    def _set_initial_sash_positions(self):
        self._initial_sash_job = None
        self._initial_sashes_set = True
        workspace_width = self.column_panes.winfo_width()
        workspace_height = self.column_panes.winfo_height()
        if workspace_width <= 1 or workspace_height <= 1:
            return

        available_width = workspace_width - 6
        extra_width = max(0, available_width - 796)
        left_width = 205 + extra_width / 7
        self.column_panes.sash_place(0, int(left_width), 0)
        self.update_idletasks()

        bottom_width = max(0, self.timeline_panes.winfo_width() - 6)
        timeline_extra = max(0, bottom_width - 585)
        self.timeline_panes.sash_place(
            0,
            int(380 + timeline_extra * 5 / 6),
            0,
        )

        vertical_position = int((workspace_height - 6) * 4 / 6)
        self.left_panes.sash_place(0, 0, vertical_position)
        self.editor_panes.sash_place(0, 0, vertical_position)

    def _on_tool_selected(self, tool_name):
        self.timeline.set_tool(tool_name)
        instructions = {
            "Copy": "Copy: click a timeline clip",
            "Cut": "Cut: click the clip where it should split",
            "Paste": "Paste: click a timeline track to place the copied clip"
        }
        message = instructions.get(tool_name)
        if message is not None and self.on_status is not None:
            self.on_status(message)

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
            self.timeline.layers
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

    def _on_layer_selected(self, layer):
        self.layer_effects.set_layer(layer)

    def _open_hue_saturation(self):
        if self.timeline.selected_clip is None:
            return

        window = tk.Toplevel(self)
        window.title("Hue/Saturation")
        window.geometry("400x300")
        window.minsize(300, 200)
        window.transient(self.winfo_toplevel())
        window.protocol(
            "WM_DELETE_WINDOW",
            window.destroy,
        )

    def _open_scene_separation(self):
        selected_clip = self.timeline.selected_clip
        if selected_clip is None:
            return

        selected_layer = self.timeline.selected_clip_layer
        original_layer_name = (
            selected_layer.name
            if selected_layer is not None
            else "Layer"
        )

        window = SceneSeparationWindow(
            self,
            selected_clip,
            self.timeline.current_time,
            original_layer_name,
            on_add_layers=lambda layers: self._add_scene_separation_layers(
                selected_clip,
                layers,
            ),
        )
        self.scene_separation_windows.append(window)

        def close_scene_separation():
            if window in self.scene_separation_windows:
                self.scene_separation_windows.remove(window)
            window._close()

        window.protocol("WM_DELETE_WINDOW", close_scene_separation)

    def _add_scene_separation_layers(self, source_clip, exported_layers):
        for layer_name, image_path in exported_layers:
            layer = Layer(layer_name)
            segment_clip = MediaClip(
                image_path,
                start_time=source_clip.start_time,
                duration=source_clip.duration,
            )
            layer.add_clip(segment_clip)
            self.timeline.layers.insert(0, layer)

        if exported_layers:
            self.timeline.timeline_duration = max(
                self.timeline.timeline_duration,
                source_clip.end_time,
            )
            self.timeline.redraw()
            self.timeline._notify_timeline_changed()
            self._on_timeline_changed()

    # ======================================================
    # TIMELINE ARRANGEMENT CHANGED
    # ======================================================

    def _on_timeline_changed(
        self
    ):

        self.display.set_viewport_layers(
            self.timeline.layers
        )

        self.display.set_viewport_time(
            self.timeline.current_time
        )

        self.layer_effects.set_layer(
            self.timeline.selected_layer
        )