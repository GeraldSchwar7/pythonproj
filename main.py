import importlib
import os
import queue
import tempfile
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from settings import (
    ACCENT,
    BG,
    BORDER,
    DANGER,
    FONT,
    FONT_SMALL,
    FONT_TITLE,
    PANEL,
    SUCCESS,
    TEXT,
    TEXT_DIM,
    WARNING,
    configure_ttk,
    flat_button,
)


APP_ROOT = Path(__file__).resolve().parent
REQUIRED_MODULES = (
    "cv2",
    "mediapipe",
    "mediapipe.tasks.python.vision",
    "pyautogui",
    "numpy",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
)
DEFAULT_VIEWPORT_RESOLUTION = (1920, 1080)


def _choose_viewport_resolution(parent):
    presets = {
        "HD 720p (1280 x 720)": (1280, 720),
        "Full HD 1080p (1920 x 1080)": (1920, 1080),
        "QHD 1440p (2560 x 1440)": (2560, 1440),
        "UHD 4K (3840 x 2160)": (3840, 2160),
        "Custom": None,
    }

    dialog = tk.Toplevel(parent)
    dialog.title("Viewport Resolution")
    dialog.geometry("460x330")
    dialog.resizable(False, False)
    dialog.transient(parent)
    dialog.configure(bg=BG)

    container = tk.Frame(
        dialog,
        bg=PANEL,
        highlightbackground=BORDER,
        highlightthickness=1,
        padx=22,
        pady=18,
    )
    container.pack(fill="both", expand=True, padx=14, pady=14)
    tk.Label(
        container,
        text="VIEWPORT SETUP",
        bg=PANEL,
        fg=ACCENT,
        font=(FONT, FONT_SMALL, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 5))
    tk.Label(
        container,
        text="Choose a composition resolution",
        bg=PANEL,
        fg=TEXT,
        font=(FONT, FONT_TITLE, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 14))
    tk.Label(
        container,
        text="The viewport will preserve this aspect ratio as its panel is resized.",
        bg=PANEL,
        fg=TEXT_DIM,
        font=(FONT, FONT_SMALL),
        anchor="w",
        justify="left",
        wraplength=410,
    ).pack(fill="x", pady=(0, 14))

    preset_var = tk.StringVar(
        master=dialog,
        value="Full HD 1080p (1920 x 1080)",
    )
    preset_box = ttk.Combobox(
        container,
        textvariable=preset_var,
        values=tuple(presets),
        state="readonly",
    )
    preset_box.pack(fill="x", pady=(0, 12))

    dimensions = tk.Frame(container, bg=PANEL)
    dimensions.pack(fill="x")
    width_var = tk.StringVar(master=dialog, value="1920")
    height_var = tk.StringVar(master=dialog, value="1080")

    tk.Label(
        dimensions,
        text="Width",
        bg=PANEL,
        fg=TEXT_DIM,
        font=(FONT, FONT_SMALL),
    ).grid(row=0, column=0, sticky="w")
    tk.Label(
        dimensions,
        text="Height",
        bg=PANEL,
        fg=TEXT_DIM,
        font=(FONT, FONT_SMALL),
    ).grid(row=0, column=2, sticky="w", padx=(14, 0))
    width_entry = ttk.Entry(
        dimensions,
        textvariable=width_var,
        state="readonly",
        width=10,
    )
    width_entry.grid(row=1, column=0, sticky="w")
    tk.Label(
        dimensions,
        text="x",
        bg=PANEL,
        fg=TEXT_DIM,
        font=(FONT, FONT_SMALL),
    ).grid(row=1, column=1, padx=8)
    height_entry = ttk.Entry(
        dimensions,
        textvariable=height_var,
        state="readonly",
        width=10,
    )
    height_entry.grid(row=1, column=2, sticky="w")

    error_label = tk.Label(
        container,
        text="",
        bg=PANEL,
        fg=DANGER,
        font=(FONT, FONT_SMALL),
        anchor="w",
    )
    error_label.pack(fill="x", pady=(8, 0))
    selected_resolution = [DEFAULT_VIEWPORT_RESOLUTION]

    def update_dimension_fields(_event=None):
        preset = presets[preset_var.get()]
        if preset is None:
            width_entry.configure(state="normal")
            height_entry.configure(state="normal")
            return

        width_var.set(str(preset[0]))
        height_var.set(str(preset[1]))
        width_entry.configure(state="readonly")
        height_entry.configure(state="readonly")

    def use_default():
        selected_resolution[0] = DEFAULT_VIEWPORT_RESOLUTION
        dialog.destroy()

    def use_selected_resolution():
        preset = presets[preset_var.get()]
        if preset is None:
            try:
                width = int(width_var.get())
                height = int(height_var.get())
            except ValueError:
                error_label.configure(text="Enter whole-number dimensions.")
                return

            if not (320 <= width <= 16384 and 240 <= height <= 16384):
                error_label.configure(
                    text="Use a width from 320-16384 and height from 240-16384."
                )
                return
            selected_resolution[0] = (width, height)
        else:
            selected_resolution[0] = preset
        dialog.destroy()

    preset_box.bind("<<ComboboxSelected>>", update_dimension_fields)
    buttons = tk.Frame(container, bg=PANEL)
    buttons.pack(fill="x", pady=(14, 0))
    flat_button(
        buttons,
        "Use 1080p",
        command=use_default,
    ).pack(side="left")
    flat_button(
        buttons,
        "Continue",
        command=use_selected_resolution,
        accent=True,
    ).pack(side="right")

    dialog.protocol("WM_DELETE_WINDOW", use_default)
    dialog.grab_set()
    dialog.wait_window()
    return selected_resolution[0]


