
import math
import os
import time

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
        click_debounce=0.06,
        click_hold_duration=2.0
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
        self.click_debounce = max(0.0, float(click_debounce))
        self.click_hold_duration = max(
            0.0,
            float(click_hold_duration)
        )
        self.pinch_release_time = 0.0
        self.pinch_suppressed_until = 0.0
        self.pinch_cancel_cooldown = 0.22
        self.pinch_missing_since = None
        self.pinch_tracking_grace = 0.10
        self.pinch_release_threshold_ratio = 0.42
        self.pinch_engage_threshold_ratio = 0.30
        self.pinch_sensitivity = 1.0
        self.drag_movement_threshold = 12.0
        self.pinch_start_position = None
        self.pinch_last_position = None
        self.pinch_dragging = False
        self.pinch_drag_frames = 0
        self.pinch_release_frames = 0
        self.pinch_release_confirm_frames = 2
        self.pinch_start_time = None
        self.pinch_click_fired = False

        # Distance between thumb and index that counts as a pinch.
        # We'll tune this if needed.
        self.pinch_threshold = 35

        # Prevent MediaPipe from running every camera frame.
        self.last_process_time = 0

        # 30 FPS hand detection is plenty for now.
        self.tracking_interval = 1 / 30

    def set_pinch_sensitivity(self, value):
        self.pinch_sensitivity = max(0.6, min(1.4, float(value)))
        self.pinch_engage_threshold_ratio = 0.30 * self.pinch_sensitivity
        self.pinch_release_threshold_ratio = 0.42 * self.pinch_sensitivity

    def set_drag_movement_threshold(self, value):
        self.drag_movement_threshold = max(6.0, min(40.0, float(value)))

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

    def get_palm_center(self, frame):
        palm_landmarks = (0, 5, 9, 13, 17)
        points = [
            self.get_landmark(frame, landmark_id)
            for landmark_id in palm_landmarks
        ]
        if any(point is None for point in points):
            return None
        valid_points = [point for point in points if point is not None]

        return (
            sum(point[0] for point in valid_points) / len(valid_points),
            sum(point[1] for point in valid_points) / len(valid_points)
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

    def cancel_pinch(self):
        current_time = time.monotonic()
        self.pinch_release_time = current_time
        self.pinch_suppressed_until = (
            current_time + self.pinch_cancel_cooldown
        )
        state = {
            "pinching": False,
            "pressed": False,
            "clicked": False,
            "tap": False,
            "released": self.is_pinching,
            "dragging": self.pinch_dragging,
            "drag_offset": (0.0, 0.0),
            "cancelled": True
        }
        self._reset_pinch_state()
        return state

    def update_pinch(self, frame):
        distance = self.get_distance(frame, 4, 8)
        palm_size = self.get_distance(frame, 0, 9)
        try:
            hand_position = self.get_palm_center(frame)
        except (AttributeError, TypeError):
            hand_position = None
        current_time = time.monotonic()
        cancelled = False
        pressed = False
        clicked = False
        tap = False
        released = False
        dragging = False
        drag_offset = (0.0, 0.0)
        if (
            self.is_pinching
            and self.pinch_start_position is not None
            and self.pinch_last_position is not None
        ):
            drag_offset = (
                self.pinch_last_position[0] - self.pinch_start_position[0],
                self.pinch_last_position[1] - self.pinch_start_position[1]
            )

        if distance is None:
            if self.is_pinching:
                if self.pinch_missing_since is None:
                    self.pinch_missing_since = current_time
                if (
                    current_time - self.pinch_missing_since
                    <= self.pinch_tracking_grace
                ):
                    return {
                        "pinching": True,
                        "pressed": False,
                        "clicked": False,
                        "tap": False,
                        "released": False,
                        "dragging": self.pinch_dragging,
                        "drag_offset": drag_offset,
                        "cancelled": False
                    }

                released = True
                cancelled = True
                dragging = self.pinch_dragging
                self._reset_pinch_state()
            return {
                "pinching": False,
                "pressed": False,
                "clicked": False,
                "tap": False,
                "released": released,
                "dragging": dragging,
                "drag_offset": drag_offset,
                "cancelled": cancelled
            }

        self.pinch_missing_since = None
        if palm_size is not None and palm_size > 0:
            pinch_ratio = distance / palm_size
            threshold = (
                self.pinch_release_threshold_ratio
                if self.is_pinching
                else self.pinch_engage_threshold_ratio
            )
            pinching = pinch_ratio <= threshold
        else:
            threshold = (
                self.pinch_threshold * 1.35
                if self.is_pinching
                else self.pinch_threshold
            )
            pinching = distance <= threshold

        if pinching:
            self.pinch_release_frames = 0
            if not self.is_pinching:
                if current_time < self.pinch_suppressed_until:
                    return {
                        "pinching": True,
                        "pressed": False,
                        "clicked": False,
                        "tap": False,
                        "released": False,
                        "dragging": False,
                        "drag_offset": drag_offset,
                        "cancelled": False
                    }
                if (
                    current_time - self.pinch_release_time
                    < self.click_debounce
                ):
                    return {
                        "pinching": True,
                        "pressed": False,
                        "clicked": False,
                        "tap": False,
                        "released": False,
                        "dragging": False,
                        "drag_offset": drag_offset,
                        "cancelled": False
                    }

                self.is_pinching = True
                self.pinch_start_time = current_time
                self.pinch_start_position = hand_position
                self.pinch_last_position = hand_position
                self.pinch_dragging = False
                self.pinch_drag_frames = 0
                self.pinch_click_fired = False
                pressed = True

            if hand_position is not None:
                if self.pinch_start_position is not None:
                    drag_offset = (
                        hand_position[0] - self.pinch_start_position[0],
                        hand_position[1] - self.pinch_start_position[1]
                    )
                    movement = math.hypot(
                        hand_position[0] - self.pinch_start_position[0],
                        hand_position[1] - self.pinch_start_position[1]
                    )
                else:
                    self.pinch_start_position = hand_position
                    movement = 0.0

                if (
                    movement >= self.drag_movement_threshold
                    and not self.pinch_click_fired
                ):
                    self.pinch_drag_frames += 1
                    if self.pinch_drag_frames >= 2:
                        self.pinch_dragging = True
                else:
                    self.pinch_drag_frames = 0

                self.pinch_last_position = hand_position

                if (
                    not self.pinch_dragging
                    and not self.pinch_click_fired
                    and movement < self.drag_movement_threshold
                    and self.pinch_start_time is not None
                    and current_time - self.pinch_start_time
                    >= self.click_hold_duration
                ):
                    clicked = True
                    self.pinch_click_fired = True

            dragging = self.pinch_dragging

        elif self.is_pinching:
            self.pinch_release_frames += 1
            if self.pinch_release_frames < self.pinch_release_confirm_frames:
                return {
                    "pinching": True,
                    "pressed": False,
                    "clicked": False,
                    "tap": False,
                    "released": False,
                    "dragging": self.pinch_dragging,
                    "drag_offset": drag_offset,
                    "cancelled": False
                }
            released = True
            dragging = self.pinch_dragging
            tap = not self.pinch_dragging and not self.pinch_click_fired
            self.pinch_release_time = current_time
            self._reset_pinch_state()

        return {
            "pinching": pinching,
            "pressed": pressed,
            "clicked": clicked,
            "tap": tap,
            "released": released,
            "dragging": dragging,
            "drag_offset": drag_offset,
            "cancelled": cancelled
        }

    def _reset_pinch_state(self):
        self.is_pinching = False
        self.pinch_start_time = None
        self.pinch_missing_since = None
        self.pinch_dragging = False
        self.pinch_drag_frames = 0
        self.pinch_release_frames = 0
        self.pinch_click_fired = False
        self.pinch_start_position = None
        self.pinch_last_position = None

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
        self.sensitivity = 1.0
        self.calibration_bounds = None

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
        self.deadzone = 0.0
        self.last_sent_x = int(self.current_x)
        self.last_sent_y = int(self.current_y)
        self.is_mouse_down = False
        self.drag_origin_x = self.current_x
        self.drag_origin_y = self.current_y
        self.filter_raw_x = self.current_x
        self.filter_raw_y = self.current_y
        self.filter_velocity_x = 0.0
        self.filter_velocity_y = 0.0
        self.filter_cutoff = 0.7 + 1.6 * (1.0 - self.smoothing)
        self.filter_beta = 0.012

    # ========================================================
    # ENABLE
    # ========================================================

    def enable(self):

        self.enabled = True

    # ========================================================
    # DISABLE
    # ========================================================

    def disable(self):
        self.mouse_up()
        self.enabled = False

    # ========================================================
    # TOGGLE
    # ========================================================

    def toggle(self):

        self.enabled = not self.enabled
        if not self.enabled:
            self.mouse_up()

        return self.enabled

    def set_sensitivity(self, value):
        self.sensitivity = max(0.5, min(2.0, float(value)))

    def set_smoothing(self, value):
        self.smoothing = max(0.0, min(1.0, float(value)))
        self.filter_cutoff = 0.7 + 1.6 * (1.0 - self.smoothing)

    def set_calibration_bounds(
        self,
        first_point,
        second_point,
        frame_width,
        frame_height
    ):
        if frame_width <= 0 or frame_height <= 0:
            return False

        left, right = sorted((first_point[0], second_point[0]))
        top, bottom = sorted((first_point[1], second_point[1]))
        if (
            right - left < frame_width * 0.15
            or bottom - top < frame_height * 0.15
        ):
            return False

        self.calibration_bounds = (
            max(0.0, min(1.0, left / frame_width)),
            max(0.0, min(1.0, top / frame_height)),
            max(0.0, min(1.0, right / frame_width)),
            max(0.0, min(1.0, bottom / frame_height))
        )
        return True

    def clear_calibration_bounds(self):
        self.calibration_bounds = None

    # ========================================================
    # MOVE CURSOR
    # ========================================================


    def click(self):
        if not self.enabled:
            return
        pyautogui.click(
            int(self.current_x),
            int(self.current_y)
        )

    def tap(self):
        self.click()

    def mouse_down(self):
        if not self.enabled or self.is_mouse_down:
            return
        pyautogui.mouseDown(
            int(self.current_x),
            int(self.current_y),
            button="left"
        )
        self.is_mouse_down = True
        self.drag_origin_x = self.current_x
        self.drag_origin_y = self.current_y

    def mouse_up(self):
        if not self.is_mouse_down:
            return
        pyautogui.mouseUp(
            int(self.current_x),
            int(self.current_y),
            button="left"
        )
        self.is_mouse_down = False

    def move_drag(
        self,
        offset_x,
        offset_y,
        frame_width,
        frame_height
    ):
        if not self.enabled or not self.is_mouse_down:
            return
        usable_width = frame_width * (1.0 - 2.0 * self.margin)
        usable_height = frame_height * (1.0 - 2.0 * self.margin)
        if usable_width <= 0 or usable_height <= 0:
            return
        current_time = time.monotonic()
        if current_time - self.last_move_time < self.move_interval:
            return
        target_x = self.drag_origin_x + offset_x * (
            (self.screen_width - 1) / usable_width
        ) * self.sensitivity
        target_y = self.drag_origin_y + offset_y * (
            (self.screen_height - 1) / usable_height
        ) * self.sensitivity
        self._move_to(target_x, target_y, current_time)

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
        if current_time - self.last_move_time < self.move_interval:
            return
        if self.calibration_bounds is None:
            margin_x = frame_width * self.margin
            margin_y = frame_height * self.margin
            usable_width = frame_width - (2 * margin_x)
            usable_height = frame_height - (2 * margin_y)
            if usable_width <= 0 or usable_height <= 0:
                return
            raw_x = (finger_x - margin_x) / usable_width
            raw_y = (finger_y - margin_y) / usable_height
        else:
            left, top, right, bottom = self.calibration_bounds
            usable_width = (right - left) * frame_width
            usable_height = (bottom - top) * frame_height
            if usable_width <= 0 or usable_height <= 0:
                return
            raw_x = (finger_x - left * frame_width) / usable_width
            raw_y = (finger_y - top * frame_height) / usable_height

        normalized_x = max(
            0.0,
            min(1.0, 0.5 + (raw_x - 0.5) * self.sensitivity)
        )
        normalized_y = max(
            0.0,
            min(1.0, 0.5 + (raw_y - 0.5) * self.sensitivity)
        )
        target_x = normalized_x * (self.screen_width - 1)
        target_y = normalized_y * (self.screen_height - 1)
        self._move_to(target_x, target_y, current_time)

    def _move_to(self, target_x, target_y, current_time):
        elapsed = (
            1 / 60
            if self.last_move_time == 0
            else current_time - self.last_move_time
        )
        elapsed = max(0.005, min(elapsed, 0.1))
        self.last_move_time = current_time

        def filter_axis(target, previous, raw_previous, velocity_previous):
            raw_velocity = (target - raw_previous) / elapsed
            derivative_alpha = 1.0 / (
                1.0 + 1.0 / (2.0 * math.pi * 1.0 * elapsed)
            )
            velocity = (
                derivative_alpha * raw_velocity
                + (1.0 - derivative_alpha) * velocity_previous
            )
            cutoff = self.filter_cutoff + self.filter_beta * abs(velocity)
            alpha = 1.0 / (
                1.0 + 1.0 / (2.0 * math.pi * cutoff * elapsed)
            )
            filtered = alpha * target + (1.0 - alpha) * previous
            return filtered, velocity

        new_x, self.filter_velocity_x = filter_axis(
            target_x,
            self.current_x,
            self.filter_raw_x,
            self.filter_velocity_x
        )
        new_y, self.filter_velocity_y = filter_axis(
            target_y,
            self.current_y,
            self.filter_raw_y,
            self.filter_velocity_y
        )
        self.filter_raw_x = target_x
        self.filter_raw_y = target_y

        movement = math.hypot(
            new_x - self.current_x,
            new_y - self.current_y
        )
        if movement < self.deadzone:
            return

        self.current_x = max(0, min(self.screen_width - 1, new_x))
        self.current_y = max(0, min(self.screen_height - 1, new_y))
        screen_x = int(self.current_x)
        screen_y = int(self.current_y)
        if screen_x == self.last_sent_x and screen_y == self.last_sent_y:
            return
        pyautogui.moveTo(
            screen_x,
            screen_y,
            duration=0
        )
        self.last_sent_x = screen_x
        self.last_sent_y = screen_y
