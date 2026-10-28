import tkinter as tk
from settings import PANEL, BORDER, TEXT

# ============================================================
# TIMELINE PANEL
# ============================================================

class TimelinePanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        header = tk.Frame(
            self,
            bg=PANEL
        )

        header.pack(
            fill="x"
        )

        tk.Label(
            header,
            text="Timeline",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            side="left",
            padx=10,
            pady=7
        )

        self.canvas = tk.Canvas(
            self,
            bg="#181818",
            highlightthickness=0
        )

        self.canvas.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        # Draw placeholder timeline tracks
        self.canvas.create_line(
            0,
            35,
            1000,
            35,
            fill=BORDER
        )

        self.canvas.create_line(
            0,
            70,
            1000,
            70,
            fill=BORDER
        )

        self.canvas.create_line(
            0,
            105,
            1000,
            105,
            fill=BORDER
        )
