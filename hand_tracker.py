
import os
import time
import math

import cv2
import mediapipe as mp
import pyautogui

from mediapipe.tasks import python
from mediapipe.tasks.python import vision


# ============================================================
# HAND TRACKER
# ============================================================

class HandTracker:

    def __init__(
        self,
        model_path=None,
        max_hands=1,
        detection_confidence=0.5,
        tracking_confidence=0.5,
        tracking_width=480,
        click_debounce=0.25
    ):

        # ----------------------------------------------------
        # Find MediaPipe model
        # ----------------------------------------------------

        if model_path is None:

            current_folder = os.path.dirname(
                os.path.abspath(__file__)
            )

            model_path = os.path.join(
                current_folder,
                "models",
                "hand_landmarker.task"
            )

        if not os.path.exists(model_path):

            raise FileNotFoundError(
                "\nHand Landmarker model was not found.\n"
                f"Expected location:\n{model_path}\n"
            )

        # ----------------------------------------------------
        # Tracking resolution
        #
        # MediaPipe does NOT need the full webcam resolution.
        # ----------------------------------------------------

        self.tracking_width = tracking_width

        # ----------------------------------------------------
        # MediaPipe configuration
        # ----------------------------------------------------

        base_options = python.BaseOptions(
            model_asset_path=model_path
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.VIDEO,
            num_hands=max_hands,
            min_hand_detection_confidence=detection_confidence,
            min_tracking_confidence=tracking_confidence
        )

        self.landmarker = (
            vision.HandLandmarker.create_from_options(
                options
            )
        )

        self.results = None

        self.start_time = time.monotonic()

        # Pinch / click state
        self.is_pinching = False
        self.last_click_time = 0.0
        self.click_debounce = max(0.0, float(click_debounce))
        self.pinch_start_time = None
        self.pinch_release_time = 0.0
        self.drag_threshold = 0.18
        self.drag_movement_threshold = 8.0
        self.pinch_start_position = None
        self.pinch_last_position = None
        self.pinch_dragging = False

        # Distance between thumb and index that counts as a pinch.
        # We'll tune this if needed.
        self.pinch_threshold = 35

        # Prevent MediaPipe from running every camera frame.
        self.last_process_time = 0

        # 30 FPS hand detection is plenty for now.
        self.tracking_interval = 1 / 30

    # ========================================================
    # PROCESS FRAME
    # ========================================================

    def process(self, frame):

        current_time = time.monotonic()

        # ----------------------------------------------------
        # Limit MediaPipe processing to ~20 FPS
        # ----------------------------------------------------

        if (
            current_time - self.last_process_time
            < self.tracking_interval
        ):
            return self.results

        self.last_process_time = current_time

        # ----------------------------------------------------
        # Resize ONLY the image going to MediaPipe
        # ----------------------------------------------------

        height, width = frame.shape[:2]

        scale = self.tracking_width / width

        tracking_height = max(
            1,
            int(height * scale)
        )

        small_frame = cv2.resize(
            frame,
            (
                self.tracking_width,
                tracking_height
            ),
            interpolation=cv2.INTER_AREA
        )

        # ----------------------------------------------------
        # BGR -> RGB
        # ----------------------------------------------------

        rgb_frame = cv2.cvtColor(
            small_frame,
            cv2.COLOR_BGR2RGB
        )

        # Make array contiguous for MediaPipe.
        rgb_frame = (
            rgb_frame.copy(order="C")
        )

        # ----------------------------------------------------
        # MediaPipe image
        # ----------------------------------------------------

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        timestamp_ms = int(
            (
                current_time
                - self.start_time
            )
            * 1000
        )

        # ----------------------------------------------------
        # Detect hand
        # ----------------------------------------------------

        self.results = (
            self.landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )
        )

        return self.results

    # ========================================================
    # HAND DETECTED
    # ========================================================

    def hand_detected(self):

        return (
            self.results is not None
            and len(
                self.results.hand_landmarks
            ) > 0
        )

    # ========================================================
    # GET LANDMARK
    # ========================================================

    def get_landmark(
        self,
        frame,
        landmark_id
    ):

        if not self.hand_detected():
            return None

        hand = (
            self.results.hand_landmarks[0]
        )

        if landmark_id >= len(hand):
            return None

        landmark = hand[landmark_id]

        # MediaPipe landmarks are normalized.
        #
        # That means they can be converted directly
        # to the ORIGINAL camera dimensions even though
        # detection ran on the smaller image.

        height, width = frame.shape[:2]

        x = int(
            landmark.x * width
        )

        y = int(
            landmark.y * height
        )

        return x, y

    # ========================================================
    # GET LANDMARKS
    # ========================================================
    def get_landmarks(self, frame):

        if not self.hand_detected():
            return None

        hand = self.results.hand_landmarks[0]

        height, width = frame.shape[:2]

        landmarks = {}

        for index, landmark in enumerate(hand):

            x = int(
                landmark.x * width
            )

            y = int(
                landmark.y * height
            )

            landmarks[index] = (
                x,
                y
            )

        return landmarks

    # ========================================================
    # INDEX FINGER
    # ========================================================

    def get_index_finger(self, frame):

        return self.get_landmark(
            frame,
            8
        )

    # ========================================================
    # THUMB
    # ========================================================

    def get_thumb(self, frame):

        return self.get_landmark(
            frame,
            4
        )

    # ========================================================
    # MIDDLE FINGER
    # ========================================================

    def get_middle_finger(self, frame):

        return self.get_landmark(
            frame,
            12
        )

    # ========================================================
    # LANDMARK DISTANCE
    # ========================================================

    def get_distance(
        self,
        frame,
        landmark1,
        landmark2
    ):

        point1 = self.get_landmark(
            frame,
            landmark1
        )

        point2 = self.get_landmark(
            frame,
            landmark2
        )

        if (
            point1 is None
            or point2 is None
        ):
            return None

        x1, y1 = point1
        x2, y2 = point2

        return math.hypot(
            x2 - x1,
            y2 - y1
        )

    def detect_pinch(self, frame):
        state = self.update_pinch(frame)
        return state["pressed"]

    def update_pinch(self, frame):
        distance = self.get_distance(frame, 4, 8)
        try:
            index_position = self.get_index_finger(frame)
        except (AttributeError, TypeError):
            index_position = None
        current_time = time.monotonic()

        if distance is None:
            distance = self.pinch_threshold + 1

        pinching = distance < self.pinch_threshold
        pressed = False
        released = False
        dragging = False

        if pinching:
            if not self.is_pinching:
                if current_time - self.last_click_time < self.click_debounce:
                    return {
                        "pinching": True,
                        "pressed": False,
                        "released": False,
                        "dragging": False
                    }

                self.is_pinching = True
                self.pinch_start_time = current_time
                self.pinch_start_position = index_position
                self.pinch_last_position = index_position
                self.pinch_dragging = False
                pressed = True

            if index_position is not None:
                if self.pinch_start_position is not None:
                    movement = math.hypot(
                        index_position[0] - self.pinch_start_position[0],
                        index_position[1] - self.pinch_start_position[1]
                    )
                else:
                    movement = 0.0

                held_long_enough = (
                    self.pinch_start_time is not None
                    and current_time - self.pinch_start_time >= self.drag_threshold
                )
                if movement >= self.drag_movement_threshold or held_long_enough:
                    self.pinch_dragging = True

                self.pinch_last_position = index_position

            dragging = self.pinch_dragging

        elif self.is_pinching:
            released = True
            dragging = self.pinch_dragging
            self.pinch_release_time = current_time
            self.last_click_time = current_time
            self.is_pinching = False
            self.pinch_start_time = None
            self.pinch_dragging = False
            self.pinch_start_position = None
            self.pinch_last_position = None

        return {
            "pinching": pinching,
            "pressed": pressed,
            "released": released,
            "dragging": dragging
        }

    # ========================================================
    # DRAW HAND
    # ========================================================

    def draw(self, frame):

        if not self.hand_detected():
            return frame

        hand = (
            self.results.hand_landmarks[0]
        )

        height, width = frame.shape[:2]

        points = []

        for landmark in hand:

            x = int(
                landmark.x * width
            )

            y = int(
                landmark.y * height
            )

            points.append(
                (x, y)
            )

        connections = [

            # Thumb
            (0, 1),
            (1, 2),
            (2, 3),
            (3, 4),

            # Index
            (0, 5),
            (5, 6),
            (6, 7),
            (7, 8),

            # Middle
            (5, 9),
            (9, 10),
            (10, 11),
            (11, 12),

            # Ring
            (9, 13),
            (13, 14),
            (14, 15),
            (15, 16),

            # Pinky
            (13, 17),
            (17, 18),
            (18, 19),
            (19, 20),

            # Palm
            (0, 17)
        ]

        # Draw connections.

        for start, end in connections:

            cv2.line(
                frame,
                points[start],
                points[end],
                (255, 255, 255),
                1
            )

        # Draw smaller landmarks.

        for index, point in enumerate(points):

            if index == 8:

                color = (0, 255, 0)
                radius = 6

            else:

                color = (0, 140, 255)
                radius = 3

            cv2.circle(
                frame,
                point,
                radius,
                color,
                -1
            )

        return frame

    # ========================================================
    # CLEANUP
    # ========================================================

    def close(self):

        self.landmarker.close()


# ============================================================
# HAND MOUSE CONTROLLER
# ============================================================

class HandMouseController:

    def __init__(
        self,
        smoothing=0.75,
        margin=0.10
    ):

        # ----------------------------------------------------
        # IMPORTANT PERFORMANCE FIX
        #
        # PyAutoGUI normally pauses after every call.
        # We are moving the mouse many times per second.
        # ----------------------------------------------------

        pyautogui.PAUSE = 0
        pyautogui.FAILSAFE = False

        self.screen_width, self.screen_height = (
            pyautogui.size()
        )

        # Higher than the previous 0.25.
        #
        # 0.25 = smoother but noticeably delayed
        # 0.50 = good starting point
        # 0.70 = faster but more jittery
        self.smoothing = max(
            0.0,
            min(1.0, float(smoothing))
        )

        self.margin = margin

        self.current_x = (
            self.screen_width / 2
        )

        self.current_y = (
            self.screen_height / 2
        )

        self.enabled = True

        # ----------------------------------------------------
        # Mouse update limiting
        # ----------------------------------------------------

        self.last_move_time = 0

        # Maximum ~60 cursor updates per second.
        self.move_interval = 1 / 60

        # Ignore extremely tiny movements.
        self.deadzone = 2
        self.is_mouse_down = False
        self.last_click_time = 0.0
        self.last_click_x = 0.0
        self.last_click_y = 0.0
        self.double_click_interval = 0.35
        self.double_click_distance = 28
        self.acceleration = 1.25
        self.max_acceleration = 2.2

    # ========================================================
    # ENABLE
    # ========================================================

    def enable(self):

        self.enabled = True

    # ========================================================
    # DISABLE
    # ========================================================

    def disable(self):

        self.enabled = False

    # ========================================================
    # TOGGLE
    # ========================================================

    def toggle(self):

        self.enabled = not self.enabled

        return self.enabled

    # ========================================================
    # MOVE CURSOR
    # ========================================================


    def click(self):
        if not self.enabled:
            return
        current_time = time.monotonic()
        distance = math.hypot(
            self.current_x - self.last_click_x,
            self.current_y - self.last_click_y
        )
        is_double = (
            current_time - self.last_click_time <= self.double_click_interval
            and distance <= self.double_click_distance
            and self.last_click_time > 0
        )

        if is_double:
            pyautogui.doubleClick(
                int(self.current_x),
                int(self.current_y)
            )
            self.last_click_time = 0.0
        else:
            pyautogui.click(
                int(self.current_x),
                int(self.current_y)
            )
            self.last_click_time = current_time

        self.last_click_x = self.current_x
        self.last_click_y = self.current_y

    def mouse_down(self):
        if not self.enabled or self.is_mouse_down:
            return
        pyautogui.mouseDown(
            int(self.current_x),
            int(self.current_y),
            button="left"
        )
        self.is_mouse_down = True

    def mouse_up(self):
        if not self.enabled or not self.is_mouse_down:
            return
        pyautogui.mouseUp(
            int(self.current_x),
            int(self.current_y),
            button="left"
        )
        self.is_mouse_down = False

    def move(
        self,
        finger_x,
        finger_y,
        frame_width,
        frame_height
    ):

        if not self.enabled:
            return

        current_time = time.monotonic()

        if (
            current_time - self.last_move_time
            < self.move_interval
        ):
            return

        # ----------------------------------------------------
        # Active camera area
        # ----------------------------------------------------

        margin_x = (
            frame_width
            * self.margin
        )

        margin_y = (
            frame_height
            * self.margin
        )

        usable_width = (
            frame_width
            - (2 * margin_x)
        )

        usable_height = (
            frame_height
            - (2 * margin_y)
        )

        if (
            usable_width <= 0
            or usable_height <= 0
        ):
            return

        elapsed = (
            1 / 60
            if self.last_move_time == 0
            else current_time - self.last_move_time
        )
        self.last_move_time = current_time

        # ----------------------------------------------------
        # Normalize finger position
        # ----------------------------------------------------

        normalized_x = (
            (finger_x - margin_x)
            / usable_width
        )

        normalized_y = (
            (finger_y - margin_y)
            / usable_height
        )

        normalized_x = max(
            0.0,
            min(
                1.0,
                normalized_x
            )
        )

        normalized_y = max(
            0.0,
            min(
                1.0,
                normalized_y
            )
        )

        # ----------------------------------------------------
        # Convert to monitor position
        # ----------------------------------------------------

        target_x = (
            normalized_x
            * (self.screen_width - 1)
        )

        target_y = (
            normalized_y
            * (self.screen_height - 1)
        )

        # ----------------------------------------------------
        # Smooth
        # ----------------------------------------------------

        smoothing_step = min(
            max(elapsed / (1 / 60), 0.0),
            4.0
        )
        alpha = 1.0 - (
            (1.0 - self.smoothing) ** smoothing_step
        )

        camera_distance = math.hypot(
            target_x - self.current_x,
            target_y - self.current_y
        )
        speed_ratio = min(
            camera_distance / 180.0,
            1.0
        )
        acceleration_alpha = (
            1.0
            - (
                1.0 - alpha
            )
            * (
                1.0
                - (
                    0.55
                    * speed_ratio
                )
            )
        )
        alpha = max(
            alpha,
            min(acceleration_alpha, 1.0)
        )

        new_x = (
            self.current_x
            + (
                target_x
                - self.current_x
            )
            * alpha
        )

        new_y = (
            self.current_y
            + (
                target_y
                - self.current_y
            )
            * alpha
        )

        # ----------------------------------------------------
        # Ignore tiny movements
        # ----------------------------------------------------

        movement = math.hypot(
            new_x - self.current_x,
            new_y - self.current_y
        )

        if movement < self.deadzone:
            return

        self.current_x = new_x
        self.current_y = new_y

        # ----------------------------------------------------
        # Clamp
        # ----------------------------------------------------

        self.current_x = max(
            0,
            min(
                self.screen_width - 1,
                self.current_x
            )
        )

        self.current_y = max(
            0,
            min(
                self.screen_height - 1,
                self.current_y
            )
        )

        # ----------------------------------------------------
        # Move Windows cursor
        # ----------------------------------------------------

        pyautogui.moveTo(
            int(self.current_x),
            int(self.current_y),
            duration=0
        )
