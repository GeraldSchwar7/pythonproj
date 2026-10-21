
import tkinter as tk
from tkinter import ttk, filedialog
import cv2
from PIL import Image, ImageTk


# ============================================================
# SETTINGS
# ============================================================

BG = "#1e1e1e"
PANEL = "#252526"
PANEL_LIGHT = "#2d2d30"
BORDER = "#3c3c3c"
TEXT = "white"
TEXT_DIM = "#bdbdbd"

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800


# ============================================================
# CAMERA MANAGER
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
# DISPLAY PANEL
# Camera / image / composite display
# ============================================================

class DisplayPanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        title_bar = tk.Frame(
            self,
            bg=PANEL
        )

        title_bar.pack(
            fill="x"
        )

        tk.Label(
            title_bar,
            text="Display",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            side="left",
            padx=10,
            pady=7
        )

        self.display = tk.Label(
            self,
            bg="black"
        )

        self.display.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

    def display_frame(self, frame):

        frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        # Get actual available display size
        width = self.display.winfo_width()
        height = self.display.winfo_height()

        if width <= 1 or height <= 1:
            return

        frame_height, frame_width = frame.shape[:2]

        # Preserve camera aspect ratio
        scale = min(
            width / frame_width,
            height / frame_height
        )

        new_width = max(
            1,
            int(frame_width * scale)
        )

        new_height = max(
            1,
            int(frame_height * scale)
        )

        frame = cv2.resize(
            frame,
            (new_width, new_height)
        )

        image = Image.fromarray(frame)

        photo = ImageTk.PhotoImage(
            image=image
        )

        self.display.image = photo

        self.display.configure(
            image=photo
        )


# ============================================================
# ASSET BROWSER
# ============================================================

