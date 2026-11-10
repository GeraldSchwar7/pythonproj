import time
import math


# ============================================================
# GESTURE CONTROLLER
#
# Converts hand landmarks into editor gestures.
#
# HandTracker = WHERE is the hand?
# GestureController = WHAT is the hand doing?
# ============================================================


class GestureController:

    def __init__(self):

        # --------------------------------
        # Delete gesture
        # --------------------------------

        self.delete_hold_duration = 3.0

        self.fist_start_time = None

        self.delete_triggered = False

    # ========================================================
    # FINGER DISTANCE
    # ========================================================

    def _distance(self, a, b):

        return math.sqrt(
            (a.x - b.x) ** 2
            + (a.y - b.y) ** 2
            + (a.z - b.z) ** 2
        )

    # ========================================================
    # FIST DETECTION
    # ========================================================

    def is_fist(self, hand_landmarks):

        if hand_landmarks is None:
            return False

        if len(hand_landmarks) < 21:
            return False

        # Wrist
        wrist = hand_landmarks[0]

        # Finger tips
        index_tip = hand_landmarks[8]
        middle_tip = hand_landmarks[12]
        ring_tip = hand_landmarks[16]
        pinky_tip = hand_landmarks[20]

        # Finger MCP/base joints
        index_base = hand_landmarks[5]
        middle_base = hand_landmarks[9]
        ring_base = hand_landmarks[13]
        pinky_base = hand_landmarks[17]

        # ----------------------------------------------------
        # Compare each fingertip's distance to the wrist
        # against its base joint's distance to the wrist.
        #
        # When curled into a fist, the fingertip moves
        # substantially closer to the palm/wrist.
        # ----------------------------------------------------

        index_folded = (
            self._distance(
                index_tip,
                wrist
            )
            <
            self._distance(
                index_base,
                wrist
            ) * 1.45
        )

        middle_folded = (
            self._distance(
                middle_tip,
                wrist
            )
            <
            self._distance(
                middle_base,
                wrist
            ) * 1.45
        )

        ring_folded = (
            self._distance(
                ring_tip,
                wrist
            )
            <
            self._distance(
                ring_base,
                wrist
            ) * 1.45
        )

        pinky_folded = (
            self._distance(
                pinky_tip,
                wrist
            )
            <
            self._distance(
                pinky_base,
                wrist
            ) * 1.45
        )

        return (
            index_folded
            and middle_folded
            and ring_folded
            and pinky_folded
        )

    # ========================================================
    # DELETE TIMER
    # ========================================================

    def update_delete_gesture(
        self,
        fist_detected
    ):

        # --------------------------------
        # No fist
        # --------------------------------

        if not fist_detected:

            self.fist_start_time = None

            self.delete_triggered = False

            return {
                "active": False,
                "progress": 0.0,
                "remaining":
                    self.delete_hold_duration,
                "triggered": False
            }

        # --------------------------------
        # Fist just started
        # --------------------------------

        if self.fist_start_time is None:

            self.fist_start_time = (
                time.monotonic()
            )

        # --------------------------------
        # Timer
        # --------------------------------

        elapsed = (
            time.monotonic()
            - self.fist_start_time
        )

        progress = min(
            elapsed
            / self.delete_hold_duration,
            1.0
        )

        remaining = max(
            self.delete_hold_duration
            - elapsed,
            0.0
        )

        # --------------------------------
        # Trigger delete ONCE
        # --------------------------------

        triggered = False

        if (
            progress >= 1.0
            and not self.delete_triggered
        ):

            self.delete_triggered = True

            triggered = True

        return {
            "active": True,
            "progress": progress,
            "remaining": remaining,
            "triggered": triggered
        }