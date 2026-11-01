import os
import tkinter as tk

from tkinter import filedialog

import cv2

from PIL import (
    Image,
    ImageTk
)

from settings import (
    PANEL,
    PANEL_LIGHT,
    BORDER,
    TEXT
)

from media_clip import (
    IMAGE_EXTENSIONS,
    VIDEO_EXTENSIONS
)


class AssetBrowser(tk.Frame):

    def __init__(
        self,
        parent,
        on_asset_drop=None
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

        self.assets = []

        # Keep PhotoImage references alive.
        self.thumbnail_images = []

        self.on_asset_drop = (
            on_asset_drop
        )

        self.drag_path = None
        self.drag_ghost = None

        # ==================================================
        # TITLE
        # ==================================================

        tk.Label(
            self,
            text="Assets",
            bg=PANEL,
            fg=TEXT,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        # ==================================================
        # IMPORT BUTTON
        # ==================================================

        self.import_button = tk.Button(
            self,
            text="+ Import Media",
            command=self.import_media,
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=BORDER,
            activeforeground=TEXT,
            relief="flat"
        )

        self.import_button.pack(
            fill="x",
            padx=10,
            pady=(0, 10)
        )

        # ==================================================
        # THUMBNAILS
        # ==================================================

        self.thumbnail_frame = tk.Frame(
            self,
            bg=PANEL
        )

        self.thumbnail_frame.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=5
        )

    # ======================================================
    # IMPORT
    # ======================================================

    def import_media(self):

        files = (
            filedialog.askopenfilenames(
                title="Import Media",

                filetypes=[

                    (
                        "Supported Media",
                        "*.png *.jpg *.jpeg "
                        "*.bmp *.webp *.gif "
                        "*.mp4 *.mov *.avi "
                        "*.mkv *.webm *.m4v"
                    ),

                    (
                        "Image Files",
                        "*.png *.jpg *.jpeg "
                        "*.bmp *.webp *.gif"
                    ),

                    (
                        "Video Files",
                        "*.mp4 *.mov *.avi "
                        "*.mkv *.webm *.m4v"
                    ),

                    (
                        "All Files",
                        "*.*"
                    )
                ]
            )
        )

        for file_path in files:

            self.add_asset(
                file_path
            )

    # ======================================================
    # ADD ASSET
    # ======================================================

    def add_asset(
        self,
        file_path
    ):

        extension = (
            os.path.splitext(
                file_path
            )[1].lower()
        )

        supported = (
            extension
            in IMAGE_EXTENSIONS
            or extension
            in VIDEO_EXTENSIONS
        )

        if not supported:

            print(
                "Unsupported media:",
                file_path
            )

            return

        try:

            image = self._make_thumbnail(
                file_path,
                extension
            )

            thumbnail = (
                ImageTk.PhotoImage(
                    image
                )
            )

            self.thumbnail_images.append(
                thumbnail
            )

            self.assets.append(
                file_path
            )

            index = (
                len(self.assets)
                - 1
            )

            # ==================================================
            # ASSET CELL
            # ==================================================

            cell = tk.Frame(
                self.thumbnail_frame,
                bg=PANEL
            )

            cell.grid(
                row=index // 2,
                column=index % 2,
                padx=4,
                pady=4
            )

            button = tk.Button(
                cell,
                image=thumbnail,
                bg=PANEL_LIGHT,
                activebackground=BORDER,
                relief="flat",
                cursor="hand2"
            )

            button.pack()

            # ==================================================
            # MEDIA TYPE LABEL
            # ==================================================

            if (
                extension
                in VIDEO_EXTENSIONS
            ):

                media_type = "VIDEO"

            else:

                media_type = "IMAGE"

            tk.Label(
                cell,
                text=media_type,
                bg=PANEL,
                fg=TEXT,
                font=(
                    "Segoe UI",
                    7
                )
            ).pack()

            # ==================================================
            # DRAG EVENTS
            # ==================================================

            button.bind(
                "<ButtonPress-1>",
                lambda event,
                path=file_path:
                    self._start_drag(
                        event,
                        path
                    )
            )

            button.bind(
                "<B1-Motion>",
                self._drag_motion
            )

            button.bind(
                "<ButtonRelease-1>",
                self._finish_drag
            )

        except Exception as error:

            print(
                "Could not load media:",
                error
            )

    # ======================================================
    # CREATE THUMBNAIL
    # ======================================================

    def _make_thumbnail(
        self,
        file_path,
        extension
    ):

        # --------------------------------------------------
        # VIDEO
        # --------------------------------------------------

        if (
            extension
            in VIDEO_EXTENSIONS
        ):

            capture = cv2.VideoCapture(
                file_path
            )

            success, frame = (
                capture.read()
            )

            capture.release()

            if (
                not success
                or frame is None
            ):

                raise ValueError(
                    "Could not read video thumbnail."
                )

            frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB
            )

            image = Image.fromarray(
                frame
            )

        # --------------------------------------------------
        # IMAGE
        # --------------------------------------------------

        else:

            image = Image.open(
                file_path
            ).convert(
                "RGB"
            )

        image.thumbnail(
            (90, 70)
        )

        return image

    # ======================================================
    # START DRAG
    # ======================================================

    def _start_drag(
        self,
        event,
        file_path
    ):

        self.drag_path = (
            file_path
        )

        self._destroy_ghost()

        self.drag_ghost = (
            tk.Toplevel(
                self
            )
        )

        self.drag_ghost.overrideredirect(
            True
        )

        self.drag_ghost.attributes(
            "-topmost",
            True
        )

        tk.Label(
            self.drag_ghost,
            text=os.path.basename(
                file_path
            ),
            bg=PANEL_LIGHT,
            fg=TEXT,
            padx=8,
            pady=5,
            relief="solid",
            borderwidth=1
        ).pack()

        self._move_ghost(
            event.x_root,
            event.y_root
        )

    # ======================================================
    # DRAG
    # ======================================================

    def _drag_motion(
        self,
        event
    ):

        self._move_ghost(
            event.x_root,
            event.y_root
        )

    def _move_ghost(
        self,
        x_root,
        y_root
    ):

        if (
            self.drag_ghost
            is not None
        ):

            self.drag_ghost.geometry(
                f"+{x_root + 12}"
                f"+{y_root + 12}"
            )

    # ======================================================
    # FINISH DRAG
    # ======================================================

    def _finish_drag(
        self,
        event
    ):

        path = self.drag_path

        self.drag_path = None

        self._destroy_ghost()

        if (
            path
            and self.on_asset_drop
        ):

            self.on_asset_drop(
                path,
                event.x_root,
                event.y_root
            )

    # ======================================================
    # REMOVE DRAG LABEL
    # ======================================================

    def _destroy_ghost(self):

        if (
            self.drag_ghost
            is not None
        ):

            try:

                self.drag_ghost.destroy()

            except tk.TclError:

                pass

            self.drag_ghost = None