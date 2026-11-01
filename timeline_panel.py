import tkinter as tk

from settings import (
    PANEL,
    PANEL_LIGHT,
    BORDER,
    TEXT,
    TEXT_DIM
)

from media_clip import MediaClip


class TimelinePanel(tk.Frame):

    TRACK_HEIGHT = 52
    RULER_HEIGHT = 32

    def __init__(
        self,
        parent,
        on_clip_added=None,
        on_time_changed=None
    ):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        # ==================================================
        # DATA
        # ==================================================

        self.layers = []

        self.on_clip_added = (
            on_clip_added
        )

        self.on_time_changed = (
            on_time_changed
        )

        # Current playhead position.
        self.current_time = 0.0

        # Initial project length.
        self.timeline_duration = 60.0

        # Timeline zoom.
        self.pixels_per_second = 70.0

        # ==================================================
        # HEADER
        # ==================================================

        header = tk.Frame(
            self,
            bg=PANEL
        )

        header.pack(
            fill="x"
        )

        tk.Label(
            header,
            text="Timeline",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            side="left",
            padx=10,
            pady=7
        )

        # ==================================================
        # CURRENT TIME
        # ==================================================

        self.time_label = tk.Label(
            header,
            text="00:00.00",
            bg=PANEL,
            fg=TEXT_DIM
        )

        self.time_label.pack(
            side="left",
            padx=8
        )

        # ==================================================
        # ZOOM
        # ==================================================

        tk.Button(
            header,
            text="+",
            width=3,
            command=self.zoom_in
        ).pack(
            side="right",
            padx=2
        )

        tk.Button(
            header,
            text="-",
            width=3,
            command=self.zoom_out
        ).pack(
            side="right",
            padx=2
        )

        # ==================================================
        # CANVAS CONTAINER
        # ==================================================

        body = tk.Frame(
            self,
            bg=PANEL
        )

        body.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        body.grid_rowconfigure(
            0,
            weight=1
        )

        body.grid_columnconfigure(
            0,
            weight=1
        )

        # ==================================================
        # TIMELINE CANVAS
        # ==================================================

        self.canvas = tk.Canvas(
            body,
            bg="#181818",
            highlightthickness=0
        )

        # ==================================================
        # SCROLLBARS
        # ==================================================

        self.h_scroll = tk.Scrollbar(
            body,
            orient="horizontal",
            command=self.canvas.xview
        )

        self.v_scroll = tk.Scrollbar(
            body,
            orient="vertical",
            command=self.canvas.yview
        )

        self.canvas.configure(
            xscrollcommand=
                self.h_scroll.set,

            yscrollcommand=
                self.v_scroll.set
        )

        self.canvas.grid(
            row=0,
            column=0,
            sticky="nsew"
        )

        self.v_scroll.grid(
            row=0,
            column=1,
            sticky="ns"
        )

        self.h_scroll.grid(
            row=1,
            column=0,
            sticky="ew"
        )

        # ==================================================
        # EVENTS
        # ==================================================

        self.canvas.bind(
            "<Configure>",
            lambda event:
                self.redraw()
        )

        self.canvas.bind(
            "<Button-1>",
            self._timeline_clicked
        )

        self.canvas.bind(
            "<Shift-MouseWheel>",
            self._horizontal_wheel
        )

    # ======================================================
    # LAYERS
    # ======================================================

    def set_layers(
        self,
        layers
    ):

        self.layers = layers

        self.redraw()

    # ======================================================
    # DROP MEDIA
    # ======================================================

    def drop_asset_at_screen(
        self,
        file_path,
        x_root,
        y_root
    ):

        # Convert screen position into
        # visible Canvas coordinates.

        local_x = (
            x_root
            - self.canvas.winfo_rootx()
        )

        local_y = (
            y_root
            - self.canvas.winfo_rooty()
        )

        # Must actually be over the timeline.
        if not (
            0 <= local_x
            < self.canvas.winfo_width()
            and
            0 <= local_y
            < self.canvas.winfo_height()
        ):

            return False

        # Convert visible position into the
        # scrollable Canvas coordinate system.

        timeline_x = (
            self.canvas.canvasx(
                local_x
            )
        )

        timeline_y = (
            self.canvas.canvasy(
                local_y
            )
        )

        # Don't allow clips on the ruler.
        if (
            timeline_y
            < self.RULER_HEIGHT
        ):

            return False

        # ==================================================
        # FIND TRACK
        # ==================================================

        layer_index = int(
            (
                timeline_y
                - self.RULER_HEIGHT
            )
            // self.TRACK_HEIGHT
        )

        if not (
            0 <= layer_index
            < len(self.layers)
        ):

            return False

        # ==================================================
        # FIND START TIME
        # ==================================================

        start_time = max(
            0.0,

            timeline_x
            / self.pixels_per_second
        )

        # ==================================================
        # CREATE CLIP
        # ==================================================

        clip = MediaClip(
            file_path,
            start_time=start_time
        )

        layer = (
            self.layers[
                layer_index
            ]
        )

        layer.add_clip(
            clip
        )

        # Extend timeline if necessary.
        self.timeline_duration = max(
            self.timeline_duration,
            clip.end_time + 5.0
        )

        self.redraw()

        if (
            self.on_clip_added
            is not None
        ):

            self.on_clip_added(
                layer,
                clip
            )

        return True

    # ======================================================
    # PLAYHEAD CLICK
    # ======================================================

    def _timeline_clicked(
        self,
        event
    ):

        timeline_x = (
            self.canvas.canvasx(
                event.x
            )
        )

        new_time = (
            timeline_x
            / self.pixels_per_second
        )

        self.set_current_time(
            new_time
        )

    # ======================================================
    # SET CURRENT TIME
    # ======================================================

    def set_current_time(
        self,
        value
    ):

        self.current_time = max(
            0.0,

            min(
                float(value),
                self.timeline_duration
            )
        )

        self.time_label.configure(
            text=self._format_time(
                self.current_time,
                hundredths=True
            )
        )

        self.redraw()

        if (
            self.on_time_changed
            is not None
        ):

            self.on_time_changed(
                self.current_time
            )

    # ======================================================
    # ZOOM
    # ======================================================

    def zoom_in(self):

        self._set_zoom(
            min(
                400.0,
                self.pixels_per_second
                * 1.25
            )
        )

    def zoom_out(self):

        self._set_zoom(
            max(
                10.0,
                self.pixels_per_second
                / 1.25
            )
        )

    def _set_zoom(
        self,
        new_zoom
    ):

        # Keep the current center approximately
        # centered when zooming.

        center_x = (
            self.canvas.canvasx(
                self.canvas.winfo_width()
                / 2
            )
        )

        center_time = (
            center_x
            / self.pixels_per_second
        )

        self.pixels_per_second = (
            new_zoom
        )

        self.redraw()

        total_width = max(
            1.0,
            self.timeline_duration
            * self.pixels_per_second
        )

        desired_left = max(
            0.0,

            center_time
            * self.pixels_per_second
            - self.canvas.winfo_width()
            / 2
        )

        self.canvas.xview_moveto(
            min(
                1.0,
                desired_left
                / total_width
            )
        )

    # ======================================================
    # MOUSE WHEEL SCROLL
    # ======================================================

    def _horizontal_wheel(
        self,
        event
    ):

        self.canvas.xview_scroll(
            int(
                -event.delta
                / 120
            ),
            "units"
        )

    # ======================================================
    # REDRAW
    # ======================================================

    def redraw(self):

        self.canvas.delete(
            "all"
        )

        timeline_width = max(
            self.canvas.winfo_width(),

            self.timeline_duration
            * self.pixels_per_second
        )

        timeline_height = max(
            self.canvas.winfo_height(),

            self.RULER_HEIGHT
            + len(self.layers)
            * self.TRACK_HEIGHT
        )

        self.canvas.configure(
            scrollregion=(
                0,
                0,
                timeline_width,
                timeline_height
            )
        )

        self._draw_ruler(
            timeline_width
        )

        self._draw_tracks(
            timeline_width
        )

        self._draw_clips()

        self._draw_playhead(
            timeline_height
        )

    # ======================================================
    # RULER
    # ======================================================

    def _draw_ruler(
        self,
        width
    ):

        self.canvas.create_rectangle(
            0,
            0,
            width,
            self.RULER_HEIGHT,
            fill=PANEL_LIGHT,
            outline=BORDER
        )

        # Change ruler spacing based
        # on zoom level.

        if (
            self.pixels_per_second
            >= 80
        ):

            interval = 1

        elif (
            self.pixels_per_second
            >= 25
        ):

            interval = 5

        else:

            interval = 10

        second = 0

        while (
            second
            <= int(
                self.timeline_duration
            )
            + interval
        ):

            x = (
                second
                * self.pixels_per_second
            )

            self.canvas.create_line(
                x,
                18,
                x,
                self.RULER_HEIGHT,
                fill=TEXT_DIM
            )

            self.canvas.create_text(
                x + 3,
                3,
                text=self._format_time(
                    second
                ),
                anchor="nw",
                fill=TEXT_DIM
            )

            second += interval

    # ======================================================
    # TRACKS
    # ======================================================

    def _draw_tracks(
        self,
        width
    ):

        for (
            index,
            layer
        ) in enumerate(
            self.layers
        ):

            y0 = (
                self.RULER_HEIGHT
                + index
                * self.TRACK_HEIGHT
            )

            y1 = (
                y0
                + self.TRACK_HEIGHT
            )

            if (
                index % 2
                == 0
            ):

                fill = "#1d1d1d"

            else:

                fill = "#222222"

            self.canvas.create_rectangle(
                0,
                y0,
                width,
                y1,
                outline=BORDER,
                fill=fill
            )

            self.canvas.create_text(
                8,
                y0 + 5,
                text=layer.name,
                anchor="nw",
                fill=TEXT_DIM
            )

    # ======================================================
    # CLIPS
    # ======================================================

    def _draw_clips(self):

        for (
            layer_index,
            layer
        ) in enumerate(
            self.layers
        ):

            y0 = (
                self.RULER_HEIGHT
                + layer_index
                * self.TRACK_HEIGHT
                + 16
            )

            y1 = (
                self.RULER_HEIGHT
                + (
                    layer_index
                    + 1
                )
                * self.TRACK_HEIGHT
                - 5
            )

            for clip in layer.clips:

                x0 = (
                    clip.start_time
                    * self.pixels_per_second
                )

                x1 = (
                    clip.end_time
                    * self.pixels_per_second
                )

                if (
                    clip.media_type
                    == "video"
                ):

                    fill = "#315f86"

                    prefix = "VID "

                else:

                    fill = "#4f6b3a"

                    prefix = "IMG "

                self.canvas.create_rectangle(
                    x0,
                    y0,
                    x1,
                    y1,
                    outline=BORDER,
                    fill=fill,
                    width=2
                )

                self.canvas.create_text(
                    x0 + 6,
                    (
                        y0 + y1
                    ) / 2,
                    text=(
                        prefix
                        + clip.name
                    ),
                    anchor="w",
                    fill=TEXT
                )

    # ======================================================
    # PLAYHEAD
    # ======================================================

    def _draw_playhead(
        self,
        height
    ):

        x = (
            self.current_time
            * self.pixels_per_second
        )

        self.canvas.create_line(
            x,
            0,
            x,
            height,
            fill="#ff4040",
            width=2
        )

        self.canvas.create_polygon(
            x - 6,
            0,

            x + 6,
            0,

            x,
            9,

            fill="#ff4040",
            outline=""
        )

    # ======================================================
    # TIME FORMATTING
    # ======================================================

    @staticmethod
    def _format_time(
        seconds,
        hundredths=False
    ):

        minutes = int(
            seconds // 60
        )

        remaining_seconds = (
            seconds % 60
        )

        if hundredths:

            return (
                f"{minutes:02d}:"
                f"{remaining_seconds:05.2f}"
            )

        return (
            f"{minutes:02d}:"
            f"{int(remaining_seconds):02d}"
        )