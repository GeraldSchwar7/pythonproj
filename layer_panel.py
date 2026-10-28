import tkinter as tk

from settings import PANEL, PANEL_LIGHT, BORDER, TEXT
from layer import Layer


class LayerPanel(tk.Frame):

    def __init__(self, parent, on_layers_changed=None):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.layers = []

        # Callback used to tell Workspace that layers changed.
        self.on_layers_changed = on_layers_changed

        # --------------------------------------------------
        # TITLE
        # --------------------------------------------------

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

        # --------------------------------------------------
        # LAYER LIST
        # --------------------------------------------------

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

        # NEW:
        # Double-click a layer to rename it.
        self.layer_list.bind(
            "<Double-Button-1>",
            self.rename_selected_layer
        )

        # --------------------------------------------------
        # CONTROLS
        # --------------------------------------------------

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

        # Optional explicit rename button
        tk.Button(
            controls,
            text="Rename",
            command=self.rename_selected_layer
        ).pack(
            side="left",
            padx=4
        )

        # --------------------------------------------------
        # DEFAULT LAYERS
        # --------------------------------------------------

        self.add_layer("Foreground")
        self.add_layer("Midground")
        self.add_layer("Background")

    # ======================================================
    # ADD LAYER
    # ======================================================

    def add_layer(self, name, image=None):

        layer = Layer(
            name,
            image
        )

        # New layers appear at the top.
        self.layers.insert(
            0,
            layer
        )

        self.refresh()
        self.notify_layers_changed()

    # ======================================================
    # CREATE LAYER
    # ======================================================

    def create_layer(self):

        number = len(self.layers) + 1

        self.add_layer(
            f"Layer {number}"
        )

    # ======================================================
    # DELETE LAYER
    # ======================================================

    def delete_selected_layer(self):

        selection = self.layer_list.curselection()

        if not selection:
            return

        index = selection[0]

        del self.layers[index]

        self.refresh()
        self.notify_layers_changed()

    # ======================================================
    # RENAME LAYER
    # ======================================================

    def rename_selected_layer(self, event=None):

        selection = self.layer_list.curselection()

        if not selection:
            return

        index = selection[0]

        layer = self.layers[index]

        # Find where the selected layer is located
        # inside the Listbox.
        bbox = self.layer_list.bbox(index)

        if bbox is None:
            return

        x, y, width, height = bbox

        # --------------------------------------------------
        # Temporary rename text field
        # --------------------------------------------------

        rename_entry = tk.Entry(
            self.layer_list,
            bg=PANEL_LIGHT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat"
        )

        # Start with the current layer name.
        rename_entry.insert(
            0,
            layer.name
        )

        # Put the Entry over the Listbox row.
        rename_entry.place(
            x=25,
            y=y,
            width=max(
                50,
                self.layer_list.winfo_width() - 30
            ),
            height=height
        )

        rename_entry.focus_set()

        # Highlight the existing name so typing
        # immediately replaces it.
        rename_entry.select_range(
            0,
            tk.END
        )

        # --------------------------------------------------
        # Finish rename
        # --------------------------------------------------

        def finish_rename(event=None):

            new_name = rename_entry.get().strip()

            if new_name:
                layer.name = new_name

            rename_entry.destroy()

            # Update Layers panel.
            self.refresh()

            # Tell Timeline/Workspace that the
            # layer information changed.
            self.notify_layers_changed()

        # Enter accepts the new name.
        rename_entry.bind(
            "<Return>",
            finish_rename
        )

        # Clicking somewhere else also accepts it.
        rename_entry.bind(
            "<FocusOut>",
            finish_rename
        )

    # ======================================================
    # REFRESH DISPLAY
    # ======================================================

    def refresh(self):

        self.layer_list.delete(
            0,
            tk.END
        )

        for layer in self.layers:

            visibility = (
                "●"
                if layer.visible
                else "○"
            )

            self.layer_list.insert(
                tk.END,
                f"{visibility}  {layer.name}"
            )

    # ======================================================
    # NOTIFY WORKSPACE
    # ======================================================

    def notify_layers_changed(self):

        if self.on_layers_changed is not None:

            self.on_layers_changed(
                self.layers
            )