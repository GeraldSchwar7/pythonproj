import tkinter as tk
from settings import (
    PANEL, PANEL_LIGHT, PANEL_HOVER, BORDER, TEXT, TEXT_DIM,
    ACCENT, ACCENT_SOFT, FONT, panel_title
)


class ToolPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.current_tool = "Select"
        self.buttons = {}

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", padx=12, pady=(10, 7))
        panel_title(header, "Tools").pack(side="left")
        tk.Label(header, text="EDIT", bg=PANEL, fg=TEXT_DIM, font=(FONT, 8)).pack(side="right")

        tools = [
            ("Select", "↖", "Choose clips and layers"),
            ("Move", "✥", "Move selected media"),
            ("Copy", "▣", "Duplicate selection"),
            ("Resize", "↔", "Scale selected media"),
            ("Cut", "✂", "Split at playhead"),
            ("Camera View", "◉", "Show camera monitor"),
        ]

        for name, icon, hint in tools:
            row = tk.Button(
                self,
                text=f"  {icon}    {name}",
                anchor="w",
                command=lambda t=name: self.select_tool(t),
                bg=PANEL,
                fg=TEXT_DIM,
                activebackground=PANEL_HOVER,
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                highlightthickness=0,
                cursor="hand2",
                font=(FONT, 9),
                padx=10,
                pady=8,
            )
            row.pack(fill="x", padx=8, pady=1)
            self.buttons[name] = row

        self._refresh_selection()

    def _refresh_selection(self):
        for name, button in self.buttons.items():
            selected = name == self.current_tool
            button.configure(
                bg=ACCENT_SOFT if selected else PANEL,
                fg=TEXT if selected else TEXT_DIM,
                activebackground=ACCENT_SOFT if selected else PANEL_HOVER,
            )

    def select_tool(self, tool):
        self.current_tool = tool
        self._refresh_selection()
        print("Selected tool:", tool)
