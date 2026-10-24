import tkinter as tk
from settings import PANEL, PANEL_LIGHT, BORDER, TEXT

# ============================================================
# TOOLS PANEL
# ============================================================

class ToolPanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.current_tool = "Select"

        tk.Label(
            self,
            text="Tools",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        tools = [
            "Select",
            "Move",
            "Copy",
            "Resize",
            "Cut",
            "Camera View"
        ]

        for tool in tools:

            button = tk.Button(
                self,
                text=tool,
                command=lambda t=tool: self.select_tool(t),
                bg=PANEL_LIGHT,
                fg=TEXT,
                activebackground=BORDER,
                activeforeground=TEXT,
                relief="flat"
            )

            button.pack(
                fill="x",
                padx=10,
                pady=3
            )

    def select_tool(self, tool):

        self.current_tool = tool

        print(
            "Selected tool:",
            tool
        )
