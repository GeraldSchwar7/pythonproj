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
        detection_confidence=0.6,
        tracking_confidence=0.6
    ):

        # ----------------------------------------------------
        # Find model relative to THIS Python file.
        # This prevents problems caused by running main.py
        # from a different working directory.
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
        # MediaPipe configuration
        # ----------------------------------------------------

        base_options = python.BaseOptions(
            model_asset_path=model_path
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,

            running_mode=vision.RunningMode.VIDEO,

            num_hands=max_hands,

            min_hand_detection_confidence=
                detection_confidence,

            min_tracking_confidence=
                tracking_confidence
        )

        self.landmarker = (
            vision.HandLandmarker.create_from_options(
                options
            )
        )

        self.results = None

        # MediaPipe VIDEO mode requires increasing timestamps.
        self.start_time = time.monotonic()

    # ========================================================
    # PROCESS FRAME
    # ========================================================

    def process(self, frame):

        # OpenCV:
        # BGR
        #
        # MediaPipe:
        # RGB

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=rgb_frame
        )

        timestamp_ms = int(
            (time.monotonic() - self.start_time)
            * 1000
        )

        self.results = (
            self.landmarker.detect_for_video(
                mp_image,
                timestamp_ms
            )
        )

        return self.results

    # ========================================================
    # CHECK FOR HAND
    # ========================================================

    def hand_detected(self):

        if self.results is None:
            return False

        return len(
            self.results.hand_landmarks
        ) > 0

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

        height, width = frame.shape[:2]

        x = int(
            landmark.x * width
        )

        y = int(
            landmark.y * height
        )

        return x, y

    # ========================================================
    # INDEX FINGER
    #
    # MediaPipe landmark 8
    # ========================================================

    def get_index_finger(self, frame):

        return self.get_landmark(
            frame,
            8
        )

    # ========================================================
    # THUMB
    #
    # MediaPipe landmark 4
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
    # DISTANCE BETWEEN LANDMARKS
    #
    # We'll use this later for gestures such as pinch.
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

        # Convert normalized landmarks to pixels.

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

        # ----------------------------------------------------
        # MediaPipe hand connections
        # ----------------------------------------------------

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
                2
            )

        # Draw landmarks.

        for index, point in enumerate(points):

            # Make index fingertip green.
            if index == 8:
                color = (0, 255, 0)
                radius = 8

            else:
                color = (0, 140, 255)
                radius = 4

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
        smoothing=0.25,
        margin=0.10
    ):

        self.screen_width, self.screen_height = (
            pyautogui.size()
        )

        self.smoothing = smoothing

        # Camera border that is ignored.
        #
        # Example:
        # 10% margin means you don't need to physically move
        # your finger all the way to the edge of the camera.
        self.margin = margin

        self.current_x = (
            self.screen_width / 2
        )

        self.current_y = (
            self.screen_height / 2
        )

        self.enabled = True

        pyautogui.FAILSAFE = False

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

        self.enabled = (
            not self.enabled
        )

        return self.enabled

    # ========================================================
    # MOVE CURSOR
    # ========================================================

    def move(
        self,
        finger_x,
        finger_y,
        frame_width,
        frame_height
    ):

        if not self.enabled:
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

        # ----------------------------------------------------
        # Convert finger position to 0-1
        # ----------------------------------------------------

        normalized_x = (
            (finger_x - margin_x)
            / usable_width
        )

        normalized_y = (
            (finger_y - margin_y)
            / usable_height
        )

        # Clamp values.

        normalized_x = max(
            0,
            min(
                1,
                normalized_x
            )
        )

        normalized_y = max(
            0,
            min(
                1,
                normalized_y
            )
        )

        # ----------------------------------------------------
        # Convert to screen coordinates
        # ----------------------------------------------------

        target_x = (
            normalized_x
            * self.screen_width
        )

        target_y = (
            normalized_y
            * self.screen_height
        )

        # ----------------------------------------------------
        # Smooth cursor
        # ----------------------------------------------------

        self.current_x += (
            target_x
            - self.current_x
        ) * self.smoothing

        self.current_y += (
            target_y
            - self.current_y
        ) * self.smoothing

        # ----------------------------------------------------
        # Keep cursor inside monitor
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
