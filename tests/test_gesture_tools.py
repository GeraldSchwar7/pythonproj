import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pyautogui

from app import CameraViewerApp
from asset_browser import AssetBrowser
from gesture_controller import GestureController
from hand_tracker import HandMouseController, HandTracker
from layer import Layer
from media_clip import MediaClip
from timeline_panel import TimelinePanel


class GestureControllerTests(unittest.TestCase):
    def test_asl_y_select_gesture_is_distinct_from_move_fist(self):
        controller = GestureController()
        ok_sign_landmarks = {
            0: (0, 0),
            4: (5, 40),
            5: (0, 30),
            6: (10, 20),
            8: (5, 41),
            9: (0, 100),
            10: (0, 90),
            12: (0, 150),
            13: (30, 100),
            14: (30, 80),
            16: (30, 160),
            17: (60, 90),
            18: (60, 70),
            20: (60, 140)
        }
        asl_y_landmarks = {
            0: (0, 0),
            2: (20, 15),
            3: (30, 5),
            4: (50, 5),
            5: (0, 30),
            6: (10, 20),
            8: (5, 10),
            9: (0, 100),
            10: (0, 90),
            12: (0, 70),
            13: (30, 100),
            14: (30, 80),
            16: (20, 70),
            17: (60, 90),
            18: (60, 70),
            20: (90, 100)
        }
        move_fist_landmarks = {
            0: (0, 0),
            2: (20, 15),
            3: (10, 20),
            4: (5, 10),
            5: (0, 30),
            6: (10, 20),
            8: (5, 10),
            9: (0, 100),
            10: (0, 90),
            12: (0, 70),
            13: (30, 100),
            14: (30, 80),
            16: (20, 70),
            17: (60, 90),
            18: (60, 70),
            20: (40, 65)
        }
        open_palm_landmarks = {
            0: (0, 0),
            2: (20, 15),
            3: (40, 10),
            4: (60, 0),
            5: (0, 30),
            6: (10, 20),
            8: (5, 60),
            9: (0, 100),
            10: (0, 90),
            12: (0, 150),
            13: (30, 100),
            14: (30, 80),
            16: (30, 160),
            17: (60, 90),
            18: (60, 70),
            20: (60, 140)
        }

        self.assertEqual(controller.detect_tool_gesture(asl_y_landmarks), "Select")
        self.assertFalse(controller.is_asl_y(ok_sign_landmarks))
        self.assertNotEqual(
            controller.detect_tool_gesture(ok_sign_landmarks),
            "Select"
        )
        self.assertFalse(controller.is_asl_y(move_fist_landmarks))
        self.assertEqual(controller.detect_tool_gesture(move_fist_landmarks), "Move")
        self.assertIsNone(controller.detect_tool_gesture(open_palm_landmarks))
        self.assertFalse(
            controller.update_tool_gesture("Select")["triggered"]
        )

    def test_tool_requires_hold_and_rearms_after_release(self):
        controller = GestureController()
        times = iter((0.0, 2.0, 2.05, 2.1, 2.26, 2.3, 4.3))

        with patch("gesture_controller.time.monotonic", side_effect=lambda: next(times)):
            self.assertFalse(controller.update_tool_gesture("Copy")["triggered"])
            self.assertTrue(controller.update_tool_gesture("Copy")["triggered"])
            self.assertFalse(controller.update_tool_gesture("Copy")["triggered"])
            controller.update_tool_gesture(None)
            self.assertFalse(controller.update_tool_gesture(None)["active"])
            self.assertFalse(controller.update_tool_gesture("Copy")["triggered"])
            self.assertTrue(controller.update_tool_gesture("Copy")["triggered"])

    def test_brief_detection_dropout_does_not_restart_hold(self):
        controller = GestureController()
        times = iter((0.0, 1.8, 1.85, 1.9))

        with patch("gesture_controller.time.monotonic", side_effect=lambda: next(times)):
            controller.update_tool_gesture("Move")
            controller.update_tool_gesture(None)
            self.assertGreater(
                controller.update_tool_gesture("Move")["progress"],
                0.9
            )
            self.assertFalse(controller.update_tool_gesture("Move")["triggered"])


