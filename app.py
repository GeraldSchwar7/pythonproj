import tkinter as tk
from tkinter import ttk

import cv2
from settings import (
    BG,
    PANEL,
    PANEL_LIGHT,
    BORDER,
    TEXT,
    TEXT_DIM,
    ACCENT,
    ACCENT_HOVER,
    ACCENT_SOFT,
    SUCCESS,
    FONT,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    configure_ttk
)
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
        self.pinch_asset_drag_allowed = False
        self.hand_control_paused = False
        self.latest_hand_position = None
        self.last_frame_size = None
        self.hand_settings_window = None
        self._notification_label = None
        self._notification_job = None

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

        self.hand_mouse = HandMouseController(smoothing=0.45)

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
            self.root,
            on_status=self.set_status,
            on_hand_control_toggle=self.toggle_hand_control,
            on_calibrate=self.open_hand_control_settings
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
            "<Control-c>",
            self._copy_selected_from_keyboard
        )
        self.root.bind_all(
            "<Control-v>",
            self._paste_from_keyboard
        )
        self.root.bind_all(
            "<Control-Shift-Z>",
            self._redo_from_keyboard
        )
        self.root.bind_all(
            "<F8>",
            self._toggle_hand_control_from_keyboard
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

    def _copy_selected_from_keyboard(self, event):
        if self._is_text_entry_focused():
            return None

        if self.editor.copy_selected() is None:
            self.set_status("Select a clip to copy")
        return "break"

    def _paste_from_keyboard(self, event):
        if self._is_text_entry_focused():
            return None

        timeline = self.workspace.timeline
        position = timeline.last_mouse_timeline_position
        if position is None:
            layer = timeline.selected_layer
            if layer not in timeline.layers:
                self.set_status("Select a timeline layer to paste into")
                return "break"
            layer_index = timeline.layers.index(layer)
            position = (
                timeline.current_time * timeline.pixels_per_second,
                timeline.RULER_HEIGHT
                + layer_index * timeline.TRACK_HEIGHT
                + timeline.CLIP_TOP_PADDING
                + 1
            )

        self.editor.paste_at_position(*position)
        return "break"

    def _toggle_hand_control_from_keyboard(self, event):
        self.toggle_hand_control()
        return "break"

    def toggle_hand_control(self):
        self.set_hand_control_paused(not self.hand_control_paused)

    def set_hand_control_paused(self, paused):
        paused = bool(paused)
        if paused == self.hand_control_paused:
            return

        self.hand_control_paused = paused
        if paused:
            self.hand_mouse.disable()
            self.hand_tracker.cancel_pinch()
            self.gesture_controller.reset_tool_gesture()
            self.pinch_asset_drag_allowed = False
        else:
            self.hand_mouse.enable()

        self.workspace.timeline.set_hand_control_paused(paused)
        self.set_status(
            "Hand control paused" if paused else "Hand control resumed"
        )

    def open_hand_control_settings(self):
        if (
            self.hand_settings_window is not None
            and self.hand_settings_window.winfo_exists()
        ):
            self.hand_settings_window.lift()
            return

        previously_paused = self.hand_control_paused
        self.set_hand_control_paused(True)
        window = tk.Toplevel(self.root)
        self.hand_settings_window = window
        window.title("Hand Control Calibration")
        window.geometry("480x460")
        window.transient(self.root)
        window.configure(bg=PANEL)

        title = tk.Label(
            window,
            text="Hand Control Settings",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 13, "bold")
        )
        title.pack(anchor="w", padx=18, pady=(16, 8))

        settings_frame = tk.Frame(window, bg=PANEL)
        settings_frame.pack(fill="both", expand=True)
        self._hand_settings_vars = []

        def add_scale(row, label, lower, upper, value, formatter, callback):
            tk.Label(
                settings_frame,
                text=label,
                bg=PANEL,
                fg=TEXT_DIM,
                font=(FONT, 9)
            ).grid(row=row, column=0, sticky="w", padx=(18, 8), pady=6)
            value_label = tk.Label(
                settings_frame,
                text=formatter(value),
                bg=PANEL,
                fg=TEXT,
                font=(FONT, 9)
            )
            value_label.grid(row=row, column=2, sticky="e", padx=(8, 18))
            variable = tk.DoubleVar(master=window, value=value)
            self._hand_settings_vars.append(variable)

            def update(raw_value):
                number = float(raw_value)
                value_label.configure(text=formatter(number))
                callback(number)

            ttk.Scale(
                settings_frame,
                from_=lower,
                to=upper,
                variable=variable,
                command=update
            ).grid(row=row, column=1, sticky="ew", padx=8)

        settings_frame.grid_columnconfigure(1, weight=1)
        add_scale(
            1, "Cursor sensitivity", 0.5, 2.0,
            self.hand_mouse.sensitivity, lambda value: f"{value:.2f}x",
            self.hand_mouse.set_sensitivity
        )
        add_scale(
            2, "Cursor smoothing", 0.0, 1.0,
            self.hand_mouse.smoothing, lambda value: f"{value:.2f}",
            self.hand_mouse.set_smoothing
        )
        add_scale(
            3, "Pinch sensitivity", 0.6, 1.4,
            self.hand_tracker.pinch_sensitivity, lambda value: f"{value:.2f}x",
            self.hand_tracker.set_pinch_sensitivity
        )
        add_scale(
            4, "Drag movement threshold", 6.0, 40.0,
            self.hand_tracker.drag_movement_threshold,
            lambda value: f"{value:.0f} px",
            self.hand_tracker.set_drag_movement_threshold
        )

        calibration_label = tk.Label(
            settings_frame,
            text=(
                "Move your hand to the comfortable upper-left edge "
                "of your camera area."
            ),
            bg=PANEL,
            fg=TEXT_DIM,
            justify="left",
            wraplength=420,
            font=(FONT, 9)
        )
        calibration_label.grid(
            row=5,
            column=0,
            columnspan=3,
            sticky="w",
            padx=18,
            pady=(16, 8)
        )
        capture_state = {"points": [], "finished": False}
        capture_button = tk.Button(
            settings_frame,
            text="Capture upper-left",
            bg=ACCENT,
            fg=BG,
            activebackground=ACCENT_HOVER,
            activeforeground=BG,
            relief="flat",
            bd=0,
            cursor="hand2",
            font=(FONT, 9, "bold"),
            padx=12,
            pady=8
        )
        capture_button.grid(
            row=6,
            column=0,
            columnspan=3,
            sticky="ew",
            padx=18,
            pady=4
        )

        def close_settings():
            if not capture_state["finished"]:
                capture_state["finished"] = True
                self.hand_settings_window = None
                self.set_hand_control_paused(previously_paused)
                window.destroy()

        def capture_position():
            position = self.latest_hand_position
            frame_size = self.last_frame_size
            if position is None or frame_size is None:
                calibration_label.configure(
                    text="No hand detected. Show your hand to the camera and try again."
                )
                return

            capture_state["points"].append(position)
            if len(capture_state["points"]) == 1:
                calibration_label.configure(
                    text=(
                        "Now move to the comfortable lower-right edge "
                        "and capture again."
                    )
                )
                capture_button.configure(text="Capture lower-right")
                return

            first, second = capture_state["points"]
            if not self.hand_mouse.set_calibration_bounds(
                first,
                second,
                frame_size[0],
                frame_size[1]
            ):
                capture_state["points"].pop()
                calibration_label.configure(
                    text=(
                        "The points were too close together. Move farther "
                        "apart and capture the lower-right point again."
                    )
                )
                return

            capture_state["finished"] = True
            self.hand_settings_window = None
            self.set_hand_control_paused(previously_paused)
            self.set_status("Cursor area calibrated")
            window.destroy()

        capture_button.configure(command=capture_position)
        window.protocol("WM_DELETE_WINDOW", close_settings)
        window.bind("<Escape>", lambda event: close_settings())
        window.grab_set()

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
            height=70,
            highlightbackground=BORDER,
            highlightthickness=1
        )
        menu_frame.pack(fill="x")
        menu_frame.pack_propagate(False)

        brand = tk.Frame(menu_frame, bg=PANEL)
        brand.pack(side="left", padx=(18, 15), fill="y")

        tk.Label(
            brand,
            text="M",
            bg=ACCENT,
            fg=BG,
            width=2,
            height=1,
            font=(FONT, 15, "bold")
        ).pack(side="left", padx=(0, 11), pady=15)

        brand_text = tk.Frame(brand, bg=PANEL)
        brand_text.pack(side="left", fill="y")
        tk.Label(
            brand_text,
            text="MONDAY",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 14, "bold")
        ).pack(anchor="w", pady=(13, 0))
        tk.Label(
            brand_text,
            text="VIDEO STUDIO",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 7, "bold")
        ).pack(anchor="w", pady=(0, 12))

        separator = tk.Frame(menu_frame, bg=BORDER, width=1)
        separator.pack(side="left", fill="y", pady=14)

        tk.Label(
            menu_frame,
            text="GESTURE EDITOR",
            bg=ACCENT_SOFT,
            fg=ACCENT,
            font=(FONT, 8, "bold"),
            padx=11,
            pady=6
        ).pack(side="left", padx=18)

        camera_frame = tk.Frame(menu_frame, bg=PANEL_LIGHT)
        camera_frame.pack(side="right", padx=18, pady=14)

        tk.Label(
            camera_frame,
            text="CAMERA",
            bg=PANEL_LIGHT,
            fg=TEXT_DIM,
            font=(FONT, 8, "bold")
        ).pack(side="left", padx=(10, 7), pady=5)

        self.camera_dropdown = ttk.Combobox(
            camera_frame, textvariable=self.selected_camera,
            values=self.camera_list, state="readonly", width=7
        )
        self.camera_dropdown.pack(side="left", padx=(0, 7), pady=4)
        self.camera_dropdown.bind("<<ComboboxSelected>>", self.change_camera)

    # ========================================================
    # STATUS BAR
    # ========================================================

    def create_status_bar(self):

        status_frame = tk.Frame(
            self.root,
            bg=PANEL,
            height=34,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        status_frame.pack(
            fill="x"
        )

        tk.Label(
            status_frame,
            text="●",
            bg=PANEL,
            fg=SUCCESS,
            font=(FONT, 8)
        ).pack(side="left", padx=(14, 7), pady=7)

        self.status_label = tk.Label(
            status_frame,
            text="Status: Ready",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 9)
        )

        self.status_label.pack(
            side="left",
            pady=7
        )

        tk.Label(
            status_frame,
            text=(
                "GESTURE MODE  •  HOLD 2s TO SELECT  •  "
                "PINCH = CLICK  •  ASSET → TIMELINE = DRAG"
            ),
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 8, "bold")
        ).pack(side="right", padx=14, pady=7)

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
        self.latest_hand_position = None

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
            self.last_frame_size = (frame.shape[1], frame.shape[0])
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

            self._process_hand_controls(frame, landmarks)

            # frame = self.hand_tracker.draw(frame)

            index_finger = self.hand_tracker.get_index_finger(frame)
            self.latest_hand_position = index_finger
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

    def _process_hand_controls(self, frame, landmarks):
        if self.hand_control_paused:
            if self.hand_mouse.is_mouse_down:
                self.hand_mouse.mouse_up()
            self.pinch_asset_drag_allowed = False
            return

        detected_tool = self.gesture_controller.detect_tool_gesture(
            landmarks
        )
        pinch_state = self.hand_tracker.update_pinch(frame)

        tool_gesture = (
            detected_tool
            if detected_tool == "Select"
            else (
                None
                if pinch_state["pinching"] or pinch_state["dragging"]
                else detected_tool
            )
        )
        tool_state = self.gesture_controller.update_tool_gesture(
            tool_gesture
        )

        if tool_state["triggered"]:
            self.editor.select_tool(tool_state["tool"])
            self.set_status(
                f"Gesture selected {tool_state['tool']} tool"
            )
            print("Tool selected:", tool_state["tool"])

        if (
            tool_state["active"]
            and tool_state["progress"] >= 1.0
        ):
            pinch_state = self.hand_tracker.cancel_pinch()

        if pinch_state["pressed"]:
            self.pinch_asset_drag_allowed = (
                self.workspace.assets.contains_asset_at_screen(
                    self.hand_mouse.current_x,
                    self.hand_mouse.current_y
                )
            )
            if self.pinch_asset_drag_allowed:
                self.hand_mouse.mouse_down()
            else:
                self.hand_mouse.click()

        index_finger = self.hand_tracker.get_index_finger(frame)
        if (
            index_finger is not None
            and not pinch_state["pinching"]
            and not (
                pinch_state["dragging"]
                and self.hand_mouse.is_mouse_down
            )
        ):
            height, width = frame.shape[:2]
            self.hand_mouse.move(
                index_finger[0],
                index_finger[1],
                width,
                height
            )

        if (
            pinch_state["pinching"]
            and pinch_state["dragging"]
            and self.pinch_asset_drag_allowed
        ):
            if not self.hand_mouse.is_mouse_down:
                self.hand_mouse.mouse_down()
            height, width = frame.shape[:2]
            offset_x, offset_y = pinch_state["drag_offset"]
            self.hand_mouse.move_drag(
                offset_x,
                offset_y,
                width,
                height
            )

        if pinch_state["released"] or pinch_state["cancelled"]:
            if self.hand_mouse.is_mouse_down:
                self.hand_mouse.mouse_up()
                print("DRAG RELEASE")
            self.pinch_asset_drag_allowed = False

    # ========================================================
    # STATUS
    # ========================================================

    def set_status(self, message):

        self.status_label.configure(
            text=f"Status: {message}"
        )
        if (
            message.startswith("Gesture selected ")
            or message.endswith(" has been copied")
        ):
            self.show_notification(message)

    def show_notification(self, message):
        if self._closing:
            return

        if self._notification_job is not None:
            try:
                self.root.after_cancel(self._notification_job)
            except tk.TclError:
                pass
            self._notification_job = None

        if self._notification_label is not None:
            self._notification_label.destroy()

        self._notification_label = tk.Label(
            self.root,
            text=message,
            bg=PANEL_LIGHT,
            fg=TEXT,
            font=(FONT, 10, "bold"),
            padx=16,
            pady=9,
            relief="solid",
            bd=1
        )
        self._notification_label.place(
            relx=0.5,
            rely=1.0,
            y=-42,
            anchor="s"
        )
        self._notification_job = self.root.after(
            2400,
            self._dismiss_notification
        )

    def _dismiss_notification(self):
        self._notification_job = None
        if self._notification_label is not None:
            self._notification_label.destroy()
            self._notification_label = None

    # ========================================================
    # CLEANUP
    # ========================================================

    def on_close(self):
        if self._closing:
            return

        self._closing = True

        if self._notification_job is not None:
            try:
                self.root.after_cancel(self._notification_job)
            except tk.TclError:
                pass
            self._notification_job = None

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
            self.hand_mouse.mouse_up()
        except Exception as error:
            print("Shutdown: could not release mouse button:", error)

        try:
            self.hand_tracker.close()
        except Exception as error:
            print("Shutdown: could not close hand tracker:", error)

        try:
            self.workspace.display.destroy()
        except Exception as error:
            print("Shutdown: could not destroy display:", error)

        self.root.destroy()
