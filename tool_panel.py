import tkinter as tk
from settings import (
    PANEL, PANEL_LIGHT, PANEL_HOVER, BORDER, TEXT, TEXT_DIM,
    ACCENT, ACCENT_HOVER, ACCENT_SOFT, BG, FONT, panel_title
)


class ToolPanel(tk.Frame):
    def __init__(self, parent, on_tool_selected=None):
        super().__init__(
            parent,
            bg=PANEL_LIGHT,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        self.current_tool = "Select"
        self.on_tool_selected = on_tool_selected
        self.buttons = {}

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", padx=13, pady=(12, 8))
        panel_title(header, "Toolbox").pack(side="left")
        tk.Label(
            header,
            text="GESTURE MODE",
            bg=ACCENT_SOFT,
            fg=ACCENT,
            font=(FONT, 7, "bold"),
            padx=7,
            pady=3
        ).pack(side="right")

        tk.Label(
            self,
            text="Hold a gesture for 2 seconds to activate",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 8)
        ).pack(anchor="w", padx=13, pady=(0, 7))

        tools = [
            ("Select", "↖", "🤙", "Choose clips and layers (ASL Y)"),
            ("Move", "✥", "✊", "Move selected media"),
            ("Copy", "▣", "C", "Copy selected clip"),
            ("Paste", "▤", "👌", "Paste copied clip at the timeline cursor"),
            ("Resize", "↔", "🤞", "Scale selected media"),
            ("Cut", "✂", "✌", "Split the clip at the clicked timeline time"),
            ("Camera View", "◉", "", "Show camera monitor"),
        ]

        for name, icon, gesture, hint in tools:
            row = tk.Button(
                self,
                text=f"{icon}   {name}   {gesture}",
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
                font=("Segoe UI Emoji", 9, "bold"),
                padx=12,
                pady=6,
            )
            row.pack(fill="x", padx=8, pady=2)
            self.buttons[name] = row

        self._refresh_selection()

    def _refresh_selection(self):
        for name, button in self.buttons.items():
            selected = name == self.current_tool
            button.configure(
                bg=ACCENT if selected else PANEL_LIGHT,
                fg=BG if selected else TEXT_DIM,
                activebackground=(
                    ACCENT_HOVER if selected else PANEL_HOVER
                ),
                activeforeground=BG if selected else TEXT,
                highlightbackground=(
                    ACCENT if selected else BORDER
                ),
                highlightcolor=ACCENT,
                highlightthickness=1,
            )

    def select_tool(self, tool):
        self.current_tool = tool
        self._refresh_selection()
        if self.on_tool_selected is not None:
            self.on_tool_selected(tool)
        print("Selected tool:", tool)


    def activate_tool(
        self,
        tool_name
    ):

        self.current_tool = tool_name

        # Use your existing selection method if you
        # already have one.
        self.select_tool(
            tool_name
        )