class AppGestureRoutingTests(unittest.TestCase):
    def make_app(self, pinch_states):
        app = CameraViewerApp.__new__(CameraViewerApp)
        app.hand_tracker = Mock()
        app.hand_tracker.update_pinch.side_effect = pinch_states
        app.hand_tracker.get_index_finger.return_value = None
        app.hand_tracker.cancel_pinch.return_value = {
            "pinching": False,
            "pressed": False,
            "clicked": False,
            "released": False,
            "dragging": False,
            "drag_offset": (0, 0),
            "cancelled": True
        }
        app.hand_mouse = Mock()
        app.hand_mouse.is_mouse_down = False
        app.hand_mouse.current_x = 200
        app.hand_mouse.current_y = 150
        app.workspace = Mock()
        app.workspace.assets.contains_asset_at_screen.return_value = False
        app.pinch_asset_drag_allowed = False
        app.hand_control_paused = False
        app.gesture_controller = GestureController()
        app.gesture_controller.detect_tool_gesture = Mock(
            return_value=None
        )
        app.editor = Mock()
        app.set_status = Mock()
        return app, SimpleNamespace(shape=(480, 640, 3))

    def test_non_asset_pinch_clicks_immediately_once(self):
        app, frame = self.make_app((
            {
                "pinching": True,
                "pressed": True,
                "clicked": False,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            },
            {
                "pinching": True,
                "pressed": False,
                "clicked": True,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            }
        ))

        with patch("gesture_controller.time.monotonic", side_effect=(1.0, 3.0)):
            app._process_hand_controls(frame, {})
            app._process_hand_controls(frame, {})

        app.hand_mouse.click.assert_called_once()
        app.hand_mouse.tap.assert_not_called()
        app.hand_tracker.cancel_pinch.assert_not_called()
        app.editor.select_tool.assert_not_called()

    def test_short_pinch_release_does_not_click_twice(self):
        app, frame = self.make_app((
            {
                "pinching": True,
                "pressed": True,
                "clicked": False,
                "tap": False,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            },
            {
                "pinching": False,
                "pressed": False,
                "clicked": False,
                "tap": True,
                "released": True,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            }
        ))

        app._process_hand_controls(frame, {})
        app._process_hand_controls(frame, {})

        app.hand_mouse.click.assert_called_once()
        app.hand_mouse.tap.assert_not_called()

    def test_ok_sign_select_activates_after_two_seconds_without_clicking(self):
        app, frame = self.make_app((
            {
                "pinching": True,
                "pressed": True,
                "clicked": False,
                "tap": False,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            },
            {
                "pinching": True,
                "pressed": False,
                "clicked": True,
                "tap": False,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            }
        ))
        app.hand_tracker.cancel_pinch.return_value = {
            "pinching": False,
            "pressed": False,
            "clicked": False,
            "released": True,
            "dragging": False,
            "drag_offset": (0, 0),
            "cancelled": True
        }
        app.gesture_controller.detect_tool_gesture.return_value = "Select"

        with patch("gesture_controller.time.monotonic", side_effect=(1.0, 3.0)):
            app._process_hand_controls(frame, {})
            app._process_hand_controls(frame, {})

        app.editor.select_tool.assert_called_once_with("Select")
        app.hand_tracker.cancel_pinch.assert_called_once()
        app.hand_tracker.update_pinch.assert_called()
        app.hand_mouse.click.assert_called_once()

    def test_drag_takes_precedence_over_select_gesture(self):
        app, frame = self.make_app(({
            "pinching": True,
            "pressed": False,
            "clicked": False,
            "released": False,
            "dragging": True,
            "drag_offset": (20, 0),
            "cancelled": False
        },))
        app.pinch_asset_drag_allowed = True

        app._process_hand_controls(frame, {})

        app.hand_mouse.mouse_down.assert_called_once()
        app.hand_mouse.move_drag.assert_called_once_with(20, 0, 640, 480)
        app.editor.select_tool.assert_not_called()

    def test_pinch_drag_is_only_started_from_an_asset_thumbnail(self):
        app, frame = self.make_app((
            {
                "pinching": True,
                "pressed": True,
                "clicked": False,
                "tap": False,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            },
            {
                "pinching": True,
                "pressed": False,
                "clicked": False,
                "tap": False,
                "released": False,
                "dragging": True,
                "drag_offset": (20, 0),
                "cancelled": False
            }
        ))
        app.workspace.assets.contains_asset_at_screen.return_value = True
        app.hand_mouse.mouse_down.side_effect = lambda: setattr(
            app.hand_mouse,
            "is_mouse_down",
            True
        )

        app._process_hand_controls(frame, {})
        app._process_hand_controls(frame, {})

        app.workspace.assets.contains_asset_at_screen.assert_called_once_with(
            200,
            150
        )
        app.hand_mouse.mouse_down.assert_called_once()
        app.hand_mouse.move_drag.assert_called_once_with(20, 0, 640, 480)

    def test_pinch_drag_is_blocked_when_started_outside_asset_thumbnail(self):
        app, frame = self.make_app((
            {
                "pinching": True,
                "pressed": True,
                "clicked": False,
                "tap": False,
                "released": False,
                "dragging": False,
                "drag_offset": (0, 0),
                "cancelled": False
            },
            {
                "pinching": True,
                "pressed": False,
                "clicked": False,
                "tap": False,
                "released": False,
                "dragging": True,
                "drag_offset": (20, 0),
                "cancelled": False
            }
        ))

        app._process_hand_controls(frame, {})
        app._process_hand_controls(frame, {})

        app.workspace.assets.contains_asset_at_screen.assert_called_once()
        app.hand_mouse.mouse_down.assert_not_called()
        app.hand_mouse.move_drag.assert_not_called()

    def test_nonselect_tool_gesture_cannot_generate_a_click(self):
        app, frame = self.make_app(({
            "pinching": False,
            "pressed": False,
            "clicked": False,
            "released": True,
            "dragging": False,
            "drag_offset": (0, 0),
            "cancelled": True
        },))
        app.gesture_controller.detect_tool_gesture.return_value = "Copy"

        app._process_hand_controls(frame, {})

        app.hand_tracker.cancel_pinch.assert_not_called()
        app.hand_tracker.update_pinch.assert_called_once()
        app.hand_mouse.click.assert_not_called()

    def test_cursor_keeps_tracking_during_tool_gesture_pose(self):
        app, frame = self.make_app(({
            "pinching": False,
            "pressed": False,
            "clicked": False,
            "released": False,
            "dragging": False,
            "drag_offset": (0, 0),
            "cancelled": True
        },))
        app.gesture_controller.detect_tool_gesture.return_value = "Copy"
        app.hand_tracker.get_index_finger.return_value = (400, 200)

        app._process_hand_controls(frame, {})

        app.hand_mouse.move.assert_called_once_with(400, 200, 640, 480)

    def test_paused_hand_control_skips_gesture_and_pinch_processing(self):
        app, frame = self.make_app(())
        app.hand_control_paused = True
        app.hand_mouse.is_mouse_down = True

        app._process_hand_controls(frame, {})

        app.gesture_controller.detect_tool_gesture.assert_not_called()
        app.hand_tracker.update_pinch.assert_not_called()
        app.hand_mouse.mouse_up.assert_called_once()
        self.assertFalse(app.pinch_asset_drag_allowed)

    def test_pause_and_resume_reset_hand_control_state(self):
        app, _ = self.make_app(())
        app.workspace.timeline.set_hand_control_paused = Mock()
        app.gesture_controller.pending_tool = "Copy"
        app.gesture_controller.tool_start_time = 1.0
        app.gesture_controller.active_tool = "Copy"

        app.set_hand_control_paused(True)

        app.hand_mouse.disable.assert_called_once()
        app.hand_tracker.cancel_pinch.assert_called_once()
        app.workspace.timeline.set_hand_control_paused.assert_called_once_with(
            True
        )
        self.assertIsNone(app.gesture_controller.pending_tool)
        self.assertIsNone(app.gesture_controller.tool_start_time)
        self.assertIsNone(app.gesture_controller.active_tool)

        app.set_hand_control_paused(False)

        app.hand_mouse.enable.assert_called_once()
        self.assertEqual(
            app.workspace.timeline.set_hand_control_paused.call_args_list,
            [unittest.mock.call(True), unittest.mock.call(False)]
        )


class StatusNotificationTests(unittest.TestCase):
    def test_gesture_selection_and_copy_statuses_show_notifications(self):
        app = CameraViewerApp.__new__(CameraViewerApp)
        app.status_label = Mock()
        app.show_notification = Mock()

        app.set_status("Gesture selected Copy tool")
        app.set_status("clip.mp4 has been copied")
        app.set_status("Hand control resumed")

        self.assertEqual(
            app.status_label.configure.call_args_list,
            [
                unittest.mock.call(text="Status: Gesture selected Copy tool"),
                unittest.mock.call(text="Status: clip.mp4 has been copied"),
                unittest.mock.call(text="Status: Hand control resumed")
            ]
        )
        self.assertEqual(
            app.show_notification.call_args_list,
            [
                unittest.mock.call("Gesture selected Copy tool"),
                unittest.mock.call("clip.mp4 has been copied")
            ]
        )


class KeyboardClipboardTests(unittest.TestCase):
    def make_app(self):
        app = CameraViewerApp.__new__(CameraViewerApp)
        app.editor = Mock()
        app.set_status = Mock()
        app._is_text_entry_focused = Mock(return_value=False)
        return app

    def test_ctrl_c_copies_selection_without_duplicating(self):
        app = self.make_app()
        app.editor.copy_selected.return_value = object()

        result = app._copy_selected_from_keyboard(None)

        self.assertEqual(result, "break")
        app.editor.copy_selected.assert_called_once_with()
        app.set_status.assert_not_called()

    def test_ctrl_c_without_selection_prompts_user(self):
        app = self.make_app()
        app.editor.copy_selected.return_value = None

        result = app._copy_selected_from_keyboard(None)

        self.assertEqual(result, "break")
        app.set_status.assert_called_once_with("Select a clip to copy")

    def test_ctrl_v_pastes_at_last_timeline_mouse_position(self):
        app = self.make_app()
        app.workspace = SimpleNamespace(
            timeline=SimpleNamespace(
                last_mouse_timeline_position=(210.0, 60.0)
            )
        )

        result = app._paste_from_keyboard(None)

        self.assertEqual(result, "break")
        app.editor.paste_at_position.assert_called_once_with(210.0, 60.0)


