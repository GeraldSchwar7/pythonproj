import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
from settings import PANEL, PANEL_LIGHT, BORDER, TEXT, TEXT_DIM


# ============================================================
# DISPLAY PANEL
# Tabbed Camera View / Viewport display
# ============================================================

class DisplayPanel(tk.Frame):

    def __init__(self, parent):
        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.camera_window = None
        self.camera_window_display = None
        self.camera_display = None

        self._create_header()
        self._create_tabs()

    # --------------------------------------------------------
    # HEADER
    # --------------------------------------------------------

    def _create_header(self):
        title_bar = tk.Frame(self, bg=PANEL)
        title_bar.pack(fill="x")

        tk.Label(
            title_bar,
            text="Display",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=10, pady=7)

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    def _create_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        self.camera_tab = tk.Frame(self.notebook, bg=PANEL)
        self.viewport_tab = tk.Frame(self.notebook, bg=PANEL)

        self.notebook.add(self.camera_tab, text="Camera View")
        self.notebook.add(self.viewport_tab, text="Viewport")

        self._create_camera_tab()
        self._create_viewport_tab()

    # --------------------------------------------------------
    # CAMERA TAB
    # --------------------------------------------------------

    def _create_camera_tab(self):
        controls = tk.Frame(self.camera_tab, bg=PANEL)
        controls.pack(fill="x", padx=5, pady=5)

        self.pop_out_button = tk.Button(
            controls,
            text="Pop Out Camera View",
            command=self.pop_out_camera,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat"
        )
        self.pop_out_button.pack(side="right")

        self.camera_container = tk.Frame(self.camera_tab, bg="black")
        self.camera_container.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        self.camera_display = tk.Label(
            self.camera_container,
            bg="black"
        )
        self.camera_display.pack(fill="both", expand=True)

    # --------------------------------------------------------
    # VIEWPORT TAB
    # --------------------------------------------------------

    def _create_viewport_tab(self):
        # This is intentionally a separate surface from the camera feed.
        # Future viewport/rendering tools can be added here without
        # changing the camera code.
        self.viewport_display = tk.Frame(
            self.viewport_tab,
            bg="#181818"
        )
        self.viewport_display.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        tk.Label(
            self.viewport_display,
            text="Viewport",
            bg="#181818",
            fg=TEXT_DIM,
            font=("Segoe UI", 16, "bold")
        ).place(relx=0.5, rely=0.46, anchor="center")

        tk.Label(
            self.viewport_display,
            text="Viewport content will appear here.",
            bg="#181818",
            fg=TEXT_DIM,
            font=("Segoe UI", 10)
        ).place(relx=0.5, rely=0.53, anchor="center")

    # --------------------------------------------------------
    # POP OUT / ADD BACK
    # --------------------------------------------------------

    def pop_out_camera(self):
        if self.camera_window is not None and self.camera_window.winfo_exists():
            self.camera_window.lift()
            self.camera_window.focus_force()
            return

        # Hide the embedded camera widget while it lives in its own window.
        self.camera_container.pack_forget()
        self.pop_out_button.configure(state="disabled")

        self.camera_window = tk.Toplevel(self)
        self.camera_window.title("Project Monday - Camera View")
        self.camera_window.geometry("800x600")
        self.camera_window.minsize(400, 300)
        self.camera_window.configure(bg=PANEL)
        self.camera_window.protocol("WM_DELETE_WINDOW", self.add_camera_back)

        controls = tk.Frame(self.camera_window, bg=PANEL)
        controls.pack(fill="x")

        tk.Label(
            controls,
            text="Camera View",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=10, pady=7)

        tk.Button(
            controls,
            text="Add Back to Main Window",
            command=self.add_camera_back,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat"
        ).pack(side="right", padx=10, pady=5)

        self.camera_window_display = tk.Label(
            self.camera_window,
            bg="black"
        )
        self.camera_window_display.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

    def add_camera_back(self):
        if self.camera_window is not None:
            try:
                if self.camera_window.winfo_exists():
                    self.camera_window.destroy()
            except tk.TclError:
                pass

        self.camera_window = None
        self.camera_window_display = None

        # Restore the embedded camera surface in the Camera View tab.
        if self.camera_container.winfo_manager() == "":
            self.camera_container.pack(
                fill="both",
                expand=True,
                padx=5,
                pady=(0, 5)
            )

        self.pop_out_button.configure(state="normal")

    # --------------------------------------------------------
    # CAMERA FRAME DISPLAY
    # --------------------------------------------------------

    def display_frame(self, frame):
        target = self._get_camera_target()

        if target is None:
            return

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        width = target.winfo_width()
        height = target.winfo_height()

        if width <= 1 or height <= 1:
            return

        frame_height, frame_width = frame.shape[:2]

        # Preserve the camera aspect ratio.
        scale = min(
            width / frame_width,
            height / frame_height
        )

        new_width = max(1, int(frame_width * scale))
        new_height = max(1, int(frame_height * scale))

        frame = cv2.resize(frame, (new_width, new_height))
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image=image)

        # Tkinter must keep a Python reference to the PhotoImage.
        target.image = photo
        target.configure(image=photo)

    def _get_camera_target(self):
        if self.camera_window is not None:
            try:
                if self.camera_window.winfo_exists():
                    return self.camera_window_display
            except tk.TclError:
                self.camera_window = None
                self.camera_window_display = None

        return self.camera_display
