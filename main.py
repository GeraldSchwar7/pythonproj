import tkinter as tk
from hand_tracker import HandTracker, HandMouseController
from app import CameraViewerApp
from scene_separation import clear_scene_separation_cache


def main():
    clear_scene_separation_cache()
    root = tk.Tk()
    CameraViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
