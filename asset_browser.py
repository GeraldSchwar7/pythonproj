import os
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from settings import PANEL, PANEL_LIGHT, BORDER, TEXT

class AssetBrowser(tk.Frame):
    def __init__(self, parent, on_asset_drop=None):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.images = []
        self.thumbnail_images = []
        self.on_asset_drop = on_asset_drop
        self.drag_path = None
        self.drag_ghost = None

        tk.Label(self, text="Assets", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=7)

        self.import_button = tk.Button(
            self, text="+ Import Images", command=self.import_images,
            bg=PANEL_LIGHT, fg=TEXT, activebackground=BORDER,
            activeforeground=TEXT, relief="flat")
        self.import_button.pack(fill="x", padx=10, pady=(0, 10))

        self.thumbnail_frame = tk.Frame(self, bg=PANEL)
        self.thumbnail_frame.pack(fill="both", expand=True, padx=5, pady=5)

    def import_images(self):
        files = filedialog.askopenfilenames(
            title="Import Images",
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.webp")])
        for file_path in files:
            self.add_image(file_path)

    def add_image(self, file_path):
        try:
            image = Image.open(file_path)
            image.thumbnail((80, 80))
            thumbnail = ImageTk.PhotoImage(image)
            self.thumbnail_images.append(thumbnail)
            self.images.append(file_path)

            index = len(self.images) - 1
            button = tk.Button(
                self.thumbnail_frame, image=thumbnail, bg=PANEL_LIGHT,
                activebackground=BORDER, relief="flat", cursor="hand2")
            button.grid(row=index // 2, column=index % 2, padx=4, pady=4)

            # Tkinter has no native internal drag/drop, so mouse motion tracks
            # the asset until release and Workspace decides whether it hit a track.
            button.bind("<ButtonPress-1>", lambda e, p=file_path: self._start_drag(e, p))
            button.bind("<B1-Motion>", self._drag_motion)
            button.bind("<ButtonRelease-1>", self._finish_drag)
        except Exception as error:
            print("Could not load image:", error)

    def _start_drag(self, event, file_path):
        self.drag_path = file_path
        self._destroy_ghost()
        self.drag_ghost = tk.Toplevel(self)
        self.drag_ghost.overrideredirect(True)
        self.drag_ghost.attributes("-topmost", True)
        tk.Label(self.drag_ghost, text=os.path.basename(file_path),
                 bg=PANEL_LIGHT, fg=TEXT, padx=8, pady=5,
                 relief="solid", borderwidth=1).pack()
        self._move_ghost(event.x_root, event.y_root)

    def _drag_motion(self, event):
        self._move_ghost(event.x_root, event.y_root)

    def _move_ghost(self, x_root, y_root):
        if self.drag_ghost is not None:
            self.drag_ghost.geometry(f"+{x_root + 12}+{y_root + 12}")

    def _finish_drag(self, event):
        path = self.drag_path
        self.drag_path = None
        self._destroy_ghost()
        if path and self.on_asset_drop:
            self.on_asset_drop(path, event.x_root, event.y_root)

    def _destroy_ghost(self):
        if self.drag_ghost is not None:
            try:
                self.drag_ghost.destroy()
            except tk.TclError:
                pass
            self.drag_ghost = None
