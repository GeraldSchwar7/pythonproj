import tkinter as tk
from settings import PANEL, PANEL_LIGHT, BORDER, TEXT, TEXT_DIM
from media_clip import MediaClip


class TimelinePanel(tk.Frame):
    TRACK_HEIGHT = 52
    RULER_HEIGHT = 32

    def __init__(self, parent, on_clip_added=None, on_time_changed=None, on_timeline_changed=None):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

        self.layers = []
        self.on_clip_added = on_clip_added
        self.on_time_changed = on_time_changed
        self.on_timeline_changed = on_timeline_changed

        self.current_time = 0.0
        self.timeline_duration = 60.0
        self.pixels_per_second = 70.0

        self.dragged_clip = None
        self.dragged_clip_layer = None
        self.drag_offset_time = 0.0
        self.is_dragging_clip = False

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x")

        tk.Label(header, text="Timeline", bg=PANEL, fg=TEXT,
                 font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=7)

        self.time_label = tk.Label(header, text="00:00.00", bg=PANEL, fg=TEXT_DIM)
        self.time_label.pack(side="left", padx=8)

        tk.Button(header, text="+", width=3, command=self.zoom_in).pack(side="right", padx=2)
        tk.Button(header, text="-", width=3, command=self.zoom_out).pack(side="right", padx=2)

        body = tk.Frame(self, bg=PANEL)
        body.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg="#181818", highlightthickness=0)
        self.h_scroll = tk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = tk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Configure>", lambda event: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._mouse_pressed)
        self.canvas.bind("<B1-Motion>", self._mouse_dragged)
        self.canvas.bind("<ButtonRelease-1>", self._mouse_released)
        self.canvas.bind("<Motion>", self._mouse_moved)
        self.canvas.bind("<Shift-MouseWheel>", self._horizontal_wheel)

    def set_layers(self, layers):
        self.layers = layers
        self.redraw()

    def drop_asset_at_screen(self, file_path, x_root, y_root):
        local_x = x_root - self.canvas.winfo_rootx()
        local_y = y_root - self.canvas.winfo_rooty()

        if not (0 <= local_x < self.canvas.winfo_width() and
                0 <= local_y < self.canvas.winfo_height()):
            return False

        timeline_x = self.canvas.canvasx(local_x)
        timeline_y = self.canvas.canvasy(local_y)

        if timeline_y < self.RULER_HEIGHT:
            return False

        layer_index = int((timeline_y - self.RULER_HEIGHT) // self.TRACK_HEIGHT)
        if not (0 <= layer_index < len(self.layers)):
            return False

        start_time = max(0.0, timeline_x / self.pixels_per_second)
        clip = MediaClip(file_path, start_time=start_time)
        layer = self.layers[layer_index]
        layer.add_clip(clip)

        self.timeline_duration = max(self.timeline_duration, clip.end_time + 5.0)
        self.redraw()

        if self.on_clip_added is not None:
            self.on_clip_added(layer, clip)

        return True

    def _find_clip_at_position(self, timeline_x, timeline_y):
        if timeline_y < self.RULER_HEIGHT:
            return None, None

        layer_index = int((timeline_y - self.RULER_HEIGHT) // self.TRACK_HEIGHT)
        if not (0 <= layer_index < len(self.layers)):
            return None, None

        layer = self.layers[layer_index]
        clip_y0 = self.RULER_HEIGHT + layer_index * self.TRACK_HEIGHT + 16
        clip_y1 = self.RULER_HEIGHT + (layer_index + 1) * self.TRACK_HEIGHT - 5

        if not (clip_y0 <= timeline_y <= clip_y1):
            return None, None

        for clip in reversed(layer.clips):
            x0 = clip.start_time * self.pixels_per_second
            x1 = clip.end_time * self.pixels_per_second
            if x0 <= timeline_x <= x1:
                return layer, clip

        return None, None

    def _mouse_pressed(self, event):
        timeline_x = self.canvas.canvasx(event.x)
        timeline_y = self.canvas.canvasy(event.y)
        layer, clip = self._find_clip_at_position(timeline_x, timeline_y)

        if clip is not None:
            self.dragged_clip = clip
            self.dragged_clip_layer = layer
            self.is_dragging_clip = True
            mouse_time = timeline_x / self.pixels_per_second
            self.drag_offset_time = mouse_time - clip.start_time
            return

        self.set_current_time(timeline_x / self.pixels_per_second)

    def _mouse_dragged(self, event):
        if not self.is_dragging_clip or self.dragged_clip is None:
            return

        timeline_x = self.canvas.canvasx(event.x)
        timeline_y = self.canvas.canvasy(event.y)

        mouse_time = timeline_x / self.pixels_per_second
        new_start_time = max(0.0, mouse_time - self.drag_offset_time)

        snap_interval = 0.25
        new_start_time = round(new_start_time / snap_interval) * snap_interval
        self.dragged_clip.start_time = new_start_time

        target_layer_index = int((timeline_y - self.RULER_HEIGHT) // self.TRACK_HEIGHT)
        if 0 <= target_layer_index < len(self.layers):
            target_layer = self.layers[target_layer_index]
            if target_layer is not self.dragged_clip_layer:
                self.dragged_clip_layer.remove_clip(self.dragged_clip)
                target_layer.add_clip(self.dragged_clip)
                self.dragged_clip_layer = target_layer

        if self.dragged_clip.end_time > self.timeline_duration:
            self.timeline_duration = self.dragged_clip.end_time + 5.0

        self.redraw()

    def _mouse_released(self, event):
        if not self.is_dragging_clip:
            return

        self.dragged_clip = None
        self.dragged_clip_layer = None
        self.drag_offset_time = 0.0
        self.is_dragging_clip = False
        self.redraw()

        if self.on_timeline_changed is not None:
            self.on_timeline_changed()

    def _mouse_moved(self, event):
        timeline_x = self.canvas.canvasx(event.x)
        timeline_y = self.canvas.canvasy(event.y)
        _, clip = self._find_clip_at_position(timeline_x, timeline_y)
        self.canvas.configure(cursor="fleur" if clip is not None else "")

    def set_current_time(self, value):
        self.current_time = max(0.0, min(float(value), self.timeline_duration))
        self.time_label.configure(text=self._format_time(self.current_time, hundredths=True))
        self.redraw()

        if self.on_time_changed is not None:
            self.on_time_changed(self.current_time)

    def zoom_in(self):
        self._set_zoom(min(400.0, self.pixels_per_second * 1.25))

    def zoom_out(self):
        self._set_zoom(max(10.0, self.pixels_per_second / 1.25))

    def _set_zoom(self, new_zoom):
        center_x = self.canvas.canvasx(self.canvas.winfo_width() / 2)
        center_time = center_x / self.pixels_per_second
        self.pixels_per_second = new_zoom
        self.redraw()

        total_width = max(1.0, self.timeline_duration * self.pixels_per_second)
        desired_left = max(
            0.0,
            center_time * self.pixels_per_second - self.canvas.winfo_width() / 2
        )
        self.canvas.xview_moveto(min(1.0, desired_left / total_width))

    def _horizontal_wheel(self, event):
        self.canvas.xview_scroll(int(-event.delta / 120), "units")

    def redraw(self):
        self.canvas.delete("all")

        timeline_width = max(
            self.canvas.winfo_width(),
            self.timeline_duration * self.pixels_per_second
        )

        timeline_height = max(
            self.canvas.winfo_height(),
            self.RULER_HEIGHT + len(self.layers) * self.TRACK_HEIGHT
        )

        self.canvas.configure(scrollregion=(0, 0, timeline_width, timeline_height))
        self._draw_ruler(timeline_width)
        self._draw_tracks(timeline_width)
        self._draw_clips()
        self._draw_playhead(timeline_height)

    def _draw_ruler(self, width):
        self.canvas.create_rectangle(
            0, 0, width, self.RULER_HEIGHT,
            fill=PANEL_LIGHT, outline=BORDER
        )

        if self.pixels_per_second >= 80:
            interval = 1
        elif self.pixels_per_second >= 25:
            interval = 5
        else:
            interval = 10

        second = 0
        while second <= int(self.timeline_duration) + interval:
            x = second * self.pixels_per_second
            self.canvas.create_line(x, 18, x, self.RULER_HEIGHT, fill=TEXT_DIM)
            self.canvas.create_text(
                x + 3, 3,
                text=self._format_time(second),
                anchor="nw",
                fill=TEXT_DIM
            )
            second += interval

    def _draw_tracks(self, width):
        for index, layer in enumerate(self.layers):
            y0 = self.RULER_HEIGHT + index * self.TRACK_HEIGHT
            y1 = y0 + self.TRACK_HEIGHT
            fill = "#1d1d1d" if index % 2 == 0 else "#222222"

            self.canvas.create_rectangle(
                0, y0, width, y1,
                outline=BORDER, fill=fill
            )

            self.canvas.create_text(
                8, y0 + 5,
                text=layer.name,
                anchor="nw",
                fill=TEXT_DIM
            )

    def _draw_clips(self):
        for layer_index, layer in enumerate(self.layers):
            y0 = self.RULER_HEIGHT + layer_index * self.TRACK_HEIGHT + 16
            y1 = self.RULER_HEIGHT + (layer_index + 1) * self.TRACK_HEIGHT - 5

            for clip in layer.clips:
                x0 = clip.start_time * self.pixels_per_second
                x1 = clip.end_time * self.pixels_per_second

                if clip.media_type == "video":
                    fill = "#315f86"
                    prefix = "VID "
                else:
                    fill = "#4f6b3a"
                    prefix = "IMG "

                self.canvas.create_rectangle(
                    x0, y0, x1, y1,
                    outline=BORDER, fill=fill, width=2
                )

                self.canvas.create_text(
                    x0 + 6,
                    (y0 + y1) / 2,
                    text=prefix + clip.name,
                    anchor="w",
                    fill=TEXT
                )

    def _draw_playhead(self, height):
        x = self.current_time * self.pixels_per_second
        self.canvas.create_line(x, 0, x, height, fill="#ff4040", width=2)
        self.canvas.create_polygon(
            x - 6, 0,
            x + 6, 0,
            x, 9,
            fill="#ff4040",
            outline=""
        )

    @staticmethod
    def _format_time(seconds, hundredths=False):
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60

        if hundredths:
            return f"{minutes:02d}:{remaining_seconds:05.2f}"

        return f"{minutes:02d}:{int(remaining_seconds):02d}"
