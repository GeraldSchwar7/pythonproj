import time
import tkinter as tk
from settings import (PANEL, PANEL_LIGHT, PANEL_HOVER, PANEL_DEEP, BORDER, TEXT, TEXT_DIM,
                      TEXT_MUTED, ACCENT, ACCENT_SOFT, PLAYHEAD, TRACK_A, TRACK_B, VIDEO_CLIP,
                      IMAGE_CLIP, FONT, flat_button)
from media_clip import MediaClip
from layer import Layer


class TimelinePanel(tk.Frame):
    TRACK_HEIGHT = 64
    RULER_HEIGHT = 32
    TRACK_HEADER_HEIGHT = 26
    CLIP_TOP_PADDING = 28
    LAYER_NAME_X = 42
    LAYER_NAME_WIDTH = 150

    def __init__(self, parent, on_clip_added=None, on_time_changed=None,
                 on_timeline_changed=None, on_layer_selected=None):
        super().__init__(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)

        self.layers = [
            Layer("Background"),
            Layer("Midground"),
            Layer("Foreground"),
        ]
        self.selected_layer = self.layers[0]
        self.on_clip_added = on_clip_added
        self.on_time_changed = on_time_changed
        self.on_timeline_changed = on_timeline_changed
        self.on_layer_selected = on_layer_selected

        self.current_time = 0.0
        self.timeline_duration = 60.0
        self.pixels_per_second = 70.0
        self.is_playing = False
        self.playback_job = None
        self.playback_interval_ms = 33
        self._last_playback_tick = None

        self.dragged_clip = None
        self.dragged_clip_layer = None
        self.drag_offset_time = 0.0
        self.is_dragging_clip = False
        self.is_dragging_playhead = False
        self.resizing_clip = None
        self.resize_edge = None
        self.resize_fixed_time = 0.0
        self.is_dragging_layer = False
        self.dragged_layer = None
        self.layer_order_changed = False

        # How close the mouse needs to be to the playhead
        # to grab it.
        self.playhead_grab_width = 8
        self.clip_resize_grab_width = 6

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x")

        tk.Label(header, text="TIMELINE", bg=PANEL, fg=TEXT_DIM,
                 font=(FONT, 9, "bold")).pack(side="left", padx=(12, 8), pady=10)

        self.time_label = tk.Label(header, text="00:00.00", bg=PANEL_DEEP, fg=TEXT,
                                   font=("Consolas", 10, "bold"), padx=8, pady=3)
        self.time_label.pack(side="left", padx=8)

        self.play_button = flat_button(
            header,
            "Play",
            self.toggle_playback
        )
        self.play_button.pack(side="left", padx=4)

        flat_button(header, "+", self.zoom_in, width=2).pack(side="right", padx=(2, 10), pady=5)
        flat_button(header, "−", self.zoom_out, width=2).pack(side="right", padx=2, pady=5)

        layer_toolbar = tk.Frame(self, bg=PANEL)
        layer_toolbar.pack(fill="x", padx=8, pady=(0, 4))

        tk.Label(
            layer_toolbar,
            text="LAYERS",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 8, "bold")
        ).pack(side="left", padx=(2, 8))

        flat_button(layer_toolbar, "Add Layer", self.create_layer).pack(side="left", padx=2)
        flat_button(layer_toolbar, "Delete Layer", self.delete_selected_layer).pack(side="left", padx=2)

        body = tk.Frame(self, bg=PANEL)
        body.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(body, bg=PANEL_DEEP, highlightthickness=0)
        from tkinter import ttk
        self.h_scroll = ttk.Scrollbar(body, orient="horizontal", command=self.canvas.xview)
        self.v_scroll = ttk.Scrollbar(body, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(xscrollcommand=self.h_scroll.set, yscrollcommand=self.v_scroll.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.v_scroll.grid(row=0, column=1, sticky="ns")
        self.h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.bind("<Configure>", lambda event: self.redraw())
        self.canvas.bind("<ButtonPress-1>", self._mouse_pressed)
        self.canvas.bind("<B1-Motion>", self._mouse_dragged)
        self.canvas.bind("<ButtonRelease-1>", self._mouse_released)
        self.canvas.bind("<Motion>", self._mouse_moved)
        self.canvas.bind("<Double-Button-1>", self._rename_layer_from_canvas)
        self.canvas.bind("<Shift-MouseWheel>", self._horizontal_wheel)

    def set_layers(self, layers):
        self.layers = layers
        if self.selected_layer not in self.layers:
            self.selected_layer = self.layers[0] if self.layers else None
        self.redraw()

    def select_layer(self, layer):
        if layer not in self.layers or layer is self.selected_layer:
            return

        self.selected_layer = layer
        self.redraw()
        if self.on_layer_selected is not None:
            self.on_layer_selected(layer)

    def create_layer(self):
        layer = Layer(f"Layer {len(self.layers) + 1}")
        self.layers.insert(0, layer)
        self.select_layer(layer)
        self._notify_timeline_changed()
        return layer

    def delete_selected_layer(self):
        if self.selected_layer is not None:
            self.delete_layer(self.selected_layer)

    def delete_layer(self, layer):
        if layer not in self.layers:
            return

        index = self.layers.index(layer)
        self.layers.remove(layer)
        if self.selected_layer is layer:
            self.selected_layer = (
                self.layers[min(index, len(self.layers) - 1)]
                if self.layers
                else None
            )
            if self.on_layer_selected is not None:
                self.on_layer_selected(self.selected_layer)

        self.redraw()
        self._notify_timeline_changed()

    def rename_selected_layer(self):
        layer = self.selected_layer
        if layer is None:
            return

        layer_index = self.layers.index(layer)
        row_y = self.RULER_HEIGHT + layer_index * self.TRACK_HEIGHT
        rename_entry = tk.Entry(
            self.canvas,
            bg=PANEL_LIGHT,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat"
        )
        rename_entry.insert(0, layer.name)
        window_id = self.canvas.create_window(
            self.LAYER_NAME_X + 4,
            row_y + 4,
            window=rename_entry,
            anchor="nw",
            width=self.LAYER_NAME_WIDTH - 8,
            height=self.TRACK_HEADER_HEIGHT - 6
        )
        rename_entry.focus_set()
        rename_entry.select_range(0, tk.END)
        rename_finished = False

        def finish_rename(event=None):
            nonlocal rename_finished
            if rename_finished:
                return

            rename_finished = True
            new_name = rename_entry.get().strip()
            if new_name:
                layer.name = new_name

            rename_entry.destroy()
            self.canvas.delete(window_id)
            self.redraw()
            if new_name:
                self._notify_timeline_changed()

        def cancel_rename(event=None):
            nonlocal rename_finished
            if rename_finished:
                return

            rename_finished = True
            rename_entry.destroy()
            self.canvas.delete(window_id)

        rename_entry.bind("<Return>", finish_rename)
        rename_entry.bind("<FocusOut>", finish_rename)
        rename_entry.bind("<Escape>", cancel_rename)

    def _rename_layer_from_canvas(self, event):
        timeline_x = self.canvas.canvasx(event.x)
        timeline_y = self.canvas.canvasy(event.y)
        layer_index = self._layer_name_index_at(
            timeline_x,
            timeline_y
        )
        if layer_index is None:
            return

        self.select_layer(self.layers[layer_index])
        self.rename_selected_layer()

    def _notify_timeline_changed(self):
        if self.on_timeline_changed is not None:
            self.on_timeline_changed()

    def _layer_index_at_y(self, timeline_y):
        if timeline_y < self.RULER_HEIGHT:
            return None

        layer_index = int(
            (timeline_y - self.RULER_HEIGHT) // self.TRACK_HEIGHT
        )
        return layer_index if 0 <= layer_index < len(self.layers) else None

    def _layer_name_index_at(self, timeline_x, timeline_y):
        layer_index = self._layer_index_at_y(timeline_y)
        if layer_index is None:
            return None

        name_box_items = self.canvas.find_withtag(
            f"layer-name-box-{layer_index}"
        )
        if not name_box_items:
            return None

        bounds = self.canvas.bbox(name_box_items[0])
        if bounds is None:
            return None

        x0, y0, x1, y1 = bounds
        if x0 <= timeline_x <= x1 and y0 <= timeline_y <= y1:
            return layer_index
        return None

    def _toggle_layer_visibility_at(self, timeline_x, timeline_y):
        layer_index = self._layer_index_at_y(timeline_y)
        if layer_index is None:
            return False

        row_y = self.RULER_HEIGHT + layer_index * self.TRACK_HEIGHT
        if not (24 <= timeline_x <= 38 and row_y + 2 <= timeline_y <= row_y + 15):
            return False

        layer = self.layers[layer_index]
        self.toggle_layer_visibility(layer)
        return True

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
        self.select_layer(layer)

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
        clip_y0 = (
            self.RULER_HEIGHT
            + layer_index * self.TRACK_HEIGHT
            + self.CLIP_TOP_PADDING
        )
        clip_y1 = self.RULER_HEIGHT + (layer_index + 1) * self.TRACK_HEIGHT - 5

        if not (clip_y0 <= timeline_y <= clip_y1):
            return None, None

        for clip in reversed(layer.clips):
            x0 = clip.start_time * self.pixels_per_second
            x1 = clip.end_time * self.pixels_per_second
            if x0 <= timeline_x <= x1:
                return layer, clip

        return None, None

    def _find_clip_resize_edge(self, timeline_x, timeline_y):
        layer, clip = self._find_clip_at_position(timeline_x, timeline_y)
        if clip is None or clip.media_type != "image":
            return None, None, None

        left_x = clip.start_time * self.pixels_per_second
        right_x = clip.end_time * self.pixels_per_second
        left_distance = abs(timeline_x - left_x)
        right_distance = abs(timeline_x - right_x)

        if min(left_distance, right_distance) > self.clip_resize_grab_width:
            return None, None, None

        edge = "left" if left_distance <= right_distance else "right"
        return layer, clip, edge

    def _layer_reorder_handle_at_position(self, timeline_x, timeline_y):
        if not (6 <= timeline_x <= 20) or timeline_y < self.RULER_HEIGHT:
            return None

        layer_index = int(
            (timeline_y - self.RULER_HEIGHT) // self.TRACK_HEIGHT
        )
        if not (0 <= layer_index < len(self.layers)):
            return None

        row_y = self.RULER_HEIGHT + layer_index * self.TRACK_HEIGHT
        if timeline_y > row_y + 15:
            return None

        return layer_index

    def _mouse_pressed(self, event):
        timeline_x = self.canvas.canvasx(event.x)
        timeline_y = self.canvas.canvasy(event.y)

        layer, clip, edge = self._find_clip_resize_edge(timeline_x, timeline_y)
        if clip is not None:
            self.select_layer(layer)
            self.resizing_clip = clip
            self.resize_edge = edge
            self.resize_fixed_time = (
                clip.end_time if edge == "left" else clip.start_time
            )
            return

        layer, clip = self._find_clip_at_position(timeline_x, timeline_y)
        if clip is not None:
            self.select_layer(layer)
            self.dragged_clip = clip
            self.dragged_clip_layer = layer
            self.is_dragging_clip = True
            mouse_time = timeline_x / self.pixels_per_second
            self.drag_offset_time = mouse_time - clip.start_time
            return

        layer_index = self._layer_reorder_handle_at_position(
            timeline_x, timeline_y
        )
        if layer_index is not None:
            self.select_layer(self.layers[layer_index])
            self.dragged_layer = self.layers[layer_index]
            self.is_dragging_layer = True
            self.layer_order_changed = False
            return

        layer_index = self._layer_name_index_at(timeline_x, timeline_y)
        if layer_index is not None:
            self.select_layer(self.layers[layer_index])
            return

        layer_index = self._layer_index_at_y(timeline_y)
        if layer_index is not None:
            self.select_layer(self.layers[layer_index])
            if self._toggle_layer_visibility_at(timeline_x, timeline_y):
                return

        playhead_x = self.current_time * self.pixels_per_second
        distance_from_playhead = abs(timeline_x - playhead_x)
        if (distance_from_playhead <= self.playhead_grab_width or
                timeline_y <= self.RULER_HEIGHT):
            self.is_dragging_playhead = True
            self._update_playhead_from_x(timeline_x)
            return

        self.set_current_time(timeline_x / self.pixels_per_second)

    def _move_playhead_visual(self):

        x = (
            self.current_time
            * self.pixels_per_second
        )

        timeline_height = max(self.canvas.winfo_height(),
            self.RULER_HEIGHT
            + len(self.layers)
            * self.TRACK_HEIGHT
        )

    # Remove only the old playhead.
        self.canvas.delete(
            "playhead"
        )

    # Draw line.
        self.canvas.create_line(x,0,x,timeline_height,
            fill=PLAYHEAD,
            width=2,
            tags="playhead"
        )

    # Draw triangle.
        self.canvas.create_polygon(x - 6,0,x + 6,0,x,9,
            fill=PLAYHEAD,
            outline="",
            tags="playhead"
        )
    # Keep playhead above clips.
        self.canvas.tag_raise("playhead")

    def _update_playhead_from_x(self,timeline_x):
        self.set_current_time(
            timeline_x / self.pixels_per_second
        )

    def _mouse_dragged(self, event):
        timeline_x = self.canvas.canvasx(event.x)

        if self.resizing_clip is not None:
            resized_time = max(0.0, timeline_x / self.pixels_per_second)
            if self.resize_edge == "left":
                new_start = min(
                    resized_time,
                    self.resize_fixed_time - 0.05
                )
                self.resizing_clip.start_time = max(0.0, new_start)
                self.resizing_clip.duration = (
                    self.resize_fixed_time - self.resizing_clip.start_time
                )
            else:
                self.resizing_clip.duration = max(
                    0.05,
                    resized_time - self.resizing_clip.start_time
                )

            if self.resizing_clip.end_time > self.timeline_duration:
                self.timeline_duration = self.resizing_clip.end_time + 5.0
            self.redraw()
            return

        if self.is_dragging_layer:
            if not self.layers:
                return

            timeline_y = self.canvas.canvasy(event.y)
            target_index = int(
                (timeline_y - self.RULER_HEIGHT) // self.TRACK_HEIGHT
            )
            target_index = max(0, min(target_index, len(self.layers) - 1))
            source_index = self.layers.index(self.dragged_layer)
            if source_index != target_index:
                layer = self.layers.pop(source_index)
                self.layers.insert(target_index, layer)
                self.layer_order_changed = True
                self.redraw()
            return

        if self.is_dragging_playhead:
            self._update_playhead_from_x(timeline_x)
            return

        if not self.is_dragging_clip:
            return

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
                self.select_layer(target_layer)

        if self.dragged_clip.end_time > self.timeline_duration:
            self.timeline_duration = self.dragged_clip.end_time + 5.0

        self.redraw()

    def _mouse_released(self, event):
        if self.resizing_clip is not None:
            self.resizing_clip = None
            self.resize_edge = None
            self.redraw()
            if self.on_timeline_changed is not None:
                self.on_timeline_changed()
            return

        if self.is_dragging_layer:
            self.is_dragging_layer = False
            self.dragged_layer = None
            self.redraw()
            if self.layer_order_changed and self.on_timeline_changed is not None:
                self.on_timeline_changed()
            self.layer_order_changed = False
            return

        if self.is_dragging_playhead:
            self.is_dragging_playhead = False
            return

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
        _, _, edge = self._find_clip_resize_edge(timeline_x, timeline_y)
        if edge is not None:
            self.canvas.configure(cursor="sb_h_double_arrow")
            return

        if self._layer_reorder_handle_at_position(timeline_x, timeline_y) is not None:
            self.canvas.configure(cursor="fleur")
            return

        _, clip = self._find_clip_at_position(timeline_x, timeline_y)
        self.canvas.configure(cursor="fleur" if clip is not None else "")

    def set_current_time(self, value):
        self.current_time = max(0.0, min(float(value), self.timeline_duration))
        self.time_label.configure(text=self._format_time(self.current_time, hundredths=True))
        self._move_playhead_visual()

        if self.on_time_changed is not None:
            self.on_time_changed(self.current_time)

    def toggle_layer_visibility(self, layer):
        if layer not in self.layers:
            return

        self.select_layer(layer)
        layer.visible = not layer.visible
        self.redraw()
        self._notify_timeline_changed()

    def toggle_playback(self):
        if self.is_playing:
            self.pause_playback()
        else:
            self.play_playback()

    def play_playback(self):
        if self.is_playing:
            return

        if self.current_time >= self.timeline_duration:
            self.set_current_time(0.0)

        self.is_playing = True
        self.play_button.configure(text="Pause")
        self._last_playback_tick = time.monotonic()
        self.playback_job = self.after(
            self.playback_interval_ms,
            self._advance_playback
        )

    def pause_playback(self):
        self.is_playing = False
        self._last_playback_tick = None

        if self.playback_job is not None:
            self.after_cancel(self.playback_job)
            self.playback_job = None

        self.play_button.configure(text="Play")

    def _advance_playback(self):
        self.playback_job = None

        if not self.is_playing:
            return

        now = time.monotonic()
        elapsed = now - self._last_playback_tick
        self._last_playback_tick = now

        next_time = min(
            self.current_time + elapsed,
            self.timeline_duration
        )
        self.set_current_time(next_time)

        if self.current_time >= self.timeline_duration:
            self.pause_playback()
            return

        self.playback_job = self.after(
            self.playback_interval_ms,
            self._advance_playback
        )

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
            selected = layer is self.selected_layer
            fill = (
                ACCENT_SOFT
                if selected
                else TRACK_A if index % 2 == 0 else TRACK_B
            )

            self.canvas.create_rectangle(
                0, y0, width, y1,
                outline=ACCENT if selected else BORDER,
                fill=fill
            )

            for grip_y in (y0 + 5, y0 + 9, y0 + 13):
                self.canvas.create_line(
                    8, grip_y, 18, grip_y,
                    fill=TEXT_MUTED,
                    width=1
                )

            self.canvas.create_rectangle(
                self.LAYER_NAME_X,
                y0 + 3,
                self.LAYER_NAME_X + self.LAYER_NAME_WIDTH,
                y0 + self.TRACK_HEADER_HEIGHT,
                outline=ACCENT if selected else BORDER,
                fill=PANEL_DEEP,
                tags=(f"layer-name-box-{index}",)
            )

            self.canvas.create_text(
                24, y0 + 5,
                text="●" if layer.visible else "○",
                anchor="nw",
                fill=TEXT_DIM
            )

            self.canvas.create_text(
                self.LAYER_NAME_X + 6, y0 + 6,
                text=layer.name,
                anchor="nw",
                fill=TEXT if selected else TEXT_DIM,
                font=(FONT, 9, "bold" if selected else "normal"),
                tags=(f"layer-name-{index}",)
            )

    def _draw_clips(self):
        for layer_index, layer in enumerate(self.layers):
            y0 = (
                self.RULER_HEIGHT
                + layer_index * self.TRACK_HEIGHT
                + self.CLIP_TOP_PADDING
            )
            y1 = self.RULER_HEIGHT + (layer_index + 1) * self.TRACK_HEIGHT - 5

            for clip in layer.clips:
                x0 = clip.start_time * self.pixels_per_second
                x1 = clip.end_time * self.pixels_per_second

                if clip.media_type == "video":
                    fill = VIDEO_CLIP
                    prefix = "VID "
                else:
                    fill = IMAGE_CLIP
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

                if clip.media_type == "image":
                    self.canvas.create_line(
                        x0, y0 + 5, x0, y1 - 5,
                        fill=TEXT,
                        width=3
                    )
                    self.canvas.create_line(
                        x1, y0 + 5, x1, y1 - 5,
                        fill=TEXT,
                        width=3
                    )

    def _draw_playhead(self, height):
        x = self.current_time * self.pixels_per_second
        self.canvas.create_line(x, 0, x, height, fill=PLAYHEAD, width=2, tags="playhead")
        self.canvas.create_polygon(
            x - 6, 0,
            x + 6, 0,
            x, 9,
            fill=PLAYHEAD,
            outline="",
            tags="playhead"
        )

    @staticmethod
    def _format_time(seconds, hundredths=False):
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60

        if hundredths:
            return f"{minutes:02d}:{remaining_seconds:05.2f}"

        return f"{minutes:02d}:{int(remaining_seconds):02d}"
