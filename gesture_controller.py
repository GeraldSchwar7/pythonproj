import time
import math


# ============================================================
# GESTURE CONTROLLER
#
# Interprets one cached 21-landmark snapshot from HandTracker.
# ============================================================

class GestureController:

    def __init__(self):

        self.tool_hold_duration = 2.0
        self.tool_release_debounce = 0.15
        self.pending_tool = None
        self.tool_start_time = None
        self.release_start_time = None
        self.active_tool = None

    # ========================================================
    # HELPERS
    # ========================================================

    def _distance(self, landmarks, point1, point2):

        if (
            landmarks is None
            or point1 not in landmarks
            or point2 not in landmarks
        ):
            return None

        x1, y1 = landmarks[point1]
        x2, y2 = landmarks[point2]

        return math.hypot(
            x2 - x1,
            y2 - y1
        )

    def _finger_extended(
        self,
        landmarks,
        tip,
        pip,
        mcp
    ):

        tip_distance = self._distance(
            landmarks, tip, 0
        )

        pip_distance = self._distance(
            landmarks, pip, 0
        )

        mcp_distance = self._distance(
            landmarks, mcp, 0
        )

        if (
            tip_distance is None
            or pip_distance is None
            or mcp_distance is None
        ):
            return False

        return (
            tip_distance > pip_distance
            and tip_distance > mcp_distance
        )

    def _finger_states(self, landmarks):

        return {
            "index": self._finger_extended(
                landmarks, 8, 6, 5
            ),
            "middle": self._finger_extended(
                landmarks, 12, 10, 9
            ),
            "ring": self._finger_extended(
                landmarks, 16, 14, 13
            ),
            "pinky": self._finger_extended(
                landmarks, 20, 18, 17
            )
        }

    # ========================================================
    # MOVE: CLOSED FIST
    # ========================================================

    def is_fist(self, landmarks):

        if landmarks is None:
            return False

        fingers = self._finger_states(
            landmarks
        )

        return (
            not fingers["index"]
            and not fingers["middle"]
            and not fingers["ring"]
            and not fingers["pinky"]
        )

    # ========================================================
    # LEGACY OK-SIGN DETECTION
    # ========================================================

    def is_ok_sign(self, landmarks):

        if landmarks is None:
            return False

        pinch_distance = self._distance(
            landmarks, 4, 8
        )

        palm_size = self._distance(
            landmarks, 0, 9
        )

        if (
            pinch_distance is None
            or palm_size is None
            or palm_size == 0
        ):
            return False

        fingers = self._finger_states(
            landmarks
        )

        touching = (
            pinch_distance
            < palm_size * 0.35
        )

        return (
            touching
            and fingers["middle"]
            and fingers["ring"]
            and fingers["pinky"]
        )

    # SELECT: OK SIGN
    def is_open_palm(self, landmarks):
        if landmarks is None:
            return False

        fingers = self._finger_states(landmarks)
        thumb_tip = self._distance(landmarks, 4, 0)
        thumb_ip = self._distance(landmarks, 3, 0)
        thumb_mcp = self._distance(landmarks, 2, 0)

        return (
            all(fingers.values())
            and thumb_tip is not None
            and thumb_ip is not None
            and thumb_mcp is not None
            and thumb_tip > thumb_ip
            and thumb_tip > thumb_mcp
        )

    # ========================================================
    # CUT: SCISSORS
    # ========================================================

    def is_scissors(self, landmarks):

        if landmarks is None:
            return False

        fingers = self._finger_states(
            landmarks
        )

        gap = self._distance(
            landmarks, 8, 12
        )

        palm_size = self._distance(
            landmarks, 0, 9
        )

        if (
            gap is None
            or palm_size is None
            or palm_size == 0
        ):
            return False

        separated = (
            gap > palm_size * 0.30
        )

        return (
            fingers["index"]
            and fingers["middle"]
            and not fingers["ring"]
            and not fingers["pinky"]
            and separated
        )

    # ========================================================
    # RESIZE: L SIGN
    # ========================================================

    def is_resize_sign(self, landmarks):

        if landmarks is None:
            return False

        fingers = self._finger_states(
            landmarks
        )

        # ASL R:
        # index + middle extended
        # ring + pinky folded
        if not (
            fingers["index"]
            and fingers["middle"]
            and not fingers["ring"]
            and not fingers["pinky"]
        ):
            return False

        # Distance between index and middle fingertips
        finger_gap = self._distance(
            landmarks,
            8,
            12
        )

        # Use palm size so detection works at
        # different distances from the camera
        palm_size = self._distance(
            landmarks,
            0,
            9
        )

        if (
            finger_gap is None
            or palm_size is None
            or palm_size == 0
        ):
            return False

        gap_ratio = (
            finger_gap / palm_size
        )

        # R fingers should be close/crossed.
        fingers_together = (
            gap_ratio < 0.28
        )

        return fingers_together

    # ========================================================
    # COPY: C SIGN
    # ========================================================

    def is_copy_sign(self, landmarks):

        if landmarks is None:
            return False

        thumb_tip = landmarks.get(4)
        index_tip = landmarks.get(8)
        middle_tip = landmarks.get(12)
        ring_tip = landmarks.get(16)
        pinky_tip = landmarks.get(20)

        if any(
            point is None
            for point in (
                thumb_tip,
                index_tip,
                middle_tip,
                ring_tip,
                pinky_tip
            )
        ):
            return False

        palm_size = self._distance(
            landmarks, 0, 9
        )

        thumb_index = self._distance(
            landmarks, 4, 8
        )

        if (
            palm_size is None
            or thumb_index is None
            or palm_size == 0
        ):
            return False

        gap_ratio = (
            thumb_index / palm_size
        )

        c_gap = (
            0.45
            < gap_ratio
            < 1.40
        )

        fingers_above_thumb = (
            index_tip[1] < thumb_tip[1]
            and middle_tip[1] < thumb_tip[1]
            and ring_tip[1] < thumb_tip[1]
        )

        fingers = self._finger_states(
            landmarks
        )

        enough_fingers = (
            fingers["middle"]
            or fingers["ring"]
            or fingers["pinky"]
        )

        return (
            c_gap
            and fingers_above_thumb
            and enough_fingers
        )

    # ========================================================
    # TOOL DETECTION
    # ========================================================

    def detect_tool_gesture(
        self,
        landmarks
    ):

        if landmarks is None:
            return None

        if self.is_ok_sign(
            landmarks
        ):
            return "Select"

        if self.is_scissors(
            landmarks
        ):
            return "Cut"

        if self.is_resize_sign(
            landmarks
        ):
            return "Resize"

        if self.is_copy_sign(
            landmarks
        ):
            return "Copy"

        if self.is_fist(
            landmarks
        ):
            return "Move"

        return None

    # ========================================================
    # HOLD TO ACTIVATE
    # ========================================================

    def update_tool_gesture(
        self,
        detected_tool
    ):

        if detected_tool is None:

            if self.pending_tool is None:
                return {
                    "active": False,
                    "tool": None,
                    "progress": 0.0,
                    "triggered": False
                }

            now = time.monotonic()
            if self.release_start_time is None:
                self.release_start_time = now

            if now - self.release_start_time >= self.tool_release_debounce:
                self.pending_tool = None
                self.tool_start_time = None
                self.release_start_time = None
                self.active_tool = None

            return {
                "active": self.pending_tool is not None,
                "tool": self.pending_tool,
                "progress": self._tool_progress(now),
                "triggered": False
            }

        if detected_tool != self.pending_tool:

            self.pending_tool = detected_tool
            self.tool_start_time = (
                time.monotonic()
            )
            self.release_start_time = None

            return {
                "active": True,
                "tool": detected_tool,
                "progress": 0.0,
                "triggered": False
            }

        self.release_start_time = None
        now = time.monotonic()
        progress = self._tool_progress(now)

        triggered = False

        if (
            progress >= 1.0
            and self.active_tool != detected_tool
        ):
            self.active_tool = detected_tool
            triggered = True

        return {
            "active": True,
            "tool": detected_tool,
            "progress": progress,
            "triggered": triggered
        }

    def _tool_progress(self, now):
        if self.tool_start_time is None:
            return 0.0

        return min(
            max(0.0, now - self.tool_start_time)
            / self.tool_hold_duration,
            1.0
        )
