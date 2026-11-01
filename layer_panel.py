import tkinter as tk

from settings import (
    PANEL,
    PANEL_LIGHT,
    BORDER,
    TEXT
)

from layer import Layer


class LayerPanel(tk.Frame):

    def __init__(
        self,
        parent,
        on_layers_changed=None
    ):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        # ==================================================
        # DATA
        # ==================================================

        self.layers = []

        self.on_layers_changed = (
            on_layers_changed
        )

        # ==================================================
        # TITLE
        # ==================================================

        tk.Label(
            self,
            text="Layers",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        # ==================================================
        # LAYER LIST
        # ==================================================

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

        # Double-click to rename.
        self.layer_list.bind(
            "<Double-Button-1>",
            self.rename_selected_layer
        )

        # ==================================================
        # CONTROLS
        # ==================================================

        controls = tk.Frame(
            self,
            bg=PANEL
        )

        controls.pack(
            fill="x",
            padx=8,
            pady=8
        )

        # Add
        tk.Button(
            controls,
            text="+",
            width=3,
            command=self.create_layer,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat"
        ).pack(
            side="left"
        )

        # Delete
        tk.Button(
            controls,
            text="-",
            width=3,
            command=self.delete_selected_layer,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat"
        ).pack(
            side="left",
            padx=4
        )

        # Rename
        tk.Button(
            controls,
            text="Rename",
            command=self.rename_selected_layer,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat"
        ).pack(
            side="left",
            padx=4
        )

        # ==================================================
        # DEFAULT LAYERS
        # ==================================================

        self.add_layer(
            "Foreground",
            notify=False
        )

        self.add_layer(
            "Midground",
            notify=False
        )

        self.add_layer(
            "Background",
            notify=False
        )

        self.notify_layers_changed()

    # ======================================================
    # ADD LAYER
    # ======================================================

    def add_layer(
        self,
        name,
        notify=True
    ):

        layer = Layer(
            name
        )

        # New layers appear at the top.
        self.layers.insert(
            0,
            layer
        )

        self.refresh()

        if notify:
            self.notify_layers_changed()

        return layer

    # ======================================================
    # CREATE LAYER
    # ======================================================

    def create_layer(self):

        number = (
            len(self.layers)
            + 1
        )

        self.add_layer(
            f"Layer {number}"
        )

    # ======================================================
    # DELETE LAYER
    # ======================================================

    def delete_selected_layer(self):

        selection = (
            self.layer_list.curselection()
        )

        if not selection:
            return

        index = selection[0]

        del self.layers[index]

        self.refresh()

        self.notify_layers_changed()

    # ======================================================
    # RENAME LAYER
    # ======================================================

    def rename_selected_layer(
        self,
        event=None
    ):

        selection = (
            self.layer_list.curselection()
        )

        if not selection:
            return

        index = selection[0]

        layer = self.layers[index]

        bbox = self.layer_list.bbox(
            index
        )

        if bbox is None:
            return

        x, y, width, height = bbox

        # ==================================================
        # RENAME ENTRY
        # ==================================================

        rename_entry = tk.Entry(
            self.layer_list,
            bg=PANEL_LIGHT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat"
        )

        rename_entry.insert(
            0,
            layer.name
        )

        rename_entry.place(
            x=25,
            y=y,
            width=max(
                50,
                self.layer_list.winfo_width()
                - 30
            ),
            height=height
        )

        rename_entry.focus_set()

        rename_entry.select_range(
            0,
            tk.END
        )

        rename_finished = False

        # ==================================================
        # FINISH
        # ==================================================

        def finish_rename(
            event=None
        ):

            nonlocal rename_finished

            if rename_finished:
                return

            rename_finished = True

            new_name = (
                rename_entry
                .get()
                .strip()
            )

            if new_name:

                layer.name = (
                    new_name
                )

            rename_entry.destroy()

            self.refresh()

            self.notify_layers_changed()

        # ==================================================
        # CANCEL
        # ==================================================

        def cancel_rename(
            event=None
        ):

            nonlocal rename_finished

            if rename_finished:
                return

            rename_finished = True

            rename_entry.destroy()

            self.refresh()

        rename_entry.bind(
            "<Return>",
            finish_rename
        )

        rename_entry.bind(
            "<FocusOut>",
            finish_rename
        )

        rename_entry.bind(
            "<Escape>",
            cancel_rename
        )

    # ======================================================
    # REFRESH
    # ======================================================

    def refresh(self):

        selection = (
            self.layer_list.curselection()
        )

        selected_index = None

        if selection:

            selected_index = (
                selection[0]
            )

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

        # Restore previous selection.
        if (
            selected_index
            is not None
            and selected_index
            < len(self.layers)
        ):

            self.layer_list.selection_set(
                selected_index
            )

            self.layer_list.activate(
                selected_index
            )

    # ======================================================
    # NOTIFY WORKSPACE
    # ======================================================

    def notify_layers_changed(self):

        if (
            self.on_layers_changed
            is not None
        ):

            self.on_layers_changed(
                self.layers
            )