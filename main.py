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
root.geometry("900300x700")
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
top_frame = tk.Frame(root)
top_frame.pack(fill="x", padx=10, pady=10)

tk.Label(top_frame, text="Camera:").pack(side="left")

camera_dropdown = ttk.Combobox(
    top_frame,
    textvariable=selected_camera,
    values=camera_list,
    state="readonly",
    width=10
)

camera_dropdown.pack(side="left", padx=5)
camera_dropdown.bind("<<ComboboxSelected>>", change_camera)

# -----------------------------
# Camera View
# -----------------------------
video_label = tk.Label(root, bg="black")
video_label.pack(fill="both", expand=True)


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