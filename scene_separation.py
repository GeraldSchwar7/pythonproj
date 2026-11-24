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
    PANEL_DEEP,
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
        controls.grid(row=0, column=1, sticky="nsew")

        tk.Label(
            controls,
            text="LOCAL SCENE DECOMPOSITION",
            bg=PANEL,
            fg=TEXT_DIM,
            font=(FONT, 9, "bold"),
        ).pack(anchor="w", pady=(2, 10))

        resolution_row = tk.Frame(controls, bg=PANEL)
        resolution_row.pack(fill="x", pady=3)
        tk.Label(
            resolution_row,
            text="Processing width",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 9),
        ).pack(side="left")
        tk.OptionMenu(
            resolution_row,
            self.resolution,
            "480",
            "720",
            "960",
            "1280",
            "1920",
            "Original",
        ).pack(side="right")

        layer_count_row = tk.Frame(controls, bg=PANEL)
        layer_count_row.pack(fill="x", pady=3)
        tk.Label(
            layer_count_row,
            text="Number of layers",
            bg=PANEL,
            fg=TEXT,
            font=(FONT, 9),
        ).pack(side="left")
        tk.Spinbox(
            layer_count_row,
            from_=2,
            to=12,
            width=5,
            textvariable=self.layer_count,
            justify="center",
            bg=PANEL,
            fg=TEXT,
            buttonbackground=PANEL,
            relief="flat",
            readonlybackground=PANEL,
        ).pack(side="right")

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
        ).pack(anchor="w", pady=(8, 4))

        self.layers_frame = tk.Frame(controls, bg=PANEL)
        self.layers_frame.pack(fill="both", expand=True)

        flat_button(
            controls,
            "Add Layers to Timeline",
            self._export_layers,
        ).pack(fill="x", pady=(8, 0))

        self.preview_canvas.bind("<Configure>", self._redraw_preview)
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

        return layers

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
        self.layer_masks = layers
        self.processing_status.set(
            "Complete - {} local layers".format(len(layers))
        )
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

    def _export_layers(self):
        if not self.layer_masks:
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
        if hasattr(self, "preview_layer") and self.layer_masks:
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
        self.preview_canvas.create_image(
            x,
            y,
            anchor="nw",
            image=photo,
        )