def _check_dependencies():
    failures = []
    for module_name in REQUIRED_MODULES:
        try:
            importlib.import_module(module_name)
        except (ImportError, OSError, RuntimeError) as error:
            failures.append("{}: {}".format(module_name, error))

    if failures:
        return {
            "severity": "error",
            "message": "Required Python dependencies are unavailable:\n"
            + "\n".join(failures),
        }, None

    try:
        app_module = importlib.import_module("app")
    except (ImportError, OSError, RuntimeError) as error:
        return {
            "severity": "error",
            "message": "Could not load the editor modules: {}".format(error),
        }, None

    return {
        "severity": "ok",
        "message": "Required Python dependencies and editor modules are ready.",
    }, app_module.CameraViewerApp


def _check_models():
    models = (
        ("hand-tracking model", APP_ROOT / "models" / "hand_landmarker.task", True),
        (
            "depth-separation model",
            APP_ROOT / "models" / "scene-separation" / "dpt-hybrid-midas.onnx",
            False,
        ),
        (
            "object-segmentation model",
            APP_ROOT / "models" / "scene-separation" / "yolo11n-seg.onnx",
            False,
        ),
    )
    required_failures = []
    optional_failures = []

    for description, model_path, required in models:
        try:
            with model_path.open("rb") as model_file:
                if not model_file.read(1):
                    raise OSError("file is empty")
        except OSError as error:
            message = "{}: {}".format(description, error)
            if required:
                required_failures.append(message)
            else:
                optional_failures.append(message)

    if required_failures:
        return {
            "severity": "error",
            "message": "Required model check failed:\n"
            + "\n".join(required_failures),
        }
    if optional_failures:
        return {
            "severity": "warning",
            "message": "Some scene-separation features may be unavailable:\n"
            + "\n".join(optional_failures),
        }
    return {
        "severity": "ok",
        "message": "Bundled model files are present and readable.",
    }


def _clear_startup_cache():
    try:
        scene_separation = importlib.import_module("scene_separation")
        scene_separation.clear_scene_separation_cache()
        cache_root = scene_separation.get_scene_separation_cache_root()
        with tempfile.TemporaryFile(dir=cache_root):
            pass
        if os.listdir(cache_root):
            raise OSError("cache directory was not empty after cleanup")
    except (ImportError, OSError, RuntimeError) as error:
        return {
            "severity": "warning",
            "message": "Could not fully clear or verify the startup cache: "
            + str(error),
        }
    return {
        "severity": "ok",
        "message": "Scene-separation cache cleared and writable.",
    }


def _check_cameras():
    try:
        cv2 = importlib.import_module("cv2")
    except (ImportError, OSError, RuntimeError) as error:
        return {
            "severity": "warning",
            "message": "Camera check skipped because OpenCV is unavailable: "
            + str(error),
        }

    try:
        camera_manager = importlib.import_module(
            "camera_manager"
        ).CameraManager()
        cameras = camera_manager.find_available_cameras()
    except (ImportError, OSError, RuntimeError, cv2.error) as error:
        return {
            "severity": "warning",
            "message": "Camera check failed: {}".format(error),
        }

    if not cameras:
        return {
            "severity": "warning",
            "message": "No camera was detected; the editor can still open.",
        }
    return {
        "severity": "ok",
        "message": "Camera check passed ({} available).".format(len(cameras)),
    }


def _apply_safe_optimizations():
    try:
        cv2 = importlib.import_module("cv2")
    except (ImportError, OSError, RuntimeError) as error:
        return {
            "severity": "warning",
            "message": "OpenCV optimizations are unavailable: {}".format(error),
        }

    try:
        cv2.setUseOptimized(True)
        if not cv2.useOptimized():
            return {
                "severity": "warning",
                "message": "OpenCV optimized code paths could not be enabled.",
            }
    except (AttributeError, RuntimeError, cv2.error) as error:
        return {
            "severity": "warning",
            "message": "Could not enable OpenCV optimizations: {}".format(error),
        }

    return {
        "severity": "ok",
        "message": "Enabled OpenCV optimizations without changing frame rates.",
    }


