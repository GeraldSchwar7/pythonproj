import tkinter as tk
from settings import PANEL, BORDER, TEXT
from layer import Layer

# ============================================================
# LAYERS PANEL
# ============================================================

class LayerPanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.layers = []

        tk.Label(
            self,
            text="Layers",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        self.layer_list = tk.Listbox(
            self,
            bg="#181818",
            fg=TEXT,
            selectbackground="#094771",
            selectforeground=TEXT,
            borderwidth=0,
            highlightthickness=0
        )

        self.layer_list.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=5
        )

        controls = tk.Frame(
            self,
            bg=PANEL
        )

        controls.pack(
            fill="x",
            padx=8,
            pady=8
        )

        tk.Button(
            controls,
            text="+",
            width=3,
            command=self.create_layer
        ).pack(
            side="left"
        )

        tk.Button(
            controls,
            text="-",
            width=3,
            command=self.delete_selected_layer
        ).pack(
            side="left",
            padx=4
        )

        # Default layer structure from the sketch
        self.add_layer("Foreground")
        self.add_layer("Midground")
        self.add_layer("Background")

    def add_layer(self, name, image=None):

        layer = Layer(
            name,
            image
        )

        # Insert new layers at top
        self.layers.insert(
            0,
            layer
        )

        self.refresh()

    def create_layer(self):

        number = len(self.layers) + 1

        self.add_layer(
            f"Layer {number}"
        )

    def delete_selected_layer(self):

        selection = self.layer_list.curselection()

        if not selection:
            return

        index = selection[0]

        del self.layers[index]

        self.refresh()

    def refresh(self):

        self.layer_list.delete(
            0,
            tk.END
        )

        for layer in self.layers:

            visibility = "●" if layer.visible else "○"

            self.layer_list.insert(
                tk.END,
                f"{visibility}  {layer.name}"
            )
