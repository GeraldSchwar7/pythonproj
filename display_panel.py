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
        self.viewport_canvas = tk.Canvas(
            self.viewport_tab,
            bg="#181818",
            highlightthickness=0
        )
        self.viewport_canvas.pack(fill="both", expand=True, padx=5, pady=5)
        self.viewport_canvas.bind("<Configure>", lambda event: self.render_viewport())
        self.viewport_layers = []
        self.viewport_photos = []

    def set_viewport_layers(self, layers):
        self.viewport_layers = layers
        self.render_viewport()

    def render_viewport(self):
        if not hasattr(self, "viewport_canvas"):
            return

        self.viewport_canvas.delete("all")
        self.viewport_photos.clear()
        width = self.viewport_canvas.winfo_width()
        height = self.viewport_canvas.winfo_height()
        if width <= 1 or height <= 1:
            return

        visible_media = [
            layer for layer in reversed(self.viewport_layers)
            if layer.visible and layer.image
        ]

        if not visible_media:
            self.viewport_canvas.create_text(
                width / 2, height / 2,
                text="Drag an asset onto a timeline track\nto add it to the viewport.",
                fill=TEXT_DIM,
                font=("Segoe UI", 12),
                justify="center"
            )
            return

        for layer in visible_media:
            try:
                image = Image.open(layer.image).convert("RGBA")
                image_width, image_height = image.size
                scale = min(width / image_width, height / image_height) * layer.scale
                new_size = (
                    max(1, int(image_width * scale)),
                    max(1, int(image_height * scale))
                )
                image = image.resize(new_size, Image.Resampling.LANCZOS)

                if layer.opacity < 1.0:
                    alpha = image.getchannel("A").point(
                        lambda value: int(value * layer.opacity)
                    )
                    image.putalpha(alpha)

                photo = ImageTk.PhotoImage(image)
                self.viewport_photos.append(photo)
                self.viewport_canvas.create_image(
                    width / 2 + layer.x,
                    height / 2 + layer.y,
                    image=photo,
                    anchor="center"
                )
            except Exception as error:
                print("Could not render viewport layer:", error)

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
