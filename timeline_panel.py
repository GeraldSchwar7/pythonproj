import os
import tkinter as tk
from settings import PANEL, PANEL_LIGHT, BORDER, TEXT, TEXT_DIM

class TimelinePanel(tk.Frame):
    TRACK_HEIGHT = 42
    LABEL_WIDTH = 120

    def __init__(self, parent, on_clip_added=None):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        self.layers = []
        self.on_clip_added = on_clip_added

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x")
        tk.Label(header, text="Timeline", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=7)
        tk.Label(header, text="Drag assets onto a layer track", bg=PANEL,
                 fg=TEXT_DIM).pack(side="right", padx=10)

        self.canvas = tk.Canvas(self, bg="#181818", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.canvas.bind("<Configure>", lambda e: self.redraw())

    def set_layers(self, layers):
        self.layers = layers
        self.redraw()

    def redraw(self):
        self.canvas.delete("all")
        width = max(self.canvas.winfo_width(), 400)

        for index, layer in enumerate(self.layers):
            y0 = index * self.TRACK_HEIGHT
            y1 = y0 + self.TRACK_HEIGHT
            self.canvas.create_rectangle(0, y0, width, y1, outline=BORDER, fill="#181818")
            self.canvas.create_rectangle(0, y0, self.LABEL_WIDTH, y1,
                                         outline=BORDER, fill=PANEL)
            self.canvas.create_text(8, y0 + self.TRACK_HEIGHT / 2,
                                    text=layer.name, anchor="w", fill=TEXT)

            clip_x = self.LABEL_WIDTH + 8
            for clip in layer.clips:
                clip_width = 145
                self.canvas.create_rectangle(
                    clip_x, y0 + 6, clip_x + clip_width, y1 - 6,
                    outline=BORDER, fill=PANEL_LIGHT)
                name = os.path.basename(clip)
                if len(name) > 18:
                    name = name[:15] + "..."
                self.canvas.create_text(clip_x + 7, y0 + self.TRACK_HEIGHT / 2,
                                        text=name, anchor="w", fill=TEXT)
                clip_x += clip_width + 6

        self.canvas.configure(scrollregion=(0, 0, width,
                              max(len(self.layers) * self.TRACK_HEIGHT, self.canvas.winfo_height())))

    def drop_asset_at_screen(self, file_path, x_root, y_root):
        # Convert global mouse coordinates to coordinates inside the timeline canvas.
        x = x_root - self.canvas.winfo_rootx()
        y = y_root - self.canvas.winfo_rooty()
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        if not (0 <= x < width and 0 <= y < height):
            return False

        layer_index = int(y // self.TRACK_HEIGHT)
        if not (0 <= layer_index < len(self.layers)):
            return False

        layer = self.layers[layer_index]
        layer.clips.append(file_path)
        # The most recently dropped media becomes the layer's viewport image.
        layer.image = file_path
        self.redraw()

        if self.on_clip_added:
            self.on_clip_added(layer, file_path)
        return True
