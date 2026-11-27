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
    PANEL_HOVER,
    PANEL_DEEP,
    BORDER,
    TEXT,
    TEXT_DIM,
    FONT,
    flat_button,
    panel_title
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
        self.asset_buttons = []

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

        header = tk.Frame(self, bg=PANEL)
        header.pack(fill="x", padx=13, pady=(12, 3))
        panel_title(header, "Media Library").pack(side="left")
        self.asset_count_label = tk.Label(
            header,
            text="0 ITEMS",
            bg=PANEL_LIGHT,
            fg=TEXT_DIM,
            font=(FONT, 7, "bold"),
            padx=7,
            pady=3
        )
        self.asset_count_label.pack(side="right")

        tk.Label(
            self,
            text="Import media, then drag it into your timeline.",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 8),
            wraplength=190,
            justify="left"
        ).pack(anchor="w", padx=13, pady=(0, 9))

        # ==================================================
        # IMPORT BUTTON
        # ==================================================

        self.import_button = flat_button(
            self,
            "+  Import Media",
            self.import_media,
            accent=True
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
        self.thumbnail_frame.grid_columnconfigure(0, weight=1)
        self.thumbnail_frame.grid_columnconfigure(1, weight=1)

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
            asset_count = len(self.assets)
            self.asset_count_label.configure(
                text=(
                    f"{asset_count} ITEM"
                    f"{'S' if asset_count != 1 else ''}"
                )
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
                bg=PANEL_LIGHT,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            cell.grid(
                row=index // 2,
                column=index % 2,
                padx=5,
                pady=5,
                sticky="nsew"
            )

            button = tk.Button(
                cell,
                image=thumbnail,
                bg=PANEL_DEEP,
                activebackground=PANEL_HOVER,
                relief="flat",
                cursor="hand2",
                bd=0,
                highlightthickness=1,
                highlightbackground=BORDER
            )
            self.asset_buttons.append(button)

            button.pack()

            # ==================================================
            # FILE NAME LABEL
            # ==================================================

            tk.Label(
                cell,
                text=os.path.basename(file_path),
                bg=PANEL_LIGHT,
                fg=TEXT,
                font=(
                    FONT,
                    8
                ),
                width=16,
                wraplength=100,
                justify="center",
                pady=5
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

            with Image.open(file_path) as source:
                image = source.convert("RGB")

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

    def contains_asset_at_screen(self, x, y):
        for button in self.asset_buttons:
            if not button.winfo_exists():
                continue

            left = button.winfo_rootx()
            top = button.winfo_rooty()
            if (
                left <= x < left + button.winfo_width()
                and top <= y < top + button.winfo_height()
            ):
                return True

        return False

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