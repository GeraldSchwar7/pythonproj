import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk

# -----------------------------
# Find available cameras
# -----------------------------
def get_available_cameras(max_cameras=10):
    cameras = []

    for i in range(max_cameras):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, _ = cap.read()
            if ret:
                cameras.append(i)
        cap.release()

    return cameras


# -----------------------------
# Main Window
# -----------------------------
root = tk.Tk()
root.title("Camera Viewer")
root.geometry("900x700")
root.resizable(True, True)

# Camera list
camera_list = get_available_cameras()

if not camera_list:
    camera_list = [0]

selected_camera = tk.IntVar(value=camera_list[0])

# Open camera
cap = cv2.VideoCapture(selected_camera.get())


# -----------------------------
# Change Camera
# -----------------------------
def change_camera(event=None):
    global cap

    cap.release()

    cap = cv2.VideoCapture(selected_camera.get())


# -----------------------------
# Dropdown
# -----------------------------
# -----------------------------
# Colors
# -----------------------------
BG = "#1e1e1e"
PANEL = "#252526"
BORDER = "#3c3c3c"
TEXT = "white"

root.configure(bg=BG)

# -----------------------------
# Menu Bar
# -----------------------------
menu_frame = tk.Frame(root, bg=PANEL, height=40)
menu_frame.pack(fill="x")

tk.Label(
    menu_frame,
    text="Project Monday",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 14, "bold")
).pack(side="left", padx=10)

# -----------------------------
# Camera Selection
# -----------------------------
camera_frame = tk.Frame(menu_frame, bg=PANEL)
camera_frame.pack(side="right", padx=10)

tk.Label(
    camera_frame,
    text="Camera:",
    bg=PANEL,
    fg=TEXT
).pack(side="left")

camera_dropdown = ttk.Combobox(
    camera_frame,
    textvariable=selected_camera,
    values=camera_list,
    state="readonly",
    width=5
)

camera_dropdown.pack(side="left", padx=5)
camera_dropdown.bind("<<ComboboxSelected>>", change_camera)

# -----------------------------
# Main Area
# -----------------------------
main_frame = tk.Frame(root, bg=BG)
main_frame.pack(fill="both", expand=True)

preview_frame = tk.Frame(main_frame, bg="black")
preview_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

inspector_frame = tk.Frame(main_frame, bg=PANEL, width=250)
inspector_frame.pack(side="right", fill="y", padx=5, pady=5)

tk.Label(
    inspector_frame,
    text="Inspector",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 12, "bold")
).pack(pady=10)

# -----------------------------
# Camera Preview
# -----------------------------
video_label = tk.Label(preview_frame, bg="black")
video_label.pack(fill="both", expand=True)

# -----------------------------
# Timeline
# -----------------------------
timeline_frame = tk.Frame(root, bg=PANEL, height=150)
timeline_frame.pack(fill="x", padx=5, pady=5)

tk.Label(
    timeline_frame,
    text="Timeline",
    bg=PANEL,
    fg=TEXT,
    font=("Segoe UI", 12, "bold")
).pack(anchor="w", padx=10, pady=10)

# -----------------------------
# Status Bar
# -----------------------------
status_frame = tk.Frame(root, bg=PANEL, height=30)
status_frame.pack(fill="x")

status_label = tk.Label(
    status_frame,
    text="Status: Ready",
    bg=PANEL,
    fg="lightgray"
)
status_label.pack(side="left", padx=10)


# -----------------------------
# Update Camera Feed
# -----------------------------
def update_frame():
    ret, frame = cap.read()

    if ret:
        # Convert BGR → RGB
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Resize to fit window
        w = 300
        h = 200

        if w > 1 and h > 1:
            frame = cv2.resize(frame, (w, h))

        img = Image.fromarray(frame)
        imgtk = ImageTk.PhotoImage(image=img)

        video_label.imgtk = imgtk
        video_label.configure(image=imgtk)
    cv2.imshow("Cam feed pos", 0)
    root.after(15, update_frame)


# -----------------------------
# Cleanup
# -----------------------------
def on_close():
    cap.release()
    root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

update_frame()
root.mainloop()