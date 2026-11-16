import tkinter as tk

from settings import BORDER, PANEL, TEXT_DIM, TEXT, FONT


class LayerEffectsPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        tk.Label(
            self,
            text="LAYER EFFECTS",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        self.selected_layer_label = tk.Label(
            self,
            text="No layer selected",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 10, "bold"),
            anchor="w"
        )
        self.selected_layer_label.pack(
            fill="x",
            padx=10,
            pady=(4, 8)
        )

        self.effects_container = tk.Frame(
            self,
            bg=PANEL
        )
        self.effects_container.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8
        )

        self.placeholder_label = tk.Label(
            self.effects_container,
            text="Select a layer to configure its effects.",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9),
            wraplength=190,
            justify="left"
        )
        self.placeholder_label.pack(
            anchor="nw"
        )

        self.selected_layer = None

    def set_layer(self, layer):
        self.selected_layer = layer
        self.selected_layer_label.configure(
            text=layer.name if layer is not None else "No layer selected"
        )
        self.placeholder_label.configure(
            text=(
                "No effects added yet. Layer effects can be managed here."
                if layer is not None
                else "Select a layer to configure its effects."
            )
        )