class PinchTests(unittest.TestCase):
    def make_tracker(self, distances, positions, palm_positions=None):
        tracker = HandTracker.__new__(HandTracker)
        tracker.pinch_threshold = 35
        tracker.click_debounce = 0.06
        tracker.click_hold_duration = 2.0
        tracker.pinch_release_time = 0.0
        tracker.pinch_missing_since = None
        tracker.pinch_tracking_grace = 0.10
        tracker.pinch_release_threshold_ratio = 0.42
        tracker.pinch_engage_threshold_ratio = 0.30
        tracker.drag_movement_threshold = 12.0
        tracker.pinch_start_position = None
        tracker.pinch_last_position = None
        tracker.pinch_start_time = None
        tracker.pinch_dragging = False
        tracker.pinch_drag_frames = 0
        tracker.pinch_click_fired = False
        tracker.pinch_release_frames = 0
        tracker.pinch_release_confirm_frames = 2
        tracker.pinch_suppressed_until = 0.0
        tracker.pinch_cancel_cooldown = 0.22
        tracker.is_pinching = False
        tracker.get_distance = Mock(side_effect=[
            value
            for distance in distances
            for value in distance
        ])
        tracker.get_index_finger = Mock(side_effect=positions)
        tracker.get_palm_center = Mock(
            side_effect=palm_positions if palm_positions is not None else positions
        )
        return tracker

    def test_nearby_pinch_noise_does_not_repeat_click_or_release(self):
        tracker = self.make_tracker(
            ((20, 100), (25, 100), (None, None), (20, 100)),
            ((100, 100), (102, 101), None, (101, 100))
        )
        times = (1.0, 1.03, 1.06, 1.09)

        with patch("hand_tracker.time.monotonic", side_effect=times):
            states = [tracker.update_pinch(None) for _ in times]

        self.assertTrue(states[0]["pressed"])
        self.assertFalse(states[1]["pressed"])
        self.assertTrue(states[2]["pinching"])
        self.assertFalse(states[2]["released"])
        self.assertTrue(states[3]["pinching"])

    def test_single_open_frame_does_not_release_pinch(self):
        tracker = self.make_tracker(
            ((20, 100), (50, 100), (20, 100)),
            ((100, 100), (100, 100), (100, 100))
        )
        with patch("hand_tracker.time.monotonic", side_effect=(1.0, 1.03, 1.06)):
            start = tracker.update_pinch(None)
            noisy_open = tracker.update_pinch(None)
            closed_again = tracker.update_pinch(None)

        self.assertTrue(start["pressed"])
        self.assertTrue(noisy_open["pinching"])
        self.assertFalse(noisy_open["released"])
        self.assertTrue(closed_again["pinching"])
        self.assertFalse(closed_again["released"])

    def test_pinch_threshold_is_normalized_to_palm_scale(self):
        tracker = self.make_tracker(
            ((20, 100), (40, 200)),
            ((100, 100), (100, 100))
        )
        with patch("hand_tracker.time.monotonic", side_effect=(1.0, 1.1)):
            near_camera = tracker.update_pinch(None)
            farther_camera = tracker.update_pinch(None)

        self.assertTrue(near_camera["pressed"])
        self.assertTrue(farther_camera["pinching"])
        self.assertFalse(farther_camera["pressed"])

    def test_tracking_loss_cancels_click_after_grace_period(self):
        tracker = self.make_tracker(
            ((20, 100), (None, None), (None, None)),
            ((100, 100), None, None)
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.05, 1.16)
        ):
            pressed = tracker.update_pinch(None)
            grace = tracker.update_pinch(None)
            lost = tracker.update_pinch(None)

        self.assertTrue(pressed["pressed"])
        self.assertTrue(grace["pinching"])
        self.assertTrue(lost["released"])
        self.assertTrue(lost["cancelled"])

    def test_drag_keeps_last_offset_during_brief_tracking_dropout(self):
        tracker = self.make_tracker(
            ((20, 100), (20, 100), (20, 100), (None, None)),
            ((100, 100), (130, 100), (130, 100), None)
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.1, 1.2, 1.23)
        ):
            tracker.update_pinch(None)
            tracker.update_pinch(None)
            dragging = tracker.update_pinch(None)
            dropout = tracker.update_pinch(None)

        self.assertTrue(dragging["dragging"])
        self.assertTrue(dropout["dragging"])
        self.assertEqual(dropout["drag_offset"], (30, 0))

    def test_drag_requires_sustained_movement_not_just_holding_pinch(self):
        tracker = self.make_tracker(
            (
                (20, 100), (20, 100), (20, 100),
                (20, 100), (50, 100), (50, 100)
            ),
            (
                (100, 100), (101, 100), (130, 100),
                (130, 100), (130, 100), (130, 100)
            )
        )
        times = (1.0, 1.1, 1.2, 1.25, 1.3, 1.35)

        with patch("hand_tracker.time.monotonic", side_effect=times):
            states = [tracker.update_pinch(None) for _ in times]

        self.assertFalse(states[1]["dragging"])
        self.assertFalse(states[2]["dragging"])
        self.assertTrue(states[3]["dragging"])
        self.assertEqual(states[3]["drag_offset"], (30, 0))
        self.assertFalse(states[4]["released"])
        self.assertTrue(states[5]["released"])
        self.assertFalse(states[5]["tap"])

    def test_finger_curl_during_stationary_pinch_does_not_start_drag(self):
        tracker = self.make_tracker(
            ((20, 100), (20, 100), (20, 100), (20, 100)),
            ((100, 100), (130, 100), (130, 100), (130, 100)),
            ((50, 50), (50, 50), (50, 50), (50, 50))
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.1, 1.2, 3.0)
        ):
            states = [tracker.update_pinch(None) for _ in range(4)]

        self.assertFalse(any(state["dragging"] for state in states))
        self.assertTrue(states[-1]["clicked"])

    def test_palm_translation_while_pinched_starts_drag(self):
        tracker = self.make_tracker(
            ((20, 100), (20, 100), (20, 100)),
            ((100, 100), (100, 100), (100, 100)),
            ((50, 50), (80, 50), (80, 50))
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.1, 1.2)
        ):
            states = [tracker.update_pinch(None) for _ in range(3)]

        self.assertTrue(states[-1]["dragging"])
        self.assertEqual(states[-1]["drag_offset"], (30, 0))

    def test_stationary_pinch_clicks_once_after_two_seconds(self):
        tracker = self.make_tracker(
            ((20, 100), (20, 100), (20, 100), (20, 100), (20, 100)),
            ((100, 100), (100, 100), (100, 100), (100, 100), (100, 100))
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 2.9, 3.0, 3.1, 3.2)
        ):
            states = [tracker.update_pinch(None) for _ in range(5)]

        self.assertTrue(states[0]["pressed"])
        self.assertFalse(states[1]["clicked"])
        self.assertTrue(states[2]["clicked"])
        self.assertFalse(states[3]["clicked"])
        self.assertTrue(all(not state["dragging"] for state in states))

    def test_release_before_two_seconds_does_not_click(self):
        tracker = self.make_tracker(
            ((20, 100), (50, 100), (50, 100)),
            ((100, 100), (100, 100), (100, 100))
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.2, 1.3)
        ):
            start = tracker.update_pinch(None)
            tracker.update_pinch(None)
            release = tracker.update_pinch(None)

        self.assertTrue(start["pressed"])
        self.assertTrue(release["released"])
        self.assertFalse(release["clicked"])
        self.assertTrue(release["tap"])

    def test_drag_never_turns_into_a_long_hold_click(self):
        tracker = self.make_tracker(
            (
                (20, 100), (20, 100), (20, 100),
                (20, 100), (20, 100)
            ),
            (
                (100, 100), (130, 100), (130, 100),
                (130, 100), (130, 100)
            )
        )
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.1, 1.2, 3.1, 3.2)
        ):
            states = [tracker.update_pinch(None) for _ in range(5)]

        self.assertTrue(states[2]["dragging"])
        self.assertTrue(states[3]["dragging"])
        self.assertFalse(any(state["clicked"] for state in states))

    def test_pinch_debounce_allows_typical_double_tap_interval(self):
        tracker = self.make_tracker(
            ((20, 100), (50, 100), (50, 100), (20, 100)),
            ((100, 100), (100, 100), (100, 100), (100, 100))
        )
        tracker.click_debounce = 0.06
        with patch(
            "hand_tracker.time.monotonic",
            side_effect=(1.0, 1.05, 1.08, 1.18)
        ):
            first = tracker.update_pinch(None)
            tracker.update_pinch(None)
            tracker.update_pinch(None)
            second = tracker.update_pinch(None)

        self.assertTrue(first["pressed"])
        self.assertTrue(second["pressed"])

    def test_legacy_detect_pinch_returns_only_press_edge(self):
        tracker = self.make_tracker(
            ((20, 100), (20, 100)),
            ((100, 100), (100, 100))
        )
        with patch("hand_tracker.time.monotonic", side_effect=(1.0, 1.1)):
            self.assertTrue(tracker.detect_pinch(None))
            self.assertFalse(tracker.detect_pinch(None))

    def test_tool_gesture_cancels_overlapping_click_pinch(self):
        tracker = self.make_tracker(
            ((20, 100), (20, 100)),
            ((100, 100), (100, 100))
        )
        with patch("hand_tracker.time.monotonic", side_effect=(1.0, 1.01, 1.1)):
            tracker.update_pinch(None)
            cancelled = tracker.cancel_pinch()
            suppressed = tracker.update_pinch(None)

        self.assertTrue(cancelled["released"])
        self.assertTrue(cancelled["cancelled"])
        self.assertTrue(suppressed["pinching"])
        self.assertFalse(suppressed["pressed"])
        self.assertFalse(tracker.is_pinching)


