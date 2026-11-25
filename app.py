import tkinter as tk
from tkinter import ttk

import cv2
from settings import (BG, PANEL, PANEL_LIGHT, BORDER, TEXT, TEXT_DIM, ACCENT, FONT,
                      WINDOW_WIDTH, WINDOW_HEIGHT, configure_ttk)
from camera_manager import CameraManager
from hand_tracker import HandTracker, HandMouseController
from workspace import Workspace
from editor_controller import EditorController
from gesture_controller import GestureController

# ============================================================
# MAIN APPLICATION
# ============================================================

class CameraViewerApp:

    def __init__(self, root):

        self.root = root
        self._closing = False
        self._update_frame_job = None

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

        self.gesture_controller = GestureController()

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

        self.editor = EditorController(
            self.workspace
        )
        self.root.bind_all(
            "<Delete>",
            self._delete_selected_from_keyboard
        )
        self.root.bind_all(
            "<BackSpace>",
            self._delete_selected_from_keyboard
        )
        self.root.bind_all(
            "<Control-z>",
            self._undo_from_keyboard
        )
        self.root.bind_all(
            "<Control-y>",
            self._redo_from_keyboard
        )
        self.root.bind_all(
            "<Control-Shift-Z>",
            self._redo_from_keyboard
        )
        self.root.bind_all(
            "<KeyRelease-space>",
            self._toggle_playback_from_keyboard
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

    def _delete_selected_from_keyboard(self, event):
        if self._is_text_entry_focused():
            return None

        self.editor.delete_selected()
        return "break"

    def _undo_from_keyboard(self, event):
        if self._is_text_entry_focused():
            return None

        self.workspace.timeline.undo()
        return "break"

    def _redo_from_keyboard(self, event):
        if self._is_text_entry_focused():
            return None

        self.workspace.timeline.redo()
        return "break"

    def _toggle_playback_from_keyboard(self, event):
        focused_widget = self.root.focus_get()
        if self._is_text_entry_focused() or isinstance(
            focused_widget,
            (tk.Button, ttk.Button)
        ):
            return None

        self.workspace.timeline.toggle_playback()
        return "break"

    def _is_text_entry_focused(self):
        focused_widget = self.root.focus_get()
        return isinstance(
            focused_widget,
            (tk.Entry, tk.Text, ttk.Entry, ttk.Combobox)
        )

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
        self._update_frame_job = None
        if self._closing:
            return

        # READ CAMERA
        # ========================================

        try:
            ret, frame = self.camera_manager.read_frame()
        except Exception as error:
            print("Camera read error:", error)
            ret, frame = False, None

        if not ret or frame is None:
            self.set_status("Camera frame unavailable")
            if not self._closing:
                self._update_frame_job = self.root.after(
                    30,
                    self.update_frame,
                )
            return

        # Mirror the camera
        try:
            frame = cv2.flip(frame, 1)
        except Exception as error:
            print("Camera frame error:", error)
            if not self._closing:
                self._update_frame_job = self.root.after(
                    30,
                    self.update_frame,
                )
            return

        # ========================================
        # HAND TRACKING
        # ========================================

        try:

            self.hand_tracker.process(frame)

            # ========================================
            # GESTURE LANDMARK SNAPSHOT
            # ========================================

            landmarks = self.hand_tracker.get_landmarks(
                frame
            )

            # ========================================
            # TOOL GESTURES
            # ========================================

            # ========================================
            # TOOL GESTURE DETECTION
            # ========================================

            detected_tool = (
                self.gesture_controller.detect_tool_gesture(
                    landmarks
                )
            )

            tool_state = (
                self.gesture_controller.update_tool_gesture(
                    detected_tool
                )
            )

            if tool_state["triggered"]:

                self.editor.select_tool(
                    tool_state["tool"]
                )

                self.set_status(
                    f"Gesture selected {tool_state['tool']} tool"
                )

                print(
                    "Tool selected:",
                    tool_state["tool"]
                )

            # ========================================
            # PINCH
            # ========================================

            pinch_clicked = (
                self.hand_tracker.detect_pinch(
                    frame
                )
            )

            # ========================================
            # POINTER
            # ========================================

            index_finger = (
                self.hand_tracker.get_index_finger(
                    frame
                )
            )

            if (
                index_finger is not None
                and detected_tool is None
            ):

                x, y = index_finger

                height, width = frame.shape[:2]

                self.hand_mouse.move(
                    x,
                    y,
                    width,
                    height
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

        self._update_frame_job = self.root.after(
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
        if self._closing:
            return

        self._closing = True

        if self._update_frame_job is not None:
            try:
                self.root.after_cancel(self._update_frame_job)
            except tk.TclError:
                pass
            self._update_frame_job = None

        if hasattr(self.workspace, "timeline"):
            try:
                self.workspace.timeline.pause_playback()
            except Exception as error:
                print("Shutdown: could not stop playback:", error)

        for window in list(
            getattr(
                self.workspace,
                "scene_separation_windows",
                [],
            )
        ):
            try:
                window._close()
            except Exception as error:
                print("Shutdown: could not close scene separation:", error)

        self.camera_manager.release()

        try:
            self.hand_tracker.close()
        except Exception as error:
            print("Shutdown: could not close hand tracker:", error)

        try:
            self.workspace.display.destroy()
        except Exception as error:
            print("Shutdown: could not destroy display:", error)

        self.root.destroy()
