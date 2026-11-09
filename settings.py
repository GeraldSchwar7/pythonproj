# ============================================================
# PROJECT MONDAY - VISUAL THEME
# ============================================================

# Surfaces
BG = "#0d0f12"
PANEL = "#15181d"
PANEL_LIGHT = "#20242b"
PANEL_HOVER = "#2a3039"
PANEL_DEEP = "#101216"
BORDER = "#2a2f38"
BORDER_ACTIVE = "#3d4653"

# Text
TEXT = "#f4f6f8"
TEXT_DIM = "#9aa3ad"
TEXT_MUTED = "#68717d"

# Accent / states
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9278ff"
ACCENT_SOFT = "#29223f"
SUCCESS = "#48c78e"
WARNING = "#f0b35a"
DANGER = "#ff5d6c"
PLAYHEAD = "#ff5d6c"

# Editor colors
CANVAS_BG = "#090b0e"
TRACK_A = "#111419"
TRACK_B = "#15191f"
VIDEO_CLIP = "#315f86"
IMAGE_CLIP = "#526b3e"

# Typography
FONT = "Segoe UI"
FONT_SIZE = 10
FONT_SMALL = 9
FONT_TITLE = 15
FONT_PANEL = 10

WINDOW_WIDTH = 1360
WINDOW_HEIGHT = 860


def configure_ttk(root):
    """Apply one consistent dark theme to ttk widgets."""
    from tkinter import ttk

    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "TCombobox",
        fieldbackground=PANEL_LIGHT,
        background=PANEL_LIGHT,
        foreground=TEXT,
        arrowcolor=TEXT_DIM,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        padding=5,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", PANEL_LIGHT)],
        foreground=[("readonly", TEXT)],
        selectbackground=[("readonly", PANEL_LIGHT)],
        selectforeground=[("readonly", TEXT)],
    )

    style.configure(
        "TNotebook",
        background=PANEL,
        borderwidth=0,
        tabmargins=(0, 0, 0, 0),
    )
    style.configure(
        "TNotebook.Tab",
        background=PANEL,
        foreground=TEXT_DIM,
        padding=(16, 8),
        borderwidth=0,
        font=(FONT, FONT_SMALL, "bold"),
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", PANEL_LIGHT), ("active", PANEL_HOVER)],
        foreground=[("selected", TEXT), ("active", TEXT)],
    )

    style.configure(
        "Vertical.TScrollbar",
        background=PANEL_LIGHT,
        troughcolor=PANEL_DEEP,
        bordercolor=PANEL_DEEP,
        arrowcolor=TEXT_DIM,
        width=11,
    )
    style.configure(
        "Horizontal.TScrollbar",
        background=PANEL_LIGHT,
        troughcolor=PANEL_DEEP,
        bordercolor=PANEL_DEEP,
        arrowcolor=TEXT_DIM,
        width=11,
    )


def flat_button(parent, text, command=None, accent=False, width=None):
    """Create a consistent Project Monday button."""
    import tkinter as tk

    bg = ACCENT if accent else PANEL_LIGHT
    active = ACCENT_HOVER if accent else PANEL_HOVER
    return tk.Button(
        parent,
        text=text,
        command=command,
        width=width,
        bg=bg,
        fg=TEXT,
        activebackground=active,
        activeforeground=TEXT,
        relief="flat",
        bd=0,
        highlightthickness=0,
        cursor="hand2",
        font=(FONT, FONT_SMALL, "bold"),
        padx=10,
        pady=6,
    )


def panel_title(parent, text):
    import tkinter as tk
    return tk.Label(
        parent,
        text=text.upper(),
        bg=PANEL,
        fg=TEXT_DIM,
        font=(FONT, FONT_SMALL, "bold"),
    )