class TimelineToolTests(unittest.TestCase):
    def make_timeline(self, layer, clip, current_time=0.0):
        timeline = TimelinePanel.__new__(TimelinePanel)
        timeline.layers = [layer]
        timeline.selected_layer = layer
        timeline.selected_clip = clip
        timeline.selected_clip_layer = layer
        timeline.current_time = current_time
        timeline.timeline_duration = 60.0
        timeline.pixels_per_second = 70.0
        timeline.clipboard_clip = None
        timeline.last_mouse_timeline_position = None
        timeline.on_layer_selected = None
        timeline.on_clip_added = None
        timeline.on_status = Mock()
        timeline.redraw = Mock()
        timeline._notify_timeline_changed = Mock()
        return timeline

    def test_asset_drop_is_accepted_only_inside_a_timeline_track(self):
        layer = Layer("Video")
        timeline = TimelinePanel.__new__(TimelinePanel)
        timeline.canvas = Mock()
        timeline.canvas.winfo_rootx.return_value = 100
        timeline.canvas.winfo_rooty.return_value = 200
        timeline.canvas.winfo_width.return_value = 400
        timeline.canvas.winfo_height.return_value = 300
        timeline.canvas.canvasx.side_effect = lambda value: value
        timeline.canvas.canvasy.side_effect = lambda value: value
        timeline.layers = [layer]
        timeline.selected_layer = layer
        timeline.selected_clip = None
        timeline.selected_clip_layer = None
        timeline.RULER_HEIGHT = 32
        timeline.TRACK_HEIGHT = 64
        timeline.pixels_per_second = 70
        timeline.timeline_duration = 60.0
        timeline.redraw = Mock()
        timeline._notify_timeline_changed = Mock()
        timeline.on_clip_added = Mock()
        timeline.on_layer_selected = None

        self.assertFalse(
            timeline.drop_asset_at_screen("image.png", 550, 250)
        )
        self.assertEqual(len(layer.clips), 0)
        self.assertTrue(
            timeline.drop_asset_at_screen("image.png", 150, 250)
        )
        self.assertEqual(len(layer.clips), 1)

    def test_asset_hit_testing_uses_thumbnail_screen_bounds(self):
        button = Mock()
        button.winfo_exists.return_value = 1
        button.winfo_rootx.return_value = 100
        button.winfo_rooty.return_value = 200
        button.winfo_width.return_value = 80
        button.winfo_height.return_value = 60
        browser = SimpleNamespace(asset_buttons=[button])

        self.assertTrue(
            AssetBrowser.contains_asset_at_screen(browser, 120, 220)
        )
        self.assertFalse(
            AssetBrowser.contains_asset_at_screen(browser, 180, 260)
        )

    def test_copy_duplicates_clip_after_source(self):
        layer = Layer("Video")
        clip = MediaClip(
            "clip.png",
            start_time=2.0,
            duration=1.5,
            source_start_time=0.4
        )
        layer.add_clip(clip)
        timeline = self.make_timeline(layer, clip)

        duplicate = timeline.duplicate_clip(clip)

        self.assertIsNot(duplicate, clip)
        self.assertEqual(duplicate.start_time, clip.end_time)
        self.assertEqual(duplicate.duration, clip.duration)
        self.assertEqual(duplicate.source_start_time, 0.4)
        self.assertIs(timeline.selected_clip, duplicate)

    def test_cut_splits_timeline_and_source_time(self):
        layer = Layer("Video")
        clip = MediaClip(
            "clip.png",
            start_time=10.0,
            duration=4.0,
            source_start_time=1.5
        )
        layer.add_clip(clip)
        timeline = self.make_timeline(layer, clip, current_time=12.25)

        right_clip = timeline.split_clip_at_playhead()

        self.assertEqual(clip.duration, 2.25)
        self.assertEqual(right_clip.start_time, 12.25)
        self.assertEqual(right_clip.duration, 1.75)
        self.assertEqual(right_clip.source_start_time, 3.75)
        self.assertEqual(right_clip.local_time(12.25), 3.75)
        self.assertIs(timeline.selected_clip, right_clip)

    def test_cut_rejects_split_near_clip_edge(self):
        layer = Layer("Video")
        clip = MediaClip("clip.png", start_time=1.0, duration=2.0)
        layer.add_clip(clip)
        timeline = self.make_timeline(layer, clip, current_time=1.02)

        self.assertFalse(timeline.split_clip_at_playhead())
        self.assertEqual(len(layer.clips), 1)

    def test_copy_tool_click_copies_clip_and_reports_filename(self):
        layer = Layer("Video")
        clip = MediaClip("image.png", start_time=1.0, duration=2.0)
        layer.add_clip(clip)
        timeline = self.make_timeline(layer, clip)
        timeline.current_tool = "Copy"
        timeline.canvas = Mock()
        timeline.canvas.canvasx.side_effect = lambda value: value
        timeline.canvas.canvasy.side_effect = lambda value: value
        timeline._find_clip_resize_edge = Mock(return_value=(None, None, None))
        timeline._find_clip_at_position = Mock(return_value=(layer, clip))

        timeline._mouse_pressed(SimpleNamespace(x=30, y=50))

        self.assertEqual(len(layer.clips), 1)
        self.assertIsNot(timeline.clipboard_clip, clip)
        self.assertEqual(timeline.clipboard_clip.file_path, "image.png")
        timeline.on_status.assert_called_once_with(
            "image.png has been copied"
        )

    def test_cut_tool_splits_at_clicked_time_not_playhead(self):
        layer = Layer("Video")
        clip = MediaClip("clip.png", start_time=1.0, duration=4.0)
        layer.add_clip(clip)
        timeline = self.make_timeline(layer, clip, current_time=1.5)
        timeline.current_tool = "Cut"
        timeline.pixels_per_second = 10
        timeline.canvas = Mock()
        timeline.canvas.canvasx.side_effect = lambda value: value
        timeline.canvas.canvasy.side_effect = lambda value: value
        timeline._find_clip_resize_edge = Mock(return_value=(None, None, None))
        timeline._find_clip_at_position = Mock(return_value=(layer, clip))

        timeline._mouse_pressed(SimpleNamespace(x=25, y=50))

        self.assertEqual(clip.duration, 1.5)
        self.assertEqual(layer.clips[1].start_time, 2.5)
        self.assertEqual(layer.clips[1].duration, 2.5)

    def test_paste_tool_places_copied_clip_at_mouse_timeline_position(self):
        layer = Layer("Video")
        source = MediaClip(
            "image.png",
            start_time=1.0,
            duration=2.0,
            source_start_time=0.5
        )
        layer.add_clip(source)
        timeline = self.make_timeline(layer, source)
        timeline.current_tool = "Paste"
        timeline.clipboard_clip = source
        timeline.canvas = Mock()
        timeline.canvas.canvasx.side_effect = lambda value: value
        timeline.canvas.canvasy.side_effect = lambda value: value

        timeline._mouse_pressed(SimpleNamespace(x=210, y=50))

        self.assertEqual(len(layer.clips), 2)
        pasted = layer.clips[1]
        self.assertEqual(pasted.start_time, 3.0)
        self.assertEqual(pasted.duration, source.duration)
        self.assertEqual(pasted.source_start_time, 0.5)
        self.assertIs(timeline.selected_clip, pasted)
        timeline.on_status.assert_called_once_with("image.png pasted")

    def test_paste_without_clipboard_reports_why_it_did_not_happen(self):
        layer = Layer("Video")
        timeline = self.make_timeline(layer, None)

        self.assertIsNone(timeline.paste_clip_at_position(140, 50))

        timeline.on_status.assert_called_once_with(
            "Nothing has been copied yet"
        )

    def test_copy_then_paste_tool_completes_clipboard_workflow(self):
        layer = Layer("Video")
        source = MediaClip("image.png", start_time=0.5, duration=3.0)
        layer.add_clip(source)
        timeline = self.make_timeline(layer, source)
        timeline.current_tool = "Copy"
        timeline.canvas = Mock()
        timeline.canvas.canvasx.side_effect = lambda value: value
        timeline.canvas.canvasy.side_effect = lambda value: value
        timeline._find_clip_resize_edge = Mock(return_value=(None, None, None))
        timeline._find_clip_at_position = Mock(return_value=(layer, source))

        timeline._mouse_pressed(SimpleNamespace(x=70, y=50))
        timeline.current_tool = "Paste"
        timeline._mouse_pressed(SimpleNamespace(x=280, y=50))

        self.assertEqual(len(layer.clips), 2)
        self.assertEqual(layer.clips[1].file_path, "image.png")
        self.assertEqual(layer.clips[1].start_time, 4.0)
        self.assertEqual(
            timeline.on_status.call_args_list,
            [
                unittest.mock.call("image.png has been copied"),
                unittest.mock.call("image.png pasted")
            ]
        )

    def test_resize_edge_detection_supports_video_clips(self):
        clip = SimpleNamespace(
            media_type="video",
            start_time=2.0,
            duration=3.0,
            end_time=5.0
        )
        timeline = TimelinePanel.__new__(TimelinePanel)
        timeline.pixels_per_second = 10
        timeline.clip_resize_grab_width = 6
        timeline._find_clip_at_position = Mock(
            return_value=(object(), clip)
        )

        layer, found_clip, edge = timeline._find_clip_resize_edge(20, 50)

        self.assertIs(layer, timeline._find_clip_at_position.return_value[0])
        self.assertIs(found_clip, clip)
        self.assertEqual(edge, "left")


