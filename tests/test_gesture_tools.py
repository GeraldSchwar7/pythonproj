import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pyautogui

from gesture_controller import GestureController
from hand_tracker import HandMouseController, HandTracker
from layer import Layer
from media_clip import MediaClip
from timeline_panel import TimelinePanel


class GestureControllerTests(unittest.TestCase):
    def test_tool_requires_hold_and_rearms_after_release(self):
        controller = GestureController()
        times = iter((0.0, 0.7, 0.75, 0.8, 0.96, 1.0, 1.7))

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
        times = iter((0.0, 0.6, 0.65, 0.7))

        with patch("gesture_controller.time.monotonic", side_effect=lambda: next(times)):
            controller.update_tool_gesture("Move")
            controller.update_tool_gesture(None)
            self.assertGreater(
                controller.update_tool_gesture("Move")["progress"],
                0.9
            )
            self.assertTrue(controller.update_tool_gesture("Move")["triggered"])


class PinchTests(unittest.TestCase):
    def test_short_pinch_dropout_is_debounced(self):
        tracker = HandTracker.__new__(HandTracker)
        tracker.pinch_threshold = 35
        tracker.click_debounce = 0.25
        tracker.last_click_time = 0.0
        tracker.is_pinching = False
        tracker.pinch_start_time = None
        tracker.pinch_release_time = 0.0
        tracker.drag_threshold = 0.18
        tracker.drag_movement_threshold = 8.0
        tracker.pinch_start_position = None
        tracker.pinch_last_position = None
        tracker.pinch_dragging = False
        tracker.get_distance = Mock(side_effect=(10, 10, None, None, 10))
        tracker.get_index_finger = Mock(return_value=(100, 100))

        with patch("hand_tracker.time.monotonic", side_effect=(1.1, 1.11, 1.12, 1.13, 1.14)):
            self.assertTrue(tracker.detect_pinch(None))
            self.assertFalse(tracker.detect_pinch(None))
            self.assertFalse(tracker.detect_pinch(None))
            self.assertFalse(tracker.detect_pinch(None))
            self.assertFalse(tracker.detect_pinch(None))

    def test_pinch_hold_starts_and_releases_drag_once(self):
        tracker = HandTracker.__new__(HandTracker)
        tracker.pinch_threshold = 35
        tracker.click_debounce = 0.25
        tracker.last_click_time = 0.0
        tracker.is_pinching = False
        tracker.pinch_start_time = None
        tracker.pinch_release_time = 0.0
        tracker.drag_threshold = 0.18
        tracker.drag_movement_threshold = 8.0
        tracker.pinch_start_position = None
        tracker.pinch_last_position = None
        tracker.pinch_dragging = False
        tracker.get_distance = Mock(side_effect=(10, 10, 10, 50))
        tracker.get_index_finger = Mock(
            side_effect=((100, 100), (105, 100), (130, 100), (130, 100))
        )

        with patch("hand_tracker.time.monotonic", side_effect=(1.0, 1.1, 1.2, 1.3)):
            pressed = tracker.update_pinch(None)
            dragging = tracker.update_pinch(None)
            continued = tracker.update_pinch(None)
            released = tracker.update_pinch(None)

        self.assertTrue(pressed["pressed"])
        self.assertFalse(dragging["dragging"])
        self.assertTrue(continued["dragging"])
        self.assertTrue(released["released"])
        self.assertFalse(released["pinching"])


class TimelineToolTests(unittest.TestCase):
    def make_timeline(self, layer, clip, current_time=0.0):
        timeline = TimelinePanel.__new__(TimelinePanel)
        timeline.layers = [layer]
        timeline.selected_layer = layer
        timeline.selected_clip = clip
        timeline.selected_clip_layer = layer
        timeline.current_time = current_time
        timeline.timeline_duration = 60.0
        timeline.on_layer_selected = None
        timeline.redraw = Mock()
        timeline._notify_timeline_changed = Mock()
        return timeline

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

    def test_copy_tool_click_duplicates_the_clicked_clip(self):
        layer = Layer("Video")
        clip = MediaClip("clip.png", start_time=1.0, duration=2.0)
        layer.add_clip(clip)
        timeline = self.make_timeline(layer, clip)
        timeline.current_tool = "Copy"
        timeline.canvas = Mock()
        timeline.canvas.canvasx.side_effect = lambda value: value
        timeline.canvas.canvasy.side_effect = lambda value: value
        timeline._find_clip_resize_edge = Mock(return_value=(None, None, None))
        timeline._find_clip_at_position = Mock(return_value=(layer, clip))

        timeline._mouse_pressed(SimpleNamespace(x=30, y=50))

        self.assertEqual(len(layer.clips), 2)
        self.assertIs(timeline.selected_clip, layer.clips[1])

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

    def test_second_tap_emits_double_click(self):
        old_pause = pyautogui.PAUSE
        old_failsafe = pyautogui.FAILSAFE
        self.addCleanup(setattr, pyautogui, "PAUSE", old_pause)
        self.addCleanup(setattr, pyautogui, "FAILSAFE", old_failsafe)

        with patch("hand_tracker.pyautogui.size", return_value=(1000, 800)), \
                patch("hand_tracker.pyautogui.click") as click, \
                patch("hand_tracker.pyautogui.doubleClick") as double_click, \
                patch("hand_tracker.time.monotonic", side_effect=(100.0, 100.2)):
            mouse = HandMouseController(smoothing=0.5)
            mouse.click()
            mouse.click()

        click.assert_called_once_with(500, 400)
        double_click.assert_called_once_with(500, 400)
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
            delta=20
        )
        self.assertAlmostEqual(
            at_30_fps.current_y,
            at_60_fps.current_y,
            delta=5
        )


if __name__ == "__main__":
    unittest.main()
