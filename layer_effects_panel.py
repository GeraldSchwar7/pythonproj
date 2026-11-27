import tkinter as tk

from settings import (
    BORDER,
    PANEL,
    PANEL_LIGHT,
    ACCENT,
    ACCENT_SOFT,
    TEXT_DIM,
    TEXT,
    FONT,
    flat_button,
    panel_title
)


class LayerEffectsPanel(tk.Frame):
    def __init__(
        self,
        parent,
        on_scene_separation=None,
        on_hue_saturation=None,
    ):
        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.on_scene_separation = on_scene_separation
        self.on_hue_saturation = on_hue_saturation

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", padx=13, pady=(12, 9))
        panel_title(header, "Inspector").pack(side="left")
        tk.Label(
            header,
            text="EFFECTS",
            bg=ACCENT_SOFT,
            fg=ACCENT,
            font=(FONT, 7, "bold"),
            padx=7,
            pady=3
        ).pack(side="right")

        tk.Label(
            self,
            text="ACTIVE LAYER",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 7, "bold")
        ).pack(anchor="w", padx=13, pady=(0, 5))

        self.selected_layer_label = tk.Label(
            self,
            text="No layer selected",
            bg=PANEL_LIGHT,
            fg=TEXT,
            font=(FONT, 10, "bold"),
            anchor="w",
            padx=10,
            pady=9,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.selected_layer_label.pack(
            fill="x",
            padx=13,
            pady=(0, 13)
        )

        tk.Label(
            self,
            text="QUICK ACTIONS",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 7, "bold")
        ).pack(anchor="w", padx=13, pady=(0, 6))

        flat_button(
            self,
            "Scene Separation",
            self._open_scene_separation
        ).pack(
            fill="x",
            padx=13,
            pady=(0, 7)
        )

        flat_button(
            self,
            "Hue/Saturation",
            self._open_hue_saturation
        ).pack(
            fill="x",
            padx=13,
            pady=(0, 7)
        )

        self.effects_container = tk.Frame(
            self,
            bg=PANEL
        )
        self.effects_container.pack(
            fill="both",
            expand=True,
            padx=13,
            pady=(8, 12)
        )

        self.placeholder_label = tk.Label(
            self.effects_container,
            text="Select a layer to explore its available effect controls.",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9),
            wraplength=190,
            justify="left",
            anchor="nw"
        )
        self.placeholder_label.pack(
            anchor="nw"
        )

        self.selected_layer = None

    def _open_scene_separation(self):
        if self.on_scene_separation is not None:
            self.on_scene_separation()

    def _open_hue_saturation(self):
        if self.on_hue_saturation is not None:
            self.on_hue_saturation()

    def set_layer(self, layer):
        self.selected_layer = layer
        self.selected_layer_label.configure(
            text=layer.name if layer is not None else "No layer selected"
        )
        self.placeholder_label.configure(
            text="" if layer is not None
            else "Select a layer to explore its available effect controls."
        )