def main():
    root = tk.Tk()
    root.title("Project Monday - Starting")
    root.geometry("560x250")
    root.resizable(False, False)
    root.configure(bg=BG)
    configure_ttk(root)

    container = tk.Frame(
        root,
        bg=PANEL,
        highlightbackground=BORDER,
        highlightthickness=1,
        padx=22,
        pady=18,
    )
    container.pack(fill="both", expand=True, padx=14, pady=14)
    tk.Label(
        container,
        text="PROJECT MONDAY",
        bg=PANEL,
        fg=ACCENT,
        font=(FONT, FONT_SMALL, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 5))
    tk.Label(
        container,
        text="Preparing your workspace",
        bg=PANEL,
        fg=TEXT,
        font=(FONT, FONT_TITLE, "bold"),
        anchor="w",
    ).pack(fill="x", pady=(0, 14))
    tk.Frame(container, bg=BORDER, height=1).pack(fill="x", pady=(0, 14))
    status_label = tk.Label(
        container,
        text="Starting checks...",
        bg=PANEL,
        fg=TEXT_DIM,
        font=(FONT, FONT_SMALL),
        anchor="w",
    )
    status_label.pack(fill="x", pady=(0, 8))
    progress = ttk.Progressbar(
        container,
        mode="determinate",
        maximum=5,
        style="Horizontal.TProgressbar",
    )
    progress.pack(fill="x", pady=(0, 12))
    details_label = tk.Label(
        container,
        text="",
        bg=PANEL,
        fg=WARNING,
        font=(FONT, FONT_SMALL),
        justify="left",
        anchor="w",
        wraplength=490,
    )
    details_label.pack(fill="x", anchor="w")
    exit_button = flat_button(
        container,
        "Exit",
        command=root.destroy,
        accent=True,
    )

    events = queue.Queue()
    checks = (
        ("Checking Python dependencies...", _check_dependencies),
        ("Checking bundled model files...", _check_models),
        ("Clearing startup cache...", _clear_startup_cache),
        ("Checking camera availability...", _check_cameras),
        ("Applying safe performance defaults...", _apply_safe_optimizations),
    )

    def run_checks():
        results = []
        app_class = None
        for index, (label, check) in enumerate(checks):
            events.put(("progress", index, label))
            check_result = check()
            if index == 0:
                result, app_class = check_result
            else:
                result = check_result
            results.append(result)
            events.put(("result", index + 1, result))
        events.put(("complete", results, app_class))

    def launch_editor(app_class, warnings, viewport_resolution):
        for child in root.winfo_children():
            child.destroy()
        root.resizable(True, True)
        app = app_class(
            root,
            viewport_resolution=viewport_resolution,
        )
        if warnings:
            app.set_status("Startup warning: " + "; ".join(warnings))

    def choose_resolution_and_launch(app_class, warnings):
        viewport_resolution = _choose_viewport_resolution(root)
        launch_editor(app_class, warnings, viewport_resolution)

    def finish_startup(results, app_class):
        blocking_issues = [
            result["message"]
            for result in results
            if result["severity"] == "error"
        ]
        warnings = [
            result["message"]
            for result in results
            if result["severity"] == "warning"
        ]
        if blocking_issues or app_class is None:
            status_label.configure(
                text="Startup checks found blocking issues.",
                fg=DANGER,
            )
            details_label.configure(
                text="\n".join(
                    blocking_issues or ["The editor could not be loaded."]
                ),
                fg=DANGER,
            )
            root.geometry("640x360")
            root.resizable(True, True)
            progress.pack_forget()
            exit_button.pack(anchor="e", pady=(12, 0))
            return

        if warnings:
            status_label.configure(
                text="Checks complete with warnings.",
                fg=WARNING,
            )
            details_label.configure(text="\n".join(warnings), fg=WARNING)
            root.after(
                1800,
                lambda: choose_resolution_and_launch(app_class, warnings),
            )
            return

        status_label.configure(
            text="Checks complete. Opening the editor...",
            fg=SUCCESS,
        )
        root.after(
            300,
            lambda: choose_resolution_and_launch(app_class, warnings),
        )

    def poll_events():
        completed = False
        while True:
            try:
                event = events.get_nowait()
            except queue.Empty:
                break

            if event[0] == "progress":
                status_label.configure(text=event[2])
                progress.configure(value=event[1])
            elif event[0] == "result":
                progress.configure(value=event[1])
            elif event[0] == "complete":
                finish_startup(event[1], event[2])
                completed = True

        if not completed:
            root.after(50, poll_events)

    threading.Thread(target=run_checks, daemon=True).start()
    root.after(50, poll_events)
    root.mainloop()


if __name__ == "__main__":
    main()
