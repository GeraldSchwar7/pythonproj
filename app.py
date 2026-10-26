import tkinter as tk
from tkinter import ttk

import cv2
from settings import BG, PANEL, TEXT, TEXT_DIM, WINDOW_WIDTH, WINDOW_HEIGHT
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

        # --------------------------------
        # Camera
        # --------------------------------

        self.camera_manager = CameraManager()

        self.hand_tracker = HandTracker()

        self.hand_mouse = HandMouseController( smoothing=0.25)

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
            height=42
        )

        menu_frame.pack(
            fill="x"
        )

        tk.Label(
            menu_frame,
            text="Project Monday",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 14, "bold")
        ).pack(
            side="left",
            padx=12,
            pady=7
        )

        camera_frame = tk.Frame(
            menu_frame,
            bg=PANEL
        )

        camera_frame.pack(
            side="right",
            padx=10
        )

        tk.Label(
            camera_frame,
            text="Camera:",
            bg=PANEL,
            fg=TEXT
        ).pack(
            side="left"
        )

        self.camera_dropdown = ttk.Combobox(
            camera_frame,
            textvariable=self.selected_camera,
            values=self.camera_list,
            state="readonly",
            width=5
        )

        self.camera_dropdown.pack(
            side="left",
            padx=5
        )

        self.camera_dropdown.bind(
            "<<ComboboxSelected>>",
            self.change_camera
        )

    # ========================================================
    # STATUS BAR
    # ========================================================

    def create_status_bar(self):

        status_frame = tk.Frame(
            self.root,
            bg=PANEL,
            height=28
        )

        status_frame.pack(
            fill="x"
        )

        self.status_label = tk.Label(
            status_frame,
            text="Status: Ready",
            bg=PANEL,
            fg=TEXT_DIM
        )

        self.status_label.pack(
            side="left",
            padx=10,
            pady=4
        )

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

                self.hand_mouse.move(
                    x,
                    y,
                    width,
                    height
                )

            frame = self.hand_tracker.draw(frame)

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