class AssetBrowser(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.images = []
        self.thumbnail_images = []

        tk.Label(
            self,
            text="Assets",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        self.import_button = tk.Button(
            self,
            text="+ Import Images",
            command=self.import_images,
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

        # Container for thumbnails
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

    def import_images(self):

        files = filedialog.askopenfilenames(
            title="Import Images",
            filetypes=[
                (
                    "Image Files",
                    "*.png *.jpg *.jpeg *.bmp *.webp"
                )
            ]
        )

        for file_path in files:
            self.add_image(file_path)

    def add_image(self, file_path):

        try:

            image = Image.open(file_path)
            image.thumbnail((80, 80))

            thumbnail = ImageTk.PhotoImage(image)

            self.thumbnail_images.append(thumbnail)
            self.images.append(file_path)

            index = len(self.images) - 1

            row = index // 2
            column = index % 2

            button = tk.Button(
                self.thumbnail_frame,
                image=thumbnail,
                bg=PANEL_LIGHT,
                activebackground=BORDER,
                relief="flat"
            )

            button.grid(
                row=row,
                column=column,
                padx=4,
                pady=4
            )

        except Exception as error:

            print(
                "Could not load image:",
                error
            )


# ============================================================
# TOOLS PANEL
# ============================================================

class ToolPanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.current_tool = "Select"

        tk.Label(
            self,
            text="Tools",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        tools = [
            "Select",
            "Move",
            "Copy",
            "Resize",
            "Cut",
            "Camera View"
        ]

        for tool in tools:

            button = tk.Button(
                self,
                text=tool,
                command=lambda t=tool: self.select_tool(t),
                bg=PANEL_LIGHT,
                fg=TEXT,
                activebackground=BORDER,
                activeforeground=TEXT,
                relief="flat"
            )

            button.pack(
                fill="x",
                padx=10,
                pady=3
            )

    def select_tool(self, tool):

        self.current_tool = tool

        print(
            "Selected tool:",
            tool
        )


# ============================================================
# LAYER MODEL
# ============================================================

class Layer:

    def __init__(self, name, image=None):

        self.name = name
        self.image = image

        self.visible = True

        self.x = 0
        self.y = 0

        self.scale = 1.0
        self.opacity = 1.0


# ============================================================
# LAYERS PANEL
# ============================================================

class LayerPanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        self.layers = []

        tk.Label(
            self,
            text="Layers",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 11, "bold")
        ).pack(
            anchor="w",
            padx=10,
            pady=7
        )

        self.layer_list = tk.Listbox(
            self,
            bg="#181818",
            fg=TEXT,
            selectbackground="#094771",
            selectforeground=TEXT,
            borderwidth=0,
            highlightthickness=0
        )

        self.layer_list.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=5
        )

        controls = tk.Frame(
            self,
            bg=PANEL
        )

        controls.pack(
            fill="x",
            padx=8,
            pady=8
        )

        tk.Button(
            controls,
            text="+",
            width=3,
            command=self.create_layer
        ).pack(
            side="left"
        )

        tk.Button(
            controls,
            text="-",
            width=3,
            command=self.delete_selected_layer
        ).pack(
            side="left",
            padx=4
        )

        # Default layer structure from the sketch
        self.add_layer("Foreground")
        self.add_layer("Midground")
        self.add_layer("Background")

    def add_layer(self, name, image=None):

        layer = Layer(
            name,
            image
        )

        # Insert new layers at top
        self.layers.insert(
            0,
            layer
        )

        self.refresh()

    def create_layer(self):

        number = len(self.layers) + 1

        self.add_layer(
            f"Layer {number}"
        )

    def delete_selected_layer(self):

        selection = self.layer_list.curselection()

        if not selection:
            return

        index = selection[0]

        del self.layers[index]

        self.refresh()

    def refresh(self):

        self.layer_list.delete(
            0,
            tk.END
        )

        for layer in self.layers:

            visibility = "●" if layer.visible else "○"

            self.layer_list.insert(
                tk.END,
                f"{visibility}  {layer.name}"
            )


# ============================================================
# TIMELINE PANEL
# ============================================================

class TimelinePanel(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

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
            font=("Segoe UI", 11, "bold")
        ).pack(
            side="left",
            padx=10,
            pady=7
        )

        self.canvas = tk.Canvas(
            self,
            bg="#181818",
            highlightthickness=0
        )

        self.canvas.pack(
            fill="both",
            expand=True,
            padx=5,
            pady=(0, 5)
        )

        # Draw placeholder timeline tracks
        self.canvas.create_line(
            0,
            35,
            1000,
            35,
            fill=BORDER
        )

        self.canvas.create_line(
            0,
            70,
            1000,
            70,
            fill=BORDER
        )

        self.canvas.create_line(
            0,
            105,
            1000,
            105,
            fill=BORDER
        )


# ============================================================
# WORKSPACE
# ============================================================

class Workspace(tk.Frame):

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=BG
        )

        # Left column
        self.grid_columnconfigure(
            0,
            weight=1,
            minsize=220
        )

        # Main display / timeline
        self.grid_columnconfigure(
            1,
            weight=4
        )

        # Layer panel
        self.grid_columnconfigure(
            2,
            weight=1,
            minsize=220
        )

        # Display row
        self.grid_rowconfigure(
            0,
            weight=4
        )

        # Bottom editor row
        self.grid_rowconfigure(
            1,
            weight=2
        )

        # --------------------------------
        # Assets
        # --------------------------------

        self.assets = AssetBrowser(
            self
        )

        self.assets.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Display
        # --------------------------------

        self.display = DisplayPanel(
            self
        )

        self.display.grid(
            row=0,
            column=1,
            columnspan=2,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Tools
        # --------------------------------

        self.tools = ToolPanel(
            self
        )

        self.tools.grid(
            row=1,
            column=0,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Timeline
        # --------------------------------

        self.timeline = TimelinePanel(
            self
        )

        self.timeline.grid(
            row=1,
            column=1,
            sticky="nsew",
            padx=3,
            pady=3
        )

        # --------------------------------
        # Layers
        # --------------------------------

        self.layers = LayerPanel(
            self
        )

        self.layers.grid(
            row=1,
            column=2,
            sticky="nsew",
            padx=3,
            pady=3
        )


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

        ret, frame = (
            self.camera_manager.read_frame()
        )

        if ret:

            # IMPORTANT:
            # Camera now goes to workspace.display,
            # not self.preview.
            self.workspace.display.display_frame(
                frame
            )

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

        self.root.destroy()


# ============================================================
# MAIN
# ============================================================

def main():

    root = tk.Tk()

    CameraViewerApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
