import os
import uuid
import threading
import shutil
import queue
import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

try:
    import onnxruntime as ort
except ImportError:
    ort = None

from settings import (
    BG,
    PANEL,
    PANEL_LIGHT,
    PANEL_HOVER,
    PANEL_DEEP,
    ACCENT,
    BORDER,
    TEXT,
    TEXT_DIM,
    FONT,
    flat_button,
)


def get_scene_separation_cache_root():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "scene_separation_cache",
    )


def clear_scene_separation_cache():
    cache_root = get_scene_separation_cache_root()
    if os.path.isdir(cache_root):
        try:
            shutil.rmtree(cache_root)
        except OSError as error:
            print(
                "SceneSeparation: could not clear cache:",
                error,
            )
            return
    try:
        os.makedirs(cache_root, exist_ok=True)
    except OSError as error:
        print(
            "SceneSeparation: could not recreate cache:",
            error,
        )


MAX_MASK_CONTROL_POINTS = 32


def _simplify_contour(contour, force=False):
    contour_points = contour.reshape(-1, 2).astype(np.float32)
    if len(contour_points) <= MAX_MASK_CONTROL_POINTS and not force:
        return contour_points

    perimeter = cv2.arcLength(contour, True)
    epsilon = max(0.75, perimeter * 0.015)
    major_points = cv2.approxPolyDP(contour, epsilon, True)
    while len(major_points) > MAX_MASK_CONTROL_POINTS:
        epsilon *= 1.5
        major_points = cv2.approxPolyDP(contour, epsilon, True)

    selected = set()
    for point in major_points.reshape(-1, 2):
        distances = np.sum((contour_points - point) ** 2, axis=1)
        selected.add(int(np.argmin(distances)))
    if len(selected) < 3:
        selected.update(
            (0, len(contour_points) // 3, 2 * len(contour_points) // 3)
        )

    while len(selected) < MAX_MASK_CONTROL_POINTS:
        ordered = sorted(selected)
        best_index = None
        best_distance = 0.75
        for position, start_index in enumerate(ordered):
            end_index = ordered[(position + 1) % len(ordered)]
            arc_length = (end_index - start_index) % len(contour_points)
            if arc_length <= 1:
                continue

            arc_indices = [
                (start_index + offset) % len(contour_points)
                for offset in range(1, arc_length)
            ]
            arc_points = contour_points[arc_indices]
            start = contour_points[start_index]
            segment = contour_points[end_index] - start
            segment_length = float(np.dot(segment, segment))
            if segment_length == 0:
                distances = np.linalg.norm(arc_points - start, axis=1)
            else:
                projection = np.clip(
                    np.sum((arc_points - start) * segment, axis=1)
                    / segment_length,
                    0.0,
                    1.0,
                )
                closest = start + projection[:, np.newaxis] * segment
                distances = np.linalg.norm(arc_points - closest, axis=1)
            farthest = int(np.argmax(distances))
            if distances[farthest] > best_distance:
                best_index = arc_indices[farthest]
                best_distance = float(distances[farthest])

        if best_index is None:
            break
        selected.add(best_index)

    return contour_points[sorted(selected)]


def _contour_depth(hierarchy, contour_index):
    depth = 0
    parent = hierarchy[contour_index][3]
    while parent >= 0:
        depth += 1
        parent = hierarchy[parent][3]
    return depth


def extract_mask_contours(mask, simplify=False):
    binary_mask = (mask > 0).astype(np.uint8)
    contours, hierarchy = cv2.findContours(
        binary_mask,
        cv2.RETR_TREE,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if hierarchy is None:
        return []

    hierarchy = hierarchy[0]
    result = []
    for index, contour in enumerate(contours):
        points = _simplify_contour(contour, force=simplify)
        if len(points) < 3:
            continue
        result.append(
            (
                points.astype(np.float32),
                _contour_depth(hierarchy, index),
            )
        )
    return result


def rasterize_mask_contours(shape, contours):
    height, width = shape[:2]
    mask = np.zeros((height, width), dtype=np.float32)
    if not contours:
        return mask

    all_points = np.concatenate(
        [points for points, _ in contours],
        axis=0,
    )
    left = max(0, int(np.floor(all_points[:, 0].min())))
    right = min(width - 1, int(np.ceil(all_points[:, 0].max())))
    top = max(0, int(np.floor(all_points[:, 1].min())))
    bottom = min(height - 1, int(np.ceil(all_points[:, 1].max())))
    if left > right or top > bottom:
        return mask

    region = np.zeros((bottom - top + 1, right - left + 1), dtype=np.uint8)
    for points, depth in sorted(contours, key=lambda item: item[1]):
        polygon = np.rint(
            points - np.asarray((left, top), dtype=np.float32)
        ).astype(np.int32)
        cv2.fillPoly(region, [polygon], 255 if depth % 2 == 0 else 0)
    mask[top : bottom + 1, left : right + 1] = region.astype(np.float32) / 255.0
    return mask


def normalize_mask_edges(mask):
    binary_mask = (mask > 0).astype(np.uint8) * 255
    if not np.any(binary_mask):
        return binary_mask.astype(np.float32)

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    normalized = cv2.morphologyEx(
        binary_mask,
        cv2.MORPH_CLOSE,
        kernel,
    )
    normalized = cv2.morphologyEx(
        normalized,
        cv2.MORPH_OPEN,
        kernel,
    )
    contours = extract_mask_contours(normalized, simplify=True)
    return rasterize_mask_contours(mask.shape, contours)


def copy_mask_contours(contours):
    return [
        (points.copy(), depth)
        for points, depth in contours
    ]


def insert_contour_point(contours, x, y, max_distance):
    closest = None
    closest_distance = float(max_distance)
    point = np.asarray((x, y), dtype=np.float32)

    for contour_index, (points, _) in enumerate(contours):
        for segment_index in range(len(points)):
            start = points[segment_index]
            end = points[(segment_index + 1) % len(points)]
            segment = end - start
            length_squared = float(np.dot(segment, segment))
            if length_squared == 0:
                continue
            fraction = float(
                np.clip(np.dot(point - start, segment) / length_squared, 0, 1)
            )
            projected = start + fraction * segment
            distance = float(np.linalg.norm(point - projected))
            if distance <= closest_distance:
                closest = (
                    contour_index,
                    segment_index,
                    fraction,
                    projected,
                )
                closest_distance = distance

    if closest is None:
        return copy_mask_contours(contours), None

    contour_index, segment_index, fraction, projected = closest
    points, depth = contours[contour_index]
    if np.min(np.linalg.norm(points - projected, axis=1)) <= 2.0:
        return copy_mask_contours(contours), None

    insertion_index = segment_index + 1
    updated = copy_mask_contours(contours)
    updated_points = np.insert(points, insertion_index, projected, axis=0)
    updated[contour_index] = (updated_points, depth)
    return updated, (contour_index, segment_index, fraction, insertion_index)


def is_valid_contour_edit(source_points, target_points):
    if len(source_points) != len(target_points) or len(target_points) < 3:
        return False

    source_area = cv2.contourArea(source_points, oriented=True)
    target_area = cv2.contourArea(target_points, oriented=True)
    if source_area * target_area <= 0:
        return False

    count = len(target_points)
    for first_index in range(count):
        first_start = target_points[first_index]
        first_end = target_points[(first_index + 1) % count]
        for second_index in range(first_index + 1, count):
            if second_index in (
                first_index,
                (first_index + 1) % count,
                (first_index - 1) % count,
            ):
                continue
            second_start = target_points[second_index]
            second_end = target_points[(second_index + 1) % count]
            if _segments_intersect(
                first_start,
                first_end,
                second_start,
                second_end,
            ):
                return False
    return True


def remove_redundant_contour_points(
    source_points,
    target_points,
    tolerance=0.75,
):
    if len(source_points) != len(target_points):
        raise ValueError("Source and edited contours must have matching points")

    source = np.asarray(source_points, dtype=np.float32).copy()
    target = np.asarray(target_points, dtype=np.float32).copy()
    removed = 0
    while len(source) > 3:
        redundant_index = None
        for index in range(len(source)):
            previous = (index - 1) % len(source)
            following = (index + 1) % len(source)
            source_distance = _point_segment_distance(
                source[index],
                source[previous],
                source[following],
            )
            target_distance = _point_segment_distance(
                target[index],
                target[previous],
                target[following],
            )
            if max(source_distance, target_distance) <= tolerance:
                redundant_index = index
                break

        if redundant_index is None:
            break
        source = np.delete(source, redundant_index, axis=0)
        target = np.delete(target, redundant_index, axis=0)
        removed += 1
    return source, target, removed


def _point_segment_distance(point, start, end):
    segment = end - start
    length_squared = float(np.dot(segment, segment))
    if length_squared == 0:
        return float(np.linalg.norm(point - start))
    fraction = float(
        np.clip(np.dot(point - start, segment) / length_squared, 0.0, 1.0)
    )
    closest = start + fraction * segment
    return float(np.linalg.norm(point - closest))


def _segments_intersect(first_start, first_end, second_start, second_end):
    def orientation(point_a, point_b, point_c):
        return (
            (point_b[0] - point_a[0]) * (point_c[1] - point_a[1])
            - (point_b[1] - point_a[1]) * (point_c[0] - point_a[0])
        )

    first_a = orientation(first_start, first_end, second_start)
    first_b = orientation(first_start, first_end, second_end)
    second_a = orientation(second_start, second_end, first_start)
    second_b = orientation(second_start, second_end, first_end)
    return first_a * first_b < 0 and second_a * second_b < 0


def compose_layer_masks(back_to_front_masks):
    if not back_to_front_masks:
        return []

    shape = back_to_front_masks[0].shape
    covered = np.zeros(shape, dtype=bool)
    composed = [None] * len(back_to_front_masks)
    for index in range(len(back_to_front_masks) - 1, -1, -1):
        source_mask = back_to_front_masks[index]
        if source_mask.shape != shape:
            raise ValueError("All layer masks must have the same dimensions")
        if index == 0 and len(back_to_front_masks) > 1:
            visible_mask = ~covered
        else:
            visible_mask = (source_mask > 0) & ~covered
        composed[index] = visible_mask.astype(np.float32)
        covered |= visible_mask
    return composed


def propagate_layer_mask_change(
    back_to_front_masks,
    previous_masks,
    changed_index,
):
    if len(previous_masks) != len(back_to_front_masks):
        raise ValueError("Previous and current layer counts must match")
    if not 0 <= changed_index < len(back_to_front_masks):
        raise ValueError("Changed layer index is out of range")

    candidates = [mask.copy() for mask in back_to_front_masks]
    composed = compose_layer_masks(candidates)
    if changed_index > 0:
        released = (
            (previous_masks[changed_index] > 0)
            & (composed[changed_index] == 0)
        )
        if released.any():
            candidates[changed_index - 1][released] = 1.0
            composed = compose_layer_masks(candidates)
    return candidates, composed


def _draw_mask_contours(mask, contours):
    height, width = mask.shape[:2]
    control_edges = np.zeros((height, width), dtype=np.uint8)
    for points, _ in contours:
        polygon = np.rint(points).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(
            control_edges,
            [polygon],
            True,
            255,
            1,
            lineType=cv2.LINE_AA,
        )
    return control_edges


class SceneSeparationWindow(tk.Toplevel):
    def __init__(
        self,
        parent,
        clip,
        current_time,
        original_layer_name,
        on_add_layers=None,
    ):
        super().__init__(parent)
        self.title("Scene Separation")
        self.geometry("1100x700")
        self.minsize(760, 520)
        self.configure(bg=BG)
        self.transient(parent.winfo_toplevel())

        self.clip = clip
        self.current_time = current_time
        self.original_layer_name = original_layer_name
        self.on_add_layers = on_add_layers
        self.depth_net = None
        self.depth_session = None
        self.segmentation_net = None
        self.source_frame = None
        self.depth_map = None
        self.layer_masks = []
        self.base_layer_masks = []
        self.deformed_layer_masks = []
        self.mask_source_contours = []
        self.mask_target_contours = []
        self.mesh_editing = False
        self._mesh_edit_start_masks = None
        self._mesh_edit_changed_indices = set()
        self._dragged_mesh_node = None
        self._preview_bounds = None
        self.preview_photos = []
        self.processing = False
        self._closing = False
        self._processing_results = queue.Queue()
        self._poll_processing_job = None

        self.resolution = tk.StringVar(value="720")
        self.layer_count = tk.StringVar(value="3")
        self.processing_status = tk.StringVar(value="Ready")

        main = tk.Frame(self, bg=PANEL)
        main.pack(fill="both", expand=True, padx=8, pady=8)
        main.grid_columnconfigure(0, weight=3)
        main.grid_columnconfigure(1, weight=2)
        main.grid_rowconfigure(0, weight=1)

        self.preview_canvas = tk.Canvas(
            main,
            bg=PANEL_DEEP,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        self.preview_canvas.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

        controls = tk.Frame(main, bg=PANEL)
        controls.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)

        tk.Label(
            controls,
            text="SCENE SEPARATION",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 12, "bold"),
        ).pack(anchor="w", pady=(3, 3))

        tk.Label(
            controls,
            text="Create depth-based layers from the selected frame.",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 8),
            wraplength=280,
            justify="left"
        ).pack(anchor="w", pady=(0, 13))

        resolution_row = tk.Frame(controls, bg=PANEL_LIGHT)
        resolution_row.pack(fill="x", pady=3)
        tk.Label(
            resolution_row,
            text="Processing width",
            bg=PANEL_LIGHT,
            fg=TEXT,
            font=(FONT, 9),
        ).pack(side="left", padx=9, pady=7)
        resolution_menu = tk.OptionMenu(
            resolution_row,
            self.resolution,
            "480",
            "720",
            "960",
            "1280",
            "1920",
            "Original",
        )
        resolution_menu.configure(
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=PANEL_HOVER,
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            cursor="hand2"
        )
        resolution_menu["menu"].configure(
            bg=PANEL_LIGHT,
            fg=TEXT,
            activebackground=ACCENT,
            activeforeground=BG,
            bd=0
        )
        resolution_menu.pack(side="right", padx=7, pady=3)

        layer_count_row = tk.Frame(controls, bg=PANEL_LIGHT)
        layer_count_row.pack(fill="x", pady=3)
        tk.Label(
            layer_count_row,
            text="Number of layers",
            bg=PANEL_LIGHT,
            fg=TEXT,
            font=(FONT, 9),
        ).pack(side="left", padx=9, pady=7)
        tk.Spinbox(
            layer_count_row,
            from_=2,
            to=12,
            width=5,
            textvariable=self.layer_count,
            justify="center",
            bg=PANEL_DEEP,
            fg=TEXT,
            insertbackground=TEXT,
            buttonbackground=PANEL_LIGHT,
            relief="flat",
            readonlybackground=PANEL_DEEP,
            highlightthickness=0,
            buttonuprelief="flat",
            buttondownrelief="flat"
        ).pack(side="right", padx=9, pady=5)

        flat_button(
            controls,
            "Process Selected Frame",
            self._start_processing,
            accent=True,
        ).pack(fill="x", pady=(8, 3))

        tk.Label(
            controls,
            textvariable=self.processing_status,
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9),
            wraplength=280,
            justify="left",
        ).pack(fill="x", pady=(8, 6))

        tk.Label(
            controls,
            text="LAYERS",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9, "bold"),
        ).pack(anchor="w", pady=(14, 5))

        self.layers_frame = tk.Frame(controls, bg=PANEL)
        self.layers_frame.pack(fill="both", expand=True)

        self.mesh_edit_button = flat_button(
            controls,
            "Edit Mask Mesh",
            self._toggle_mesh_editing,
        )
        self.mesh_edit_button.pack(fill="x", pady=(8, 3))
        flat_button(
            controls,
            "Reset Current Mesh",
            self._reset_current_mesh,
        ).pack(fill="x", pady=3)

        flat_button(
            controls,
            "Add Layers to Timeline",
            self._export_layers,
        ).pack(fill="x", pady=(8, 0))

        self.preview_canvas.bind("<Configure>", self._redraw_preview)
        self.preview_canvas.bind("<ButtonPress-1>", self._start_mesh_drag)
        self.preview_canvas.bind("<B1-Motion>", self._drag_mesh_node)
        self.preview_canvas.bind("<ButtonRelease-1>", self._finish_mesh_drag)
        self.preview_canvas.bind("<Double-Button-1>", self._insert_mask_node)
        self.preview_canvas.bind("<ButtonPress-3>", self._delete_mask_node)
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._poll_processing_job = self.after(
            50,
            self._poll_processing_result,
        )
        self._load_source_frame()
        self._load_bundled_models()

    def _load_bundled_models(self):
        models_directory = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "models",
            "scene-separation",
        )
        depth_path = os.path.join(
            models_directory,
            "dpt-hybrid-midas.onnx",
        )
        segmentation_path = os.path.join(
            models_directory,
            "yolo11n-seg.onnx",
        )

        if os.path.isfile(depth_path):
            try:
                if ort is not None:
                    self.depth_session = ort.InferenceSession(
                        depth_path,
                        providers=["CPUExecutionProvider"],
                    )
                    self.depth_net = None
                else:
                    self.depth_net = cv2.dnn.readNetFromONNX(depth_path)
                    self.depth_net.setPreferableBackend(
                        cv2.dnn.DNN_BACKEND_OPENCV
                    )
                    self.depth_net.setPreferableTarget(
                        cv2.dnn.DNN_TARGET_CPU
                    )
            except Exception as error:
                print("SceneSeparation: bundled depth model error:", error)

        if os.path.isfile(segmentation_path):
            try:
                self.segmentation_net = cv2.dnn.readNetFromONNX(segmentation_path)
                self.segmentation_net.setPreferableBackend(
                    cv2.dnn.DNN_BACKEND_OPENCV
                )
                self.segmentation_net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
            except Exception as error:
                print("SceneSeparation: bundled segmentation model error:", error)

        if (
            (self.depth_net is not None or self.depth_session is not None)
            and self.segmentation_net is not None
        ):
            self.processing_status.set(
                "Local DPT and YOLO11n-seg models ready"
            )
        elif self.depth_net is not None or self.depth_session is not None:
            self.processing_status.set("Local DPT depth model ready")
        elif self.segmentation_net is not None:
            self.processing_status.set("Local YOLO11n-seg model ready")

    def _load_source_frame(self):
        if self.clip.media_type == "video":
            capture = cv2.VideoCapture(self.clip.file_path)
            try:
                if capture.isOpened():
                    local_time = max(
                        0.0,
                        min(
                            self.current_time - self.clip.start_time,
                            self.clip.duration,
                        ),
                    )
                    capture.set(
                        cv2.CAP_PROP_POS_MSEC,
                        local_time * 1000.0,
                    )
                    ok, frame = capture.read()
                    if ok:
                        self.source_frame = cv2.cvtColor(
                            frame,
                            cv2.COLOR_BGR2RGB,
                        )
            finally:
                capture.release()
        else:
            image = cv2.imread(self.clip.file_path, cv2.IMREAD_COLOR)
            if image is not None:
                self.source_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        if self.source_frame is not None:
            self.processing_status.set("Selected frame ready")
            self._redraw_preview()
        else:
            self.processing_status.set("Could not read the selected clip")

    def _start_processing(self):
        if self.source_frame is None or self.processing:
            return

        if self.mesh_editing:
            self.processing_status.set(
                "Finish mesh editing before processing another frame"
            )
            return

        self.mesh_editing = False
        self._mesh_edit_start_masks = None
        self._mesh_edit_changed_indices.clear()
        self._dragged_mesh_node = None
        self.mesh_edit_button.configure(text="Edit Mask Mesh")
        self.processing = True
        self.processing_status.set("Processing locally...")
        source_frame = self.source_frame.copy()
        try:
            requested_layer_count = max(
                2,
                min(12, int(self.layer_count.get())),
            )
        except (TypeError, ValueError):
            requested_layer_count = 3
        selected_resolution = self.resolution.get()
        target_width = (
            0
            if selected_resolution == "Original"
            else int(selected_resolution)
        )
        depth_net = self.depth_net
        depth_session = self.depth_session
        segmentation_net = self.segmentation_net
        thread = threading.Thread(
            target=self._process_frame,
            daemon=True,
            args=(
                source_frame,
                requested_layer_count,
                target_width,
                depth_net,
                depth_session,
                segmentation_net,
            ),
        )
        thread.start()

    def _process_frame(
        self,
        source_frame,
        requested_layer_count,
        target_width,
        depth_net,
        depth_session,
        segmentation_net,
    ):
        try:
            frame = self._resize_for_processing(
                source_frame,
                target_width,
            )

            if (
                depth_net is not None
                or depth_session is not None
            ):
                depth = self._estimate_depth(
                    frame,
                    depth_net,
                    depth_session,
                )
            else:
                depth = self._fallback_depth(frame)

            if segmentation_net is not None:
                masks = self._segment_instances(frame, segmentation_net)
            else:
                masks = []

            if masks:
                layer_masks = self._build_instance_layers(
                    frame,
                    depth,
                    masks,
                    requested_layer_count,
                )
            else:
                layer_masks = self._build_depth_band_layers(
                    frame,
                    depth,
                    requested_layer_count,
                )

            normalized_layers = []
            for name, _, mask in layer_masks:
                normalized_mask = normalize_mask_edges(mask)
                normalized_layers.append(
                    (
                        name,
                        self._mask_rgba(frame, normalized_mask),
                        normalized_mask,
                    )
                )
            layer_masks = normalized_layers
            self._processing_results.put(
                ("result", frame, depth, layer_masks)
            )
        except Exception as error:
            print("SceneSeparation: processing error:", error)
            self._processing_results.put(
                ("error", str(error))
            )

    def _poll_processing_result(self):
        self._poll_processing_job = None
        if self._closing:
            return

        try:
            while True:
                item = self._processing_results.get_nowait()
                if item[0] == "result":
                    _, frame, depth, layer_masks = item
                    self._publish_result(
                        frame,
                        depth,
                        layer_masks,
                    )
                else:
                    self._publish_error(item[1])
        except queue.Empty:
            pass

        if not self._closing:
            self._poll_processing_job = self.after(
                50,
                self._poll_processing_result,
            )

    def _close(self):
        self._closing = True
        self.processing = False
        if self._poll_processing_job is not None:
            try:
                self.after_cancel(self._poll_processing_job)
            except tk.TclError:
                pass
            self._poll_processing_job = None
        self.depth_net = None
        self.depth_session = None
        self.segmentation_net = None
        self.source_frame = None
        self.depth_map = None
        self.layer_masks = []
        self.base_layer_masks = []
        self.deformed_layer_masks = []
        self.mask_source_contours = []
        self.mask_target_contours = []
        self._mesh_edit_start_masks = None
        self._mesh_edit_changed_indices.clear()
        self.preview_photos = []
        self.destroy()

    def _resize_for_processing(self, frame, target_width):
        if target_width <= 0:
            return frame.copy()

        height, width = frame.shape[:2]
        if width == target_width:
            return frame.copy()
        scale = target_width / float(width)
        return cv2.resize(
            frame,
            (target_width, max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA,
        )

    def _estimate_depth(
        self,
        frame,
        depth_net=None,
        depth_session=None,
    ):
        height, width = frame.shape[:2]
        model_size = (384, 384)
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1.0 / 255.0,
            size=model_size,
            mean=(0.0, 0.0, 0.0),
            swapRB=True,
            crop=False,
        )
        channel_means = np.asarray(
            [0.485, 0.456, 0.406],
            dtype=np.float32,
        )
        channel_stdevs = np.asarray(
            [0.229, 0.224, 0.225],
            dtype=np.float32,
        )
        blob[0] = (
            blob[0] - channel_means[:, None, None]
        ) / channel_stdevs[:, None, None]

        if depth_session is not None:
            input_name = depth_session.get_inputs()[0].name
            output_name = depth_session.get_outputs()[0].name
            output = depth_session.run(
                [output_name],
                {input_name: blob},
            )[0]
            output = np.asarray(output, dtype=np.float32)
            output = output.squeeze()
            if output.ndim != 2:
                raise RuntimeError(
                    "Unsupported depth model output shape"
                )
            output = cv2.resize(
                output,
                (width, height),
                interpolation=cv2.INTER_CUBIC,
            )
            output -= float(output.min())
            maximum = float(output.max())
            if maximum > 0:
                output /= maximum
            return output

        if depth_net is None:
            return self._fallback_depth(frame)

        depth_net.setInput(blob)
        output = depth_net.forward()

        output = np.asarray(output, dtype=np.float32)
        output = output.squeeze()
        if output.ndim != 2:
            output = np.asarray(output).reshape(-1)
            side = int(np.sqrt(output.size))
            if side * side != output.size:
                raise RuntimeError("Unsupported depth model output shape")
            output = output.reshape(side, side)

        output = cv2.resize(
            output,
            (width, height),
            interpolation=cv2.INTER_CUBIC,
        )
        output -= float(output.min())
        maximum = float(output.max())
        if maximum > 0:
            output /= maximum
        return output

    def _fallback_depth(self, frame):
        gray = cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 1.2)

        gradient_x = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gradient_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        gradient = cv2.magnitude(gradient_x, gradient_y)
        gradient = cv2.GaussianBlur(gradient, (9, 9), 2.0)

        height, width = gray.shape
        center_y, center_x = height // 2, width // 2
        y, x = np.indices((height, width))
        distance = np.sqrt(
            ((x - center_x) / max(width, 1)) ** 2
            + ((y - center_y) / max(height, 1)) ** 2
        )
        center_bias = 1.0 - cv2.normalize(
            distance,
            None,
            0.0,
            1.0,
            cv2.NORM_MINMAX,
        )
        saliency = cv2.normalize(
            gradient,
            None,
            0.0,
            1.0,
            cv2.NORM_MINMAX,
        )
        depth = np.clip(
            saliency * 0.55 + center_bias * 0.45,
            0.0,
            1.0,
        )
        return cv2.GaussianBlur(depth.astype(np.float32), (7, 7), 1.5)

    def _segment_instances(self, frame, segmentation_net=None):
        if segmentation_net is None:
            segmentation_net = self.segmentation_net
        if segmentation_net is None:
            return []
        height, width = frame.shape[:2]
        model_size = (640, 640)
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1.0 / 255.0,
            size=model_size,
            swapRB=True,
            crop=False,
        )
        segmentation_net.setInput(blob)
        outputs = segmentation_net.forward(
            segmentation_net.getUnconnectedOutLayersNames()
        )
        if isinstance(outputs, tuple):
            outputs = list(outputs)

        detections = outputs[0] if isinstance(outputs, list) else outputs
        detections = np.asarray(detections, dtype=np.float32)

        protos = None
        if isinstance(outputs, list) and len(outputs) > 1:
            protos = np.asarray(outputs[1], dtype=np.float32)

        detections = np.squeeze(detections)
        if detections.ndim == 2 and detections.shape[0] < detections.shape[1]:
            detections = detections.T
        if detections.ndim != 2 or detections.shape[1] < 38:
            return []

        masks = []
        scale_x = width / float(model_size[0])
        scale_y = height / float(model_size[1])

        for detection in detections:
            confidence = float(detection[4])
            if confidence < 0.25:
                continue

            if protos is None:
                continue

            class_scores = detection[5:-32] if detection.size >= 38 else None
            if class_scores is None or class_scores.size == 0:
                continue

            coefficients = detection[-32:]
            proto = np.asarray(protos).squeeze()
            if proto.ndim != 3:
                continue

            mask = np.tensordot(
                coefficients,
                proto.reshape(proto.shape[0], -1),
                axes=1,
            )
            mask = mask.reshape(proto.shape[1:])
            mask = cv2.resize(
                mask,
                (width, height),
                interpolation=cv2.INTER_LINEAR,
            )
            mask = np.clip(mask, -40.0, 40.0)
            mask = 1.0 / (1.0 + np.exp(-mask))

            cx, cy, box_width, box_height = detection[0:4]
            cx *= scale_x
            cy *= scale_y
            box_width *= scale_x
            box_height *= scale_y

            box_mask = np.zeros((height, width), dtype=np.float32)
            left = max(0, int(cx - box_width * 0.5))
            top = max(0, int(cy - box_height * 0.5))
            right = min(width, int(cx + box_width * 0.5))
            bottom = min(height, int(cy + box_height * 0.5))
            box_mask[top:bottom, left:right] = 1.0

            mask = cv2.multiply(mask, box_mask)
            mask = (mask > 0.5).astype(np.uint8)
            if cv2.countNonZero(mask) < 32:
                continue
            masks.append(mask)

        return self._remove_duplicate_masks(masks)

    def _remove_duplicate_masks(self, masks):
        unique = []
        for mask in sorted(
            masks,
            key=lambda item: int(cv2.countNonZero(item)),
            reverse=True,
        ):
            duplicate = False
            for existing in unique:
                intersection = np.logical_and(mask, existing).sum()
                union = np.logical_or(mask, existing).sum()
                if union and intersection / float(union) > 0.75:
                    duplicate = True
                    break
            if not duplicate:
                unique.append(mask)
        return unique

    def _build_instance_layers(self, frame, depth, masks, layer_count):
        height, width = frame.shape[:2]
        covered = np.zeros((height, width), dtype=bool)
        ranked_masks = []

        for mask in masks:
            median_depth = float(np.median(depth[mask > 0]))
            ranked_masks.append((median_depth, mask))

        ranked_masks.sort(key=lambda item: item[0])
        layers = []
        object_count = max(1, layer_count - 1)
        selected_masks = ranked_masks[:object_count]
        for index, (_, mask) in enumerate(selected_masks):
            available = mask.astype(bool) & ~covered
            available = self._soften_mask(available)
            rgba = self._mask_rgba(frame, available)
            layers.append(
                (
                    "Object {}".format(index + 1),
                    rgba,
                    available,
                )
            )
            covered |= available

        if len(selected_masks) < object_count:
            remaining_depth_slots = object_count - len(selected_masks)
            remaining = ~covered
            if remaining.any():
                if remaining_depth_slots == 1:
                    bands = [remaining]
                else:
                    quantiles = np.quantile(
                        depth[remaining],
                        np.linspace(
                            0.0,
                            1.0,
                            remaining_depth_slots + 1,
                        )[1:-1],
                    )
                    bands = [remaining & (depth <= quantiles[0])]
                    for band_index in range(1, remaining_depth_slots - 1):
                        bands.append(
                            remaining
                            & (depth > quantiles[band_index - 1])
                            & (depth <= quantiles[band_index])
                        )
                    bands.append(remaining & (depth > quantiles[-1]))
                for band_index, band in enumerate(bands):
                    if not band.any():
                        continue
                    band = self._soften_mask(band)
                    rgba = self._mask_rgba(frame, band)
                    layers.append(
                        (
                            "Object {}".format(
                                len(selected_masks) + band_index + 1
                            ),
                            rgba,
                            band,
                        )
                    )
                    covered |= band

        remaining = ~covered
        if remaining.any():
            remaining = self._soften_mask(remaining)
            layers.append(
                (
                    "Background",
                    self._mask_rgba(frame, remaining),
                    remaining,
                )
            )

        background_layers = [
            layer
            for layer in layers
            if layer[0] == "Background"
        ]
        foreground_layers = [
            layer
            for layer in layers
            if layer[0] != "Background"
        ]
        return background_layers + foreground_layers

    def _build_depth_band_layers(self, frame, depth, layer_count):
        quantiles = np.quantile(
            depth,
            np.linspace(
                0.0,
                1.0,
                layer_count + 1,
            )[1:-1],
        )
        bands = []
        previous = None
        for index in range(layer_count):
            if index == 0:
                band = depth <= quantiles[0]
                name = "Background"
            elif index == layer_count - 1:
                band = depth > quantiles[-1]
                name = "Foreground"
            else:
                band = (
                    (depth > quantiles[index - 1])
                    & (depth <= quantiles[index])
                )
                name = "Depth {}".format(index)
            bands.append((name, band))

        layers = []
        for name, mask in bands:
            mask = self._soften_mask(mask)
            if mask.any():
                layers.append(
                    (
                        name,
                        self._mask_rgba(frame, mask),
                        mask,
                    )
                )
        return layers

    def _soften_mask(self, mask):
        mask = mask.astype(np.uint8) * 255
        mask = cv2.GaussianBlur(mask, (5, 5), 1.0)
        return (mask > 24).astype(np.float32)

    def _mask_rgba(self, frame, mask):
        alpha = (mask * 255).astype(np.uint8)
        return np.dstack((frame, alpha))

    def _publish_result(self, frame, depth, layers):
        self.processing = False
        self.source_frame = frame
        self.depth_map = depth
        masks = compose_layer_masks([mask for _, _, mask in layers])
        self.layer_masks = []
        for (name, _, _), mask in zip(layers, masks):
            self.layer_masks.append(
                (name, self._mask_rgba(frame, mask), mask)
            )
        self.base_layer_masks = [mask.copy() for mask in masks]
        self.deformed_layer_masks = [mask.copy() for mask in masks]
        self.mask_source_contours = [
            extract_mask_contours(mask)
            for mask in masks
        ]
        self.mask_target_contours = [
            copy_mask_contours(contours)
            for contours in self.mask_source_contours
        ]
        self.mesh_editing = False
        self._mesh_edit_start_masks = None
        self._mesh_edit_changed_indices.clear()
        self._dragged_mesh_node = None
        self.processing_status.set(
            "Complete - {} local layers".format(len(layers))
        )
        self.mesh_edit_button.configure(text="Edit Mask Mesh")
        self._render_layer_buttons()
        self.preview_canvas.delete("all")
        self.preview_photos = []
        self.preview_layer = len(layers) - 1
        self._redraw_preview()

    def _publish_error(self, message):
        self.processing = False
        self.processing_status.set("Processing failed: " + message)

    def _render_layer_buttons(self):
        for child in self.layers_frame.winfo_children():
            child.destroy()

        for index, (name, _, _) in enumerate(self.layer_masks):
            flat_button(
                self.layers_frame,
                name,
                lambda i=index: self._show_layer(i),
            ).pack(fill="x", pady=2)

    def _show_layer(self, index):
        self.preview_layer = index
        self.preview_canvas.delete("all")
        self.preview_photos = []
        self._redraw_preview()

    def _toggle_mesh_editing(self):
        if not self.layer_masks:
            self.processing_status.set("Process a frame before editing its masks")
            return

        if self.mesh_editing:
            self.mesh_editing = False
            self._dragged_mesh_node = None
            self._commit_mesh_edits()
        else:
            self.mesh_editing = True
            self._mesh_edit_start_masks = [
                mask.copy()
                for _, _, mask in self.layer_masks
            ]
            self._mesh_edit_changed_indices.clear()
            self._dragged_mesh_node = None

        self.mesh_edit_button.configure(
            text=(
                "Finish Mesh Editing"
                if self.mesh_editing
                else "Edit Mask Mesh"
            )
        )
        self.preview_canvas.configure(
            cursor="crosshair" if self.mesh_editing else ""
        )
        self.processing_status.set(
            "Drag edge points; double-click to add, right-click to remove"
            if self.mesh_editing
            else "Mesh editing finished"
        )
        self._redraw_preview()

    def _reset_current_mesh(self):
        if not self.layer_masks:
            self.processing_status.set("Process a frame before resetting its mask")
            return

        if not self.mesh_editing:
            self.processing_status.set(
                "Enter mesh editing before resetting a mesh"
            )
            return

        index = max(0, min(self.preview_layer, len(self.layer_masks) - 1))
        self.mask_target_contours[index] = copy_mask_contours(
            self.mask_source_contours[index]
        )
        name, _, _ = self.layer_masks[index]
        mask = self.base_layer_masks[index].copy()
        self.deformed_layer_masks[index] = mask
        self.layer_masks[index] = (
            name,
            self._mask_rgba(self.source_frame, mask),
            mask,
        )
        self._mesh_edit_changed_indices.add(index)
        self.processing_status.set("Reset {} mesh".format(name))
        self._redraw_preview()

    def _insert_mask_node(self, event):
        if not self.mesh_editing or self._preview_bounds is None:
            return

        bounds = self._preview_bounds
        origin_x, origin_y, display_width, display_height, width, height = bounds
        point_x = (event.x - origin_x) * width / float(display_width)
        point_y = (event.y - origin_y) * height / float(display_height)
        if not (0 <= point_x < width and 0 <= point_y < height):
            return

        index = self.preview_layer
        contours, insertion = insert_contour_point(
            self.mask_target_contours[index],
            point_x,
            point_y,
            12.0 * max(
                width / float(display_width),
                height / float(display_height),
            ),
        )
        if insertion is None:
            self.processing_status.set(
                "Double-click directly on an edge, away from existing points"
            )
            return

        contour_index, segment_index, fraction, insertion_index = insertion
        source_contours = copy_mask_contours(
            self.mask_source_contours[index]
        )
        source_points, depth = source_contours[contour_index]
        source_start = source_points[segment_index]
        source_end = source_points[(segment_index + 1) % len(source_points)]
        source_point = source_start + fraction * (source_end - source_start)
        source_contours[contour_index] = (
            np.insert(source_points, insertion_index, source_point, axis=0),
            depth,
        )
        self.mask_source_contours[index] = source_contours
        self.mask_target_contours[index] = contours
        self._mesh_edit_changed_indices.add(index)
        self.processing_status.set(
            "Added edge point; drag it to refine the mask"
        )
        self._redraw_preview()

    def _find_contour_node_at(self, event):
        if self._preview_bounds is None:
            return None
        bounds = self._preview_bounds
        origin_x, origin_y, display_width, display_height, width, height = bounds
        contours = self.mask_target_contours[self.preview_layer]
        nearest_node = None
        nearest_distance = 12.0
        for contour_index, (points, _) in enumerate(contours):
            for point_index, (node_x, node_y) in enumerate(points):
                screen_x = origin_x + node_x * display_width / float(width)
                screen_y = origin_y + node_y * display_height / float(height)
                distance = np.hypot(event.x - screen_x, event.y - screen_y)
                if distance <= nearest_distance:
                    nearest_node = (contour_index, point_index)
                    nearest_distance = distance
        return nearest_node

    def _delete_mask_node(self, event):
        if not self.mesh_editing:
            return
        node = self._find_contour_node_at(event)
        if node is None:
            return

        index = self.preview_layer
        contour_index, point_index = node
        source_contours = copy_mask_contours(
            self.mask_source_contours[index]
        )
        target_contours = copy_mask_contours(
            self.mask_target_contours[index]
        )
        source_points, source_depth = source_contours[contour_index]
        target_points, target_depth = target_contours[contour_index]
        if len(target_points) <= 3:
            self.processing_status.set(
                "A mask edge needs at least three points"
            )
            return

        source_points = np.delete(source_points, point_index, axis=0)
        target_points = np.delete(target_points, point_index, axis=0)
        if not is_valid_contour_edit(source_points, target_points):
            self.processing_status.set(
                "That point cannot be removed without distorting the edge"
            )
            return

        source_contours[contour_index] = (source_points, source_depth)
        target_contours[contour_index] = (target_points, target_depth)
        self.mask_source_contours[index] = source_contours
        self.mask_target_contours[index] = target_contours
        self._apply_mask_contours(index)
        self.processing_status.set("Removed mask edge point")
        self._redraw_preview()

    def _start_mesh_drag(self, event):
        if not self.mesh_editing:
            return

        nearest_node = self._find_contour_node_at(event)

        if nearest_node is not None:
            self._dragged_mesh_node = nearest_node
            self.preview_canvas.configure(cursor="fleur")
            self._drag_mesh_node(event)

    def _drag_mesh_node(self, event):
        if (
            not self.mesh_editing
            or self._dragged_mesh_node is None
            or self._preview_bounds is None
        ):
            return

        bounds = self._preview_bounds
        origin_x, origin_y, display_width, display_height, width, height = bounds
        contour_index, point_index = self._dragged_mesh_node
        point_x = (event.x - origin_x) * width / float(display_width)
        point_y = (event.y - origin_y) * height / float(display_height)
        point_x = min(float(width - 1), max(0.0, point_x))
        point_y = min(float(height - 1), max(0.0, point_y))

        index = self.preview_layer
        contours = copy_mask_contours(self.mask_target_contours[index])
        points, depth = contours[contour_index]
        updated_points = points.copy()
        updated_points[point_index] = (point_x, point_y)
        if not is_valid_contour_edit(
            self.mask_source_contours[index][contour_index][0],
            updated_points,
        ):
            return

        contours[contour_index] = (updated_points, depth)
        self.mask_target_contours[index] = contours
        self._apply_mask_contours(index)
        self._redraw_preview()

    def _finish_mesh_drag(self, event):
        self._dragged_mesh_node = None
        event.widget.configure(
            cursor="crosshair" if self.mesh_editing else ""
        )

    def _apply_mask_contours(self, index):
        mask = rasterize_mask_contours(
            self.base_layer_masks[index].shape,
            self.mask_target_contours[index],
        )
        self.deformed_layer_masks[index] = mask
        name, _, _ = self.layer_masks[index]
        self.layer_masks[index] = (
            name,
            self._mask_rgba(self.source_frame, mask),
            mask,
        )
        self._mesh_edit_changed_indices.add(index)

    def _commit_mesh_edits(self):
        if not self._mesh_edit_changed_indices:
            self._mesh_edit_start_masks = None
            return

        for index in self._mesh_edit_changed_indices:
            source_contours = copy_mask_contours(
                self.mask_source_contours[index]
            )
            target_contours = copy_mask_contours(
                self.mask_target_contours[index]
            )
            removed_points = 0
            for contour_index, (source_points, source_depth) in enumerate(
                source_contours
            ):
                target_points, target_depth = target_contours[contour_index]
                source_points, target_points, removed = (
                    remove_redundant_contour_points(
                        source_points,
                        target_points,
                    )
                )
                source_contours[contour_index] = (
                    source_points,
                    source_depth,
                )
                target_contours[contour_index] = (
                    target_points,
                    target_depth,
                )
                removed_points += removed

            if removed_points:
                self.mask_source_contours[index] = source_contours
                self.mask_target_contours[index] = target_contours
                self.deformed_layer_masks[index] = rasterize_mask_contours(
                    self.base_layer_masks[index].shape,
                    target_contours,
                )
                name, _, _ = self.layer_masks[index]
                mask = self.deformed_layer_masks[index]
                self.layer_masks[index] = (
                    name,
                    self._mask_rgba(self.source_frame, mask),
                    mask,
                )

        candidates = self.deformed_layer_masks
        previous_masks = self._mesh_edit_start_masks
        masks = compose_layer_masks(candidates)
        for index in sorted(self._mesh_edit_changed_indices, reverse=True):
            candidates, masks = propagate_layer_mask_change(
                candidates,
                previous_masks,
                index,
            )

        self.deformed_layer_masks = candidates
        for index, ((name, _, _), mask) in enumerate(
            zip(self.layer_masks, masks)
        ):
            self.layer_masks[index] = (
                name,
                self._mask_rgba(self.source_frame, mask),
                mask,
            )

        indices_to_rebase = {
            index
            for changed_index in self._mesh_edit_changed_indices
            for index in range(changed_index)
        }
        indices_to_rebase.difference_update(self._mesh_edit_changed_indices)
        for index in indices_to_rebase:
            mask = masks[index]
            self.base_layer_masks[index] = mask.copy()
            self.deformed_layer_masks[index] = mask.copy()
            self.mask_source_contours[index] = extract_mask_contours(mask)
            self.mask_target_contours[index] = copy_mask_contours(
                self.mask_source_contours[index]
            )
        self._mesh_edit_start_masks = None
        self._mesh_edit_changed_indices.clear()

    def _export_layers(self):
        if not self.layer_masks:
            return

        if self.mesh_editing:
            self.processing_status.set(
                "Finish mesh editing before adding layers to the timeline"
            )
            return

        cache_root = get_scene_separation_cache_root()
        try:
            os.makedirs(cache_root, exist_ok=True)
        except OSError as error:
            self.processing_status.set(
                "Could not create cache: " + str(error)
            )
            return
        session_dir = os.path.join(
            cache_root,
            uuid.uuid4().hex,
        )
        try:
            os.makedirs(session_dir)
        except OSError as error:
            self.processing_status.set(
                "Could not create export folder: " + str(error)
            )
            return

        exported_layers = []

        try:
            for index, (name, rgba, _) in enumerate(self.layer_masks):
                safe_name = "".join(
                    character
                    if character.isalnum() or character in " -_"
                    else "_"
                    for character in name
                )
                segment_number = index + 1
                layer_name = "{} Segment {}".format(
                    self.original_layer_name,
                    segment_number,
                )
                output_path = os.path.join(
                    session_dir,
                    "{}_{}.png".format(segment_number, safe_name),
                )
                Image.fromarray(rgba, mode="RGBA").save(
                    output_path
                )
                exported_layers.append(
                    (
                        layer_name,
                        output_path,
                    )
                )
        except (OSError, ValueError) as error:
            self.processing_status.set(
                "Could not export layers: " + str(error)
            )
            return

        if self.on_add_layers is not None:
            self.on_add_layers(exported_layers)

        self.processing_status.set(
            "Added {} layers to the timeline".format(
                len(exported_layers)
            )
        )

    def _redraw_preview(self, event=None):
        if self.source_frame is None:
            return

        self.preview_canvas.delete("all")
        editing_layer = (
            self.mesh_editing
            and hasattr(self, "preview_layer")
            and self.layer_masks
        )
        if editing_layer:
            index = max(
                0,
                min(
                    self.preview_layer,
                    len(self.layer_masks) - 1,
                ),
            )
            mask = np.clip(self.layer_masks[index][2], 0.0, 1.0)
            tint = np.empty_like(self.source_frame)
            tint[:, :] = (35, 205, 255)
            blend = (mask[:, :, np.newaxis] * 0.38).astype(np.float32)
            frame = np.clip(
                self.source_frame.astype(np.float32) * (1.0 - blend)
                + tint.astype(np.float32) * blend,
                0,
                255,
            ).astype(np.uint8)
            control_edges = _draw_mask_contours(
                mask,
                self.mask_target_contours[index],
            )
            mesh_alpha = (control_edges.astype(np.float32) / 255.0 * 0.85)[
                :, :, np.newaxis
            ]
            frame = np.clip(
                frame.astype(np.float32) * (1.0 - mesh_alpha)
                + np.asarray((45, 255, 185), dtype=np.float32) * mesh_alpha,
                0,
                255,
            ).astype(np.uint8)
        elif hasattr(self, "preview_layer") and self.layer_masks:
            index = max(
                0,
                min(
                    self.preview_layer,
                    len(self.layer_masks) - 1,
                ),
            )
            frame = self.layer_masks[index][1]
        elif self.depth_map is not None:
            depth = (self.depth_map * 255).astype(np.uint8)
            frame = cv2.applyColorMap(depth, cv2.COLORMAP_MAGMA)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        else:
            frame = self.source_frame

        canvas_width = max(1, self.preview_canvas.winfo_width())
        canvas_height = max(1, self.preview_canvas.winfo_height())
        height, width = frame.shape[:2]
        scale = min(canvas_width / float(width), canvas_height / float(height))
        display_width = max(1, int(width * scale))
        display_height = max(1, int(height * scale))
        display = cv2.resize(
            frame,
            (display_width, display_height),
            interpolation=cv2.INTER_AREA,
        )

        if display.shape[2] == 4:
            pil_image = Image.fromarray(display, mode="RGBA")
        else:
            pil_image = Image.fromarray(display, mode="RGB")
        photo = ImageTk.PhotoImage(pil_image)
        self.preview_photos = [photo]

        x = (canvas_width - display_width) // 2
        y = (canvas_height - display_height) // 2
        height, width = self.source_frame.shape[:2]
        self._preview_bounds = (
            x,
            y,
            display_width,
            display_height,
            width,
            height,
        )
        self.preview_canvas.create_image(
            x,
            y,
            anchor="nw",
            image=photo,
        )
        if editing_layer:
            for points, _ in self.mask_target_contours[index]:
                for point_x, point_y in points:
                    screen_x = x + point_x * display_width / float(width)
                    screen_y = y + point_y * display_height / float(height)
                    radius = 4
                    self.preview_canvas.create_oval(
                        screen_x - radius,
                        screen_y - radius,
                        screen_x + radius,
                        screen_y + radius,
                        fill=BG,
                        outline=TEXT,
                        width=2,
                    )
