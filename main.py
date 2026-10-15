
import tkinter as tk
from tkinter import ttk

import cv2
from PIL import Image, ImageTk


# ============================================================
# Application Settings
# ============================================================

BG = "#1e1e1e"
PANEL = "#252526"
BORDER = "#3c3c3c"
TEXT = "white"

WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700

PREVIEW_WIDTH = 640
PREVIEW_HEIGHT = 480


# ============================================================
# Camera Manager
# Handles camera detection, opening, switching, and reading.
# ============================================================

class CameraManager:

    def __init__(self):
        self.cap = None
        self.camera_index = None

    def find_available_cameras(self, max_cameras=10):
        cameras = []

        for index in range(max_cameras):
            cap = cv2.VideoCapture(index)

            if cap.isOpened():
                ret, _ = cap.read()

                if ret:
                    cameras.append(index)

            cap.release()

        return cameras

    def open_camera(self, camera_index):
        self.release()

        self.camera_index = camera_index
        self.cap = cv2.VideoCapture(camera_index)

        return self.cap.isOpened()

    def read_frame(self):
        if self.cap is None:
            return False, None

        if not self.cap.isOpened():
            return False, None

        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None


# ============================================================
# Camera Preview
# Responsible only for displaying camera frames.
# ============================================================

class CameraPreview(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg="black")

        self.video_label = tk.Label(
            self,
            bg="black"
        )

        self.video_label.pack(
            fill="both",
            expand=True
        )

    def display_frame(self, frame):

        # OpenCV uses BGR.
        # Pillow/Tkinter expects RGB.
        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        frame = cv2.resize(
            frame,
            (PREVIEW_WIDTH, PREVIEW_HEIGHT)
        )

        image = Image.fromarray(frame)

        photo = ImageTk.PhotoImage(
            image=image
        )

        # Keep a reference so Tkinter does not garbage collect it.
        self.video_label.image = photo

        self.video_label.configure(
            image=photo
        )


# ============================================================
# Inspector Panel
# ============================================================

class InspectorPanel(tk.Frame):

    def __init__(self, parent):
        super().__init__(
            parent,
            bg=PANEL,
            width=250
        )

        self.pack_propagate(False)

        title = tk.Label(
            self,
            text="Inspector",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        )

        title.pack(pady=10)


# ============================================================
# Timeline Panel
# ============================================================

class TimelinePanel(tk.Frame):

    def __init__(self, parent):
        super().__init__(
            parent,
            bg=PANEL,
            height=150
        )

        self.pack_propagate(False)

        title = tk.Label(
            self,
            text="Timeline",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        )

        title.pack(
            anchor="w",
            padx=10,
            pady=10
        )


# ============================================================
# Main Application
# ============================================================

class CameraViewerApp:

    def __init__(self, root):

        self.root = root

        self.root.title("Project Monday")

        self.root.geometry(
            f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}"
        )

        self.root.configure(bg=BG)

        self.root.resizable(
            True,
            True
        )

        # --------------------------------
        # Camera system
        # --------------------------------

        self.camera_manager = CameraManager()

        self.camera_list = (
            self.camera_manager.find_available_cameras()
        )

        if not self.camera_list:
            self.camera_list = [0]

        self.selected_camera = tk.IntVar(
            value=self.camera_list[0]
        )

        # --------------------------------
        # Build interface
        # --------------------------------

        self.create_menu()
        self.create_main_area()
        self.create_timeline()
        self.create_status_bar()

        # --------------------------------
        # Start camera
        # --------------------------------

        self.change_camera()

        # --------------------------------
        # Window cleanup
        # --------------------------------

        self.root.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        # Start preview loop
        self.update_frame()

    # ========================================================
    # Menu
    # ========================================================

    def create_menu(self):

        self.menu_frame = tk.Frame(
            self.root,
            bg=PANEL,
            height=40
        )

        self.menu_frame.pack(
            fill="x"
        )

        title = tk.Label(
            self.menu_frame,
            text="Project Monday",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 14, "bold")
        )

        title.pack(
            side="left",
            padx=10
        )

        # Camera controls

        camera_frame = tk.Frame(
            self.menu_frame,
            bg=PANEL
        )

        camera_frame.pack(
            side="right",
            padx=10
        )

        camera_label = tk.Label(
            camera_frame,
            text="Camera:",
            bg=PANEL,
            fg=TEXT
        )

        camera_label.pack(
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
    # Main Workspace
    # ========================================================

    class Workspace(tk.Frame):

        def __init__(self, parent):
            super().__init__(parent, bg=BG)

            # Make the center/display area expand the most
            self.grid_columnconfigure(0, weight=1)
            self.grid_columnconfigure(1, weight=4)
            self.grid_columnconfigure(2, weight=1)

            self.grid_rowconfigure(0, weight=4)
            self.grid_rowconfigure(1, weight=2)

            # -------------------------
            # Asset Browser
            # -------------------------

            self.assets = AssetBrowser(self)

            self.assets.grid(
                row=0,
                column=0,
                sticky="nsew",
                padx=4,
                pady=4
            )

            # -------------------------
            # Main Display
            # -------------------------

            self.display = DisplayPanel(self)

            self.display.grid(
                row=0,
                column=1,
                columnspan=2,
                sticky="nsew",
                padx=4,
                pady=4
            )

            # -------------------------
            # Tools
            # -------------------------

            self.tools = ToolPanel(self)

            self.tools.grid(
                row=1,
                column=0,
                sticky="nsew",
                padx=4,
                pady=4
            )

            # -------------------------
            # Timeline
            # -------------------------

            self.timeline = TimelinePanel(self)

            self.timeline.grid(
                row=1,
                column=1,
                sticky="nsew",
                padx=4,
                pady=4
            )

            # -------------------------
            # Layers
            # -------------------------

            self.layers = LayerPanel(self)

            self.layers.grid(
                row=1,
                column=2,
                sticky="nsew",
                padx=4,
                pady=4
            )

    # ========================================================
    # Timeline
    # ========================================================

    def create_timeline(self):

        self.timeline = TimelinePanel(
            self.root
        )

        self.timeline.pack(
            fill="x",
            padx=5,
            pady=5
        )

    # ========================================================
    # Status Bar
    # ========================================================

    def create_status_bar(self):

        self.status_frame = tk.Frame(
            self.root,
            bg=PANEL,
            height=30
        )

        self.status_frame.pack(
            fill="x"
        )

        self.status_label = tk.Label(
            self.status_frame,
            text="Status: Ready",
            bg=PANEL,
            fg="lightgray"
        )

        self.status_label.pack(
            side="left",
            padx=10
        )

    # ========================================================
    # Camera Control
    # ========================================================

    def change_camera(self, event=None):

        camera_index = self.selected_camera.get()

        success = self.camera_manager.open_camera(
            camera_index
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
    # Camera Update Loop
    # ========================================================

    def update_frame(self):

        ret, frame = (
            self.camera_manager.read_frame()
        )

        if ret:

            self.preview.display_frame(
                frame
            )

        self.root.after(
            15,
            self.update_frame
        )

    # ========================================================
    # Status
    # ========================================================

    def set_status(self, message):

        self.status_label.configure(
            text=f"Status: {message}"
        )

    # ========================================================
    # Cleanup
    # ========================================================

    def on_close(self):

        self.camera_manager.release()

        self.root.destroy()


# ============================================================
# Program Entry Point
# ============================================================

def main():

    root = tk.Tk()

    CameraViewerApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
