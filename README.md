# Project Python Libraries

Wohoo, importing a lot of stuff. 

```powershell
testing.venv\Scripts\python.exe -m pip install opencv-python mediapipe pyautogui pillow numpy onnxruntime torch transformers ultralytics onnx onnxscript onnxslim safetensors
```

## Application Libraries

| Package | Import | Purpose |
|---|---|---|
| `opencv-python` | `import cv2` | Camera capture, image processing, DNN inference, and video metadata |
| `numpy` | `import numpy as np` | Image arrays, depth maps, masks, and numerical processing |
| `pillow` | `from PIL import Image, ImageTk` | Tkinter image display and PNG/RGBA export |
| `mediapipe` | `import mediapipe as mp` | Hand tracking and MediaPipe Tasks |
| `pyautogui` | `import pyautogui` | Gesture-controller mouse and keyboard automation |

## Scene Separation Libraries (the new stuff)

| Package | Import | Purpose |
|---|---|---|
| `onnxruntime` | `import onnxruntime as ort` | Local DPT-Hybrid depth-model inference |
| `torch` | `import torch` | Loading/exporting PyTorch scene-separation models |
| `transformers` | `from transformers import DPTForDepthEstimation` | DPT-Hybrid-MiDaS depth model |
| `ultralytics` | `from ultralytics import YOLO` | YOLO11n-seg instance-segmentation model |
| `onnx` | `import onnx` | ONNX model representation and validation |
| `onnxscript` | `import onnxscript` | ONNX model export support |
| `onnxslim` | `from onnxslim import slim` | ONNX model optimization |
| `safetensors` | `import safetensors` | Safe model-weight support |
