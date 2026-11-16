import tkinter as tk
from collections import OrderedDict

from tkinter import ttk

import cv2

from PIL import (
    Image,
    ImageTk
)

from settings import (
    PANEL,
    PANEL_LIGHT,
    PANEL_HOVER,
    PANEL_DEEP,
    BORDER,
    TEXT,
    TEXT_DIM,
    FONT,
    flat_button
)


# ============================================================
# DISPLAY PANEL
# ============================================================


class DisplayPanel(tk.Frame):

    def __init__(
        self,
        parent
    ):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        # ==================================================
        # VIEWPORT RENDER SCHEDULING
        # ==================================================

        self.pending_viewport_time = 0.0

        self.viewport_render_job = None

        # About 30 FPS.
        self.viewport_frame_delay = 33

        self._video_captures = {}
        self._video_decoder_frames = {}
        self._video_frame_cache = {}
        self._still_image_cache = OrderedDict()
        self._still_photo_cache = OrderedDict()

        # ==================================================
        # CAMERA WINDOW
        # ==================================================

        self.camera_window = None

        self.camera_window_display = None

        self.camera_display = None

        # ==================================================
        # BUILD UI
        # ==================================================

        self._create_header()

        self._create_tabs()

    # ======================================================
    # HEADER
    # ======================================================

    def _create_header(self):

        title_bar = tk.Frame(
            self,
            bg=PANEL
        )

        title_bar.pack(
            fill="x"
        )

        tk.Label(
            title_bar,
            text="PROGRAM MONITOR",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(
                "Segoe UI",
                9,
                "bold"
            )
        ).pack(
            side="left",
            padx=10,
            pady=7
        )

    # ======================================================
    # TABS
    # ======================================================

    def _create_tabs(self):

        self.notebook = (
            ttk.Notebook(
                self
            )
        )

        self.notebook.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        self.camera_tab = tk.Frame(
            self.notebook,
            bg=PANEL
        )

        self.viewport_tab = tk.Frame(
            self.notebook,
            bg=PANEL
        )

        self.notebook.add(
            self.camera_tab,
            text="Camera View"
        )

        self.notebook.add(
            self.viewport_tab,
            text="Viewport"
        )

        self._create_camera_tab()

        self._create_viewport_tab()

    # ======================================================
    # CAMERA TAB
    # ======================================================

    def _create_camera_tab(self):

        controls = tk.Frame(
            self.camera_tab,
            bg=PANEL
        )

        controls.pack(
            fill="x",
            padx=5,
            pady=5
        )

        self.pop_out_button = flat_button(
            controls, "↗  Pop Out", self.pop_out_camera
        )

        self.pop_out_button.pack(
            side="right"
        )

        self.camera_container = (
            tk.Frame(
                self.camera_tab,
                bg="black"
            )
        )

        self.camera_container.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        self.camera_display = (
            tk.Label(
                self.camera_container,
                bg="black"
            )
        )

        self.camera_display.pack(
            fill="both",
            expand=True
        )

    # ======================================================
    # VIEWPORT TAB
    # ======================================================

    def _create_viewport_tab(self):

        self.viewport_canvas = (
            tk.Canvas(
                self.viewport_tab,
                bg=PANEL_DEEP,
                highlightthickness=0
            )
        )

        self.viewport_canvas.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

        self.viewport_canvas.bind(
            "<Configure>",
            lambda event:
                self.render_viewport()
        )

        self.viewport_layers = []

        # Keep rendered Tkinter images alive.
        self.viewport_photos = []

        # Current project time.
        self.viewport_time = 0.0

    # ======================================================
    # VIEWPORT LAYERS
    # ======================================================

    def set_viewport_layers(
        self,
        layers
    ):

        self.viewport_layers = (
            layers
        )

        self.render_viewport()

    # ======================================================
    # VIEWPORT TIME
    # ======================================================

    def set_viewport_time(
        self,
        project_time
    ):
        self.pending_viewport_time = max(
            0.0,
            float(project_time)
        )

        if (self.viewport_render_job is not None):
            return

        self.viewport_render_job = (
            self.after(
                self.viewport_frame_delay,
                self._render_pending_viewport
            )
        )

    def _render_pending_viewport(self):

        # Allow another render to be scheduled.
        self.viewport_render_job = None

        # Render the newest requested time.
        self.viewport_time = self.pending_viewport_time

        self.render_viewport()

    # ======================================================
    # GET VIDEO FRAME
    # ======================================================

    def _get_video_frame(
        self,
        clip,
        viewport_width,
        viewport_height,
        layer_scale,
        layer_opacity
    ):

        capture = (
            self._video_captures.get(
                clip.file_path
            )
        )

        opened_capture = (
            capture is not None
            and capture.isOpened()
        )

        if (
            not opened_capture
        ):

            capture = (
                cv2.VideoCapture(
                    clip.file_path
                )
            )

            self._video_captures[
                clip.file_path
            ] = capture

            self._video_decoder_frames.pop(
                clip.file_path,
                None
            )
            self._video_frame_cache.pop(
                clip.file_path,
                None
            )

        if not capture.isOpened():

            return None

        # Determine position inside this clip.
        local_time = clip.local_time(
            self.viewport_time
        )

        # Prevent seeking beyond the source.
        local_time = min(
            local_time,

            max(
                0.0,
                clip.source_duration
                - 0.001
            )
        )

        fps = clip.fps if clip.fps > 0 else 30.0
        frame_index = int(local_time * fps)

        if clip.frame_count > 0:
            frame_index = min(
                frame_index,
                clip.frame_count - 1
            )

        cache_key = (
            frame_index,
            viewport_width,
            viewport_height,
            layer_scale,
            layer_opacity
        )
        cached_frame = self._video_frame_cache.get(
            clip.file_path
        )
        if cached_frame is not None and cached_frame[0] == cache_key:
            return cached_frame[1]

        last_frame_index = self._video_decoder_frames.get(
            clip.file_path
        )

        sequential = (
            last_frame_index is not None
            and 0 < frame_index - last_frame_index <= 2
        )

        if not sequential:
            seek_succeeded = capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                frame_index
            )

            if not seek_succeeded:
                self._video_decoder_frames.pop(
                    clip.file_path,
                    None
                )
                return None

            last_frame_index = frame_index - 1

        while last_frame_index < frame_index:
            success, frame = capture.read()

            if not success or frame is None:
                self._video_decoder_frames.pop(
                    clip.file_path,
                    None
                )
                self._video_frame_cache.pop(
                    clip.file_path,
                    None
                )
                return None

            last_frame_index += 1

        self._video_decoder_frames[clip.file_path] = frame_index

        frame_height, frame_width = frame.shape[:2]
        fit_scale = min(
            viewport_width / frame_width,
            viewport_height / frame_height
        ) * layer_scale
        new_size = (
            max(1, int(frame_width * fit_scale)),
            max(1, int(frame_height * fit_scale))
        )
        if new_size != (frame_width, frame_height):
            interpolation = (
                cv2.INTER_AREA
                if new_size[0] < frame_width
                or new_size[1] < frame_height
                else cv2.INTER_LINEAR
            )
            frame = cv2.resize(
                frame,
                new_size,
                interpolation=interpolation
            )

        # Resize the decoded BGR frame before color conversion to avoid
        # allocating and resampling a full-resolution RGBA image each frame.
        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )
        image = Image.fromarray(frame)
        if layer_opacity < 1.0:
            image.putalpha(
                int(255 * layer_opacity)
            )

        self._video_frame_cache[clip.file_path] = (
            cache_key,
            image
        )

        return image

    def _get_still_photo(
        self,
        clip,
        layer,
        viewport_width,
        viewport_height
    ):
        image = self._still_image_cache.get(clip.file_path)
        if image is None:
            with Image.open(clip.file_path) as source:
                image = source.convert("RGBA")

            self._still_image_cache[clip.file_path] = image
            while len(self._still_image_cache) > 8:
                self._still_image_cache.popitem(last=False)
        else:
            self._still_image_cache.move_to_end(clip.file_path)

        image_width, image_height = image.size
        scale = min(
            viewport_width / image_width,
            viewport_height / image_height
        ) * layer.scale
        new_size = (
            max(1, int(image_width * scale)),
            max(1, int(image_height * scale))
        )
        cache_key = (clip.file_path, new_size, layer.opacity)

        photo = self._still_photo_cache.get(cache_key)
        if photo is not None:
            self._still_photo_cache.move_to_end(cache_key)
            return photo

        image = image.resize(new_size, Image.Resampling.LANCZOS)
        if layer.opacity < 1.0:
            alpha = image.getchannel("A").point(
                lambda value: int(value * layer.opacity)
            )
            image.putalpha(alpha)

        photo = ImageTk.PhotoImage(image)
        self._still_photo_cache[cache_key] = photo
        while len(self._still_photo_cache) > 16:
            self._still_photo_cache.popitem(last=False)

        return photo

    # ======================================================
    # RENDER VIEWPORT
    # ======================================================

    def render_viewport(self):

        if not hasattr(
            self,
            "viewport_canvas"
        ):

            return

        self.viewport_canvas.delete(
            "all"
        )

        self.viewport_photos.clear()

        width = (
            self.viewport_canvas
            .winfo_width()
        )

        height = (
            self.viewport_canvas
            .winfo_height()
        )

        if (
            width <= 1
            or height <= 1
        ):

            return

        # ==================================================
        # FIND ACTIVE MEDIA
        # ==================================================

        active_layers = []

        # Reverse so lower layers are
        # rendered before upper layers.

        for layer in reversed(
            self.viewport_layers
        ):

            if not layer.visible:
                continue

            clip = (
                layer.get_clip_at_time(
                    self.viewport_time
                )
            )

            if clip is not None:

                active_layers.append(
                    (
                        layer,
                        clip
                    )
                )

        # ==================================================
        # NOTHING AT CURRENT TIME
        # ==================================================

        if not active_layers:

            self.viewport_canvas.create_text(
                width / 2,
                height / 2,

                text=(
                    "Move the timeline playhead "
                    "over a media clip\n"
                    "to show it in the viewport."
                ),

                fill=TEXT_DIM,

                font=(
                    "Segoe UI",
                    12
                ),

                justify="center"
            )

            return

        # ==================================================
        # RENDER ACTIVE LAYERS
        # ==================================================

        for (
            layer,
            clip
        ) in active_layers:

            try:

                # ------------------------------------------
                # VIDEO
                # ------------------------------------------

                if clip.media_type == "video":

                    image = (
                        self._get_video_frame(
                            clip,
                            width,
                            height,
                            layer.scale,
                            layer.opacity
                        )
                    )

                    if image is None:
                        continue

                    photo = ImageTk.PhotoImage(image)

                else:
                    photo = self._get_still_photo(
                        clip,
                        layer,
                        width,
                        height
                    )

                self.viewport_photos.append(
                    photo
                )

                # ------------------------------------------
                # POSITION
                # ------------------------------------------

                self.viewport_canvas.create_image(
                    width / 2
                    + layer.x,

                    height / 2
                    + layer.y,

                    image=photo,

                    anchor="center"
                )

            except Exception as error:

                print(
                    "Could not render "
                    "viewport clip:",
                    error
                )

    # ======================================================
    # POP OUT CAMERA
    # ======================================================

    def pop_out_camera(self):

        if (
            self.camera_window
            is not None
            and
            self.camera_window.winfo_exists()
        ):

            self.camera_window.lift()

            self.camera_window.focus_force()

            return

        # Hide embedded camera.
        self.camera_container.pack_forget()

        self.pop_out_button.configure(
            state="disabled"
        )

        # ==================================================
        # WINDOW
        # ==================================================

        self.camera_window = (
            tk.Toplevel(
                self
            )
        )

        self.camera_window.title(
            "Project Monday - Camera View"
        )

        self.camera_window.geometry(
            "800x600"
        )

        self.camera_window.minsize(
            400,
            300
        )

        self.camera_window.configure(
            bg=PANEL
        )

        self.camera_window.protocol(
            "WM_DELETE_WINDOW",
            self.add_camera_back
        )

        # ==================================================
        # WINDOW CONTROLS
        # ==================================================

        controls = tk.Frame(
            self.camera_window,
            bg=PANEL
        )

        controls.pack(
            fill="x"
        )

        tk.Label(
            controls,
            text="Camera View",
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

        tk.Button(
            controls,
            text="Add Back to Main Window",
            command=self.add_camera_back,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=PANEL_HOVER,
            activeforeground=TEXT,
            relief="flat"
        ).pack(
            side="right",
            padx=10,
            pady=5
        )

        # ==================================================
        # CAMERA DISPLAY
        # ==================================================

        self.camera_window_display = (
            tk.Label(
                self.camera_window,
                bg="black"
            )
        )

        self.camera_window_display.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

    # ======================================================
    # ADD CAMERA BACK
    # ======================================================

    def add_camera_back(self):

        if (
            self.camera_window
            is not None
        ):

            try:

                if (
                    self.camera_window
                    .winfo_exists()
                ):

                    self.camera_window.destroy()

            except tk.TclError:

                pass

        self.camera_window = None

        self.camera_window_display = None

        # Restore embedded camera.
        if (
            self.camera_container
            .winfo_manager()
            == ""
        ):

            self.camera_container.pack(
                fill="both",
                expand=True,
                padx=5,
                pady=(0, 5)
            )

        self.pop_out_button.configure(
            state="normal"
        )

    # ======================================================
    # LIVE CAMERA FRAME
    # ======================================================

    def display_frame(
        self,
        frame
    ):

        target = (
            self._get_camera_target()
        )

        if target is None:
            return

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        width = target.winfo_width()

        height = target.winfo_height()

        if (
            width <= 1
            or height <= 1
        ):

            return

        frame_height, frame_width = (
            frame.shape[:2]
        )

        # Preserve camera aspect ratio.
        scale = min(
            width
            / frame_width,

            height
            / frame_height
        )

        new_width = max(
            1,
            int(
                frame_width
                * scale
            )
        )

        new_height = max(
            1,
            int(
                frame_height
                * scale
            )
        )

        frame = cv2.resize(
            frame,
            (
                new_width,
                new_height
            )
        )

        image = Image.fromarray(
            frame
        )

        photo = ImageTk.PhotoImage(
            image=image
        )

        # Keep reference alive.
        target.image = photo

        target.configure(
            image=photo
        )

    # ======================================================
    # CAMERA TARGET
    # ======================================================

    def _get_camera_target(self):

        if (
            self.camera_window
            is not None
        ):

            try:

                if (
                    self.camera_window
                    .winfo_exists()
                ):

                    return (
                        self.camera_window_display
                    )

            except tk.TclError:

                self.camera_window = None

                self.camera_window_display = None

        return self.camera_display