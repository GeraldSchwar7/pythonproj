import tkinter as tk
from app import CameraViewerApp


def main():
    root = tk.Tk()
    CameraViewerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
