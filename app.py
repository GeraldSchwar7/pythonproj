import tkinter as tk
from tkinter import ttk

import cv2
from settings import (BG, PANEL, PANEL_LIGHT, BORDER, TEXT, TEXT_DIM, ACCENT, FONT,
                      WINDOW_WIDTH, WINDOW_HEIGHT, configure_ttk)
from camera_manager import CameraManager
from hand_tracker import HandTracker, HandMouseController
from workspace import Workspace

# ============================================================
# MAIN APPLICATION
# ============================================================

class CameraViewerApp:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "Project Monday"
        )

        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )

        self.root.minsize(
            900,
            600
        )

        self.root.configure(
            bg=BG
        )

        configure_ttk(self.root)

        # --------------------------------
        # Camera
        # --------------------------------

        self.camera_manager = CameraManager()

        self.hand_tracker = HandTracker()

        self.hand_mouse = HandMouseController(smoothing=0.75)

        self.camera_list = (
            self.camera_manager.find_available_cameras()
        )

        if not self.camera_list:
            self.camera_list = [0]

        self.selected_camera = tk.IntVar(
            value=self.camera_list[0]
        )

        # --------------------------------
        # UI
        # --------------------------------

        self.create_menu()

        self.workspace = Workspace(
            self.root
        )

        self.workspace.pack(
            fill="both",
            expand=True
        )

        self.create_status_bar()

        # --------------------------------
        # Start camera
        # --------------------------------

        self.change_camera()

        # --------------------------------
        # Cleanup
        # --------------------------------

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self.update_frame()

    # ========================================================
    # MENU
    # ========================================================

    def create_menu(self):

        menu_frame = tk.Frame(
            self.root,
            bg=PANEL,
            height=58,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        menu_frame.pack(fill="x")
        menu_frame.pack_propagate(False)

        brand = tk.Frame(menu_frame, bg=PANEL)
        brand.pack(side="left", padx=16, fill="y")

        tk.Label(
            brand, text="PROJECT", bg=PANEL, fg=TEXT_DIM,
            font=(FONT, 8, "bold")
        ).pack(anchor="w", pady=(9, 0))

        tk.Label(
            brand, text="MONDAY", bg=PANEL, fg=TEXT,
            font=(FONT, 15, "bold")
        ).pack(anchor="w", pady=(0, 7))

        separator = tk.Frame(menu_frame, bg=ACCENT, width=3)
        separator.pack(side="left", fill="y", pady=12)

        tk.Label(
            menu_frame, text="Gesture Video Workspace", bg=PANEL, fg=TEXT_DIM,
            font=(FONT, 9)
        ).pack(side="left", padx=12)

        camera_frame = tk.Frame(menu_frame, bg=PANEL)
        camera_frame.pack(side="right", padx=16)

        tk.Label(
            camera_frame, text="CAMERA", bg=PANEL, fg=TEXT_DIM,
            font=(FONT, 8, "bold")
        ).pack(side="left", padx=(0, 8))

        self.camera_dropdown = ttk.Combobox(
            camera_frame, textvariable=self.selected_camera,
            values=self.camera_list, state="readonly", width=6
        )
        self.camera_dropdown.pack(side="left")
        self.camera_dropdown.bind("<<ComboboxSelected>>", self.change_camera)

    # ========================================================
    # STATUS BAR
    # ========================================================

    def create_status_bar(self):

        status_frame = tk.Frame(
            self.root,
            bg=PANEL,
            height=30,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        status_frame.pack(
            fill="x"
        )

        tk.Label(
            status_frame, text="●", bg=PANEL, fg="#48c78e",
            font=(FONT, 8)
        ).pack(side="left", padx=(14, 5), pady=5)

        self.status_label = tk.Label(
            status_frame,
            text="Status: Ready",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9)
        )

        self.status_label.pack(
            side="left",
            pady=5
        )

        tk.Label(
            status_frame, text="HAND CONTROL  •  PINCH TO CLICK",
            bg=PANEL, fg=TEXT_DIM, font=(FONT, 8, "bold")
        ).pack(side="right", padx=14, pady=5)

    # ========================================================
    # CAMERA
    # ========================================================

    def change_camera(self, event=None):

        camera_index = (
            self.selected_camera.get()
        )

        success = (
            self.camera_manager.open_camera(
                camera_index
            )
        )

        if success:

            self.set_status(
                f"Camera {camera_index} connected"
            )

        else:

            self.set_status(
                f"Unable to open camera {camera_index}"
            )

    # ========================================================
    # UPDATE CAMERA
    # ========================================================

    def update_frame(self):

        # ========================================
        # READ CAMERA
        # ========================================

        ret, frame = self.camera_manager.read_frame()

        if not ret or frame is None:
            self.set_status("Camera frame unavailable")
            self.root.after(30, self.update_frame)
            return

        # Mirror the camera
        frame = cv2.flip(frame, 1)

        # ========================================
        # HAND TRACKING
        # ========================================

        try:

            self.hand_tracker.process(frame)

            index_finger = (
                self.hand_tracker.get_index_finger(frame)
            )

            if index_finger is not None:

                x, y = index_finger

                height, width = frame.shape[:2]

                # -----------------------------
                # Move mouse
                # -----------------------------

                self.hand_mouse.move(
                    x,
                    y,
                    width,
                    height
                )

                # -----------------------------
                # Detect pinch
                # -----------------------------

                pinch_clicked = (
                    self.hand_tracker.detect_pinch(
                        frame
                    )
                )

                if pinch_clicked:

                    self.hand_mouse.click()

                    print("CLICK")

            # frame = self.hand_tracker.draw(frame)

            index_finger = self.hand_tracker.get_index_finger(frame)
            thumb = self.hand_tracker.get_thumb(frame)

            if index_finger is not None:

                cv2.circle(
                    frame,
                    index_finger,
                    6,
                    (0, 255, 0),
                    -1
                )

            if thumb is not None:

                cv2.circle(
                    frame,
                    thumb,
                    6,
                    (0, 255, 255),
                    -1
                )

        except Exception as error:

            # IMPORTANT:
            # Hand tracking can fail without stopping
            # the camera feed.
            print(
                "Hand tracking error:",
                error
            )

        # ========================================
        # DISPLAY CAMERA
        # ========================================

        try:

            self.workspace.display.display_frame(
                frame
            )

        except Exception as error:

            print(
                "Display error:",
                error
            )

        # ========================================
        # NEXT FRAME
        # ========================================

        self.root.after(
            15,
            self.update_frame
        )
    # ========================================================
    # STATUS
    # ========================================================

    def set_status(self, message):

        self.status_label.configure(
            text=f"Status: {message}"
        )

    # ========================================================
    # CLEANUP
    # ========================================================

    def on_close(self):

        self.camera_manager.release()

        self.hand_tracker.close()

        self.root.destroy()