class HandMouseTests(unittest.TestCase):
    def test_calibration_bounds_map_hand_range_and_reject_tiny_area(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.time.monotonic", return_value=100.0):
            mouse = HandMouseController()

            self.assertTrue(
                mouse.set_calibration_bounds(
                    (20, 10),
                    (180, 90),
                    200,
                    100
                )
            )
            mouse.move(100, 50, 200, 100)
            self.assertAlmostEqual(mouse.filter_raw_x, 499.5)
            self.assertAlmostEqual(mouse.filter_raw_y, 399.5)

            self.assertFalse(
                mouse.set_calibration_bounds(
                    (20, 10),
                    (40, 20),
                    200,
                    100
                )
            )
            self.assertEqual(
                mouse.calibration_bounds,
                (0.1, 0.1, 0.9, 0.9)
            )

    def test_cursor_sensitivity_changes_calibrated_reach(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.time.monotonic", return_value=100.0):
            mouse = HandMouseController()
            mouse.set_calibration_bounds(
                (20, 10),
                (180, 90),
                200,
                100
            )
            mouse.set_sensitivity(2.0)
            mouse.move(60, 30, 200, 100)

        self.assertEqual(mouse.filter_raw_x, 0.0)
        self.assertEqual(mouse.filter_raw_y, 0.0)

    def test_drag_and_tap_use_distinct_mouse_actions(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.mouseDown") as mouse_down, \
                patch("hand_tracker.pyautogui.mouseUp") as mouse_up, \
                patch("hand_tracker.pyautogui.click") as click:
            mouse = HandMouseController(smoothing=0.5)
            mouse.mouse_down()
            mouse.mouse_up()
            mouse.click()

        mouse_down.assert_called_once_with(500, 400, button="left")
        mouse_up.assert_called_once_with(500, 400, button="left")
        click.assert_called_once_with(500, 400)

    def test_short_pinch_clicks_immediately(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.click") as click:
            mouse = HandMouseController(smoothing=0.5)
            mouse.tap()

        click.assert_called_once_with(500, 400)

    def test_two_quick_pinches_send_two_native_clicks_for_explorer(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.click") as click, \
                patch("hand_tracker.pyautogui.doubleClick") as double_click:
            mouse = HandMouseController(smoothing=0.5)
            mouse.tap()
            mouse.tap()

        self.assertEqual(click.call_count, 2)
        self.assertEqual(
            click.call_args_list,
            [
                unittest.mock.call(500, 400),
                unittest.mock.call(500, 400)
            ]
        )
        double_click.assert_not_called()

    def test_disabling_controller_releases_held_mouse_button(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.mouseDown") as mouse_down, \
                patch("hand_tracker.pyautogui.mouseUp") as mouse_up:
            mouse = HandMouseController()
            mouse.mouse_down()
            mouse.disable()

        mouse_down.assert_called_once()
        mouse_up.assert_called_once()
        self.assertFalse(mouse.is_mouse_down)

    def test_drag_relative_motion_starts_from_click_location(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.mouseDown"), \
                patch("hand_tracker.pyautogui.moveTo") as move_to, \
                patch("hand_tracker.time.monotonic", return_value=100.1):
            mouse = HandMouseController()
            mouse.current_x = 500
            mouse.current_y = 400
            mouse.mouse_down()
            mouse.move_drag(20, -10, 640, 480)

        x, y = move_to.call_args.args[:2]
        self.assertGreater(x, 500)
        self.assertLess(y, 400)
        self.assertTrue(mouse.is_mouse_down)

    def test_tracking_small_noise_does_not_make_large_cursor_jumps(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)
        timestamps = [1000 + index / 60 for index in range(10)]

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.moveTo"), \
                patch("hand_tracker.time.monotonic", side_effect=timestamps):
            mouse = HandMouseController()
            mouse.move_interval = 0
            mouse.deadzone = 0
            mouse.current_x = 500
            mouse.current_y = 400
            mouse.filter_raw_x = 500
            mouse.filter_raw_y = 400
            for finger_x in (500, 501, 499, 501, 500, 499, 500, 501, 500, 500):
                mouse.move(finger_x, 400, 1000, 800)

        self.assertLess(abs(mouse.current_x - 500), 10)
        self.assertLess(abs(mouse.current_y - 400), 10)

    def test_fast_sweeps_get_more_response_than_small_adjustments(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.moveTo"), \
                patch("hand_tracker.time.monotonic", return_value=1000 + 1 / 60):
            small = HandMouseController()
            small.move_interval = 0
            small.last_move_time = 1000
            small.move(516, 400, 1000, 800)
            small_response = (small.current_x - 500) / 20

            fast = HandMouseController()
            fast.move_interval = 0
            fast.last_move_time = 1000
            fast.move(740, 400, 1000, 800)
            fast_response = (fast.current_x - 500) / 300

        self.assertGreater(fast_response, small_response)

    def test_adaptive_filter_reduces_stationary_pointer_jitter(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)
        noise = (2, -2, 1, -1, 2, -2, 1, -1) * 4
        timestamps = [1000 + index / 60 for index in range(len(noise))]

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.moveTo"), \
                patch("hand_tracker.time.monotonic", side_effect=timestamps):
            mouse = HandMouseController()
            mouse.move_interval = 0
            mouse.current_x = mouse.filter_raw_x = 500
            mouse.current_y = mouse.filter_raw_y = 400
            outputs = []
            for offset in noise:
                mouse.move(500 + offset, 400, 1000, 800)
                outputs.append(mouse.current_x)

        input_rms = math.sqrt(
            sum((offset * 999 / 800) ** 2 for offset in noise)
            / len(noise)
        )
        output_rms = math.sqrt(
            sum((position - 500) ** 2 for position in outputs)
            / len(outputs)
        )
        self.assertLess(output_rms, input_rms * 0.5)
    def test_cursor_uses_smoothed_screen_coordinates(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.moveTo") as move_to, \
                patch("hand_tracker.time.monotonic", return_value=1000.0):
            mouse = HandMouseController(smoothing=0.5)
            mouse.move_interval = 0
            mouse.deadzone = 0
            mouse.current_x = 500
            mouse.current_y = 400

            mouse.move(80, 50, 100, 100)

        call_args = move_to.call_args
        self.assertIsNotNone(call_args)
        self.assertGreaterEqual(call_args.args[0], 750)
        self.assertEqual(call_args.args[1], 399)
        self.assertEqual(call_args.kwargs["duration"], 0)

    def test_smoothing_is_consistent_across_frame_rates(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.moveTo"), \
                patch(
                    "hand_tracker.time.monotonic",
                    side_effect=(1000 + 2 / 60, 1000 + 1 / 60, 1000 + 2 / 60)
                ):
            at_30_fps = HandMouseController(smoothing=0.5)
            at_30_fps.move_interval = 0
            at_30_fps.deadzone = 0
            at_30_fps.current_x = at_60_fps_x = 500
            at_30_fps.current_y = at_60_fps_y = 400
            at_30_fps.last_move_time = 1000
            at_30_fps.move(80, 50, 100, 100)

            at_60_fps = HandMouseController(smoothing=0.5)
            at_60_fps.move_interval = 0
            at_60_fps.deadzone = 0
            at_60_fps.current_x = at_60_fps_x
            at_60_fps.current_y = at_60_fps_y
            at_60_fps.last_move_time = 1000
            at_60_fps.move(80, 50, 100, 100)
            at_60_fps.move(80, 50, 100, 100)

        self.assertAlmostEqual(
            at_30_fps.current_x,
            at_60_fps.current_x,
            delta=40
        )
        self.assertAlmostEqual(
            at_30_fps.current_y,
            at_60_fps.current_y,
            delta=40
        )


if __name__ == "__main__":
    unittest.main()
