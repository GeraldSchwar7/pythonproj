import tkinter as tk
import cv2
from PIL import Image, ImageTk
from settings import PANEL, BORDER, TEXT

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
