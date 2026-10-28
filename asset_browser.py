import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
from settings import PANEL, PANEL_LIGHT, BORDER, TEXT

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
