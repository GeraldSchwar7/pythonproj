import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import cv2
import numpy as np

from scene_separation import (
    SceneSeparationWindow,
    _draw_mask_contours,
    compose_layer_masks,
    copy_mask_contours,
    extract_mask_contours,
    insert_contour_point,
    is_valid_contour_edit,
    normalize_mask_edges,
    propagate_layer_mask_change,
    rasterize_mask_contours,
    remove_redundant_contour_points,
)


class MaskContourTests(unittest.TestCase):
    def test_normalization_straightens_and_reduces_edge_points(self):
        mask = np.zeros((64, 64), dtype=np.float32)
        for y in range(8, 56):
            left = 8 + y % 2
            right = 48 + y % 2
            mask[y, left:right] = 1.0
        mask[30:34, 48:51] = 1.0
        raw_contours, _ = cv2.findContours(
            (mask > 0).astype(np.uint8),
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_NONE,
        )
        normalized = normalize_mask_edges(mask)
        controls = extract_mask_contours(normalized)
        normalized_contours, _ = cv2.findContours(
            normalized.astype(np.uint8),
            cv2.RETR_TREE,
            cv2.CHAIN_APPROX_NONE,
        )

        self.assertEqual(normalized.shape, mask.shape)
        self.assertTrue(np.all((normalized == 0) | (normalized == 1)))
        self.assertLess(
            cv2.arcLength(normalized_contours[0], True),
            cv2.arcLength(raw_contours[0], True),
        )
        self.assertLess(
            sum(len(points) for points, _ in controls),
            len(raw_contours[0]),
        )
        self.assertTrue(
            all(len(points) <= 32 for points, _ in controls)
        )
        self.assertTrue(any(points[:, 0].max() >= 50 for points, _ in controls))

    def test_new_control_point_can_be_inserted_on_a_mask_edge(self):
        mask = np.zeros((64, 64), dtype=np.float32)
        mask[10:50, 10:50] = 1.0
        contours = extract_mask_contours(mask)

        updated, insertion = insert_contour_point(
            contours,
            30.0,
            10.0,
            max_distance=2.0,
        )

        self.assertIsNotNone(insertion)
        contour_index, segment_index, fraction, insertion_index = insertion
        self.assertEqual(
            len(updated[contour_index][0]),
            len(contours[contour_index][0]) + 1,
        )
        np.testing.assert_array_equal(
            rasterize_mask_contours(mask.shape, updated),
            mask,
        )

        source_points, depth = contours[contour_index]
        source_point = (
            source_points[segment_index]
            + fraction
            * (
                source_points[(segment_index + 1) % len(source_points)]
                - source_points[segment_index]
            )
        )
        with_inserted_source = np.insert(
            source_points,
            insertion_index,
            source_point,
            axis=0,
        )
        self.assertEqual(len(with_inserted_source), len(updated[contour_index][0]))
        self.assertEqual(depth, updated[contour_index][1])

    def test_double_click_adds_corresponding_source_and_target_nodes(self):
        mask = np.zeros((64, 64), dtype=np.float32)
        mask[10:50, 10:50] = 1.0
        contours = extract_mask_contours(mask)
        window = SceneSeparationWindow.__new__(SceneSeparationWindow)
        window.mesh_editing = True
        window._preview_bounds = (0, 0, 64, 64, 64, 64)
        window.preview_layer = 0
        window.mask_source_contours = [copy_mask_contours(contours)]
        window.mask_target_contours = [copy_mask_contours(contours)]
        window._mesh_edit_changed_indices = set()
        window.processing_status = Mock()
        window._redraw_preview = Mock()

        window._insert_mask_node(SimpleNamespace(x=30, y=10))

        source_points = window.mask_source_contours[0][0][0]
        target_points = window.mask_target_contours[0][0][0]
        self.assertEqual(len(source_points), len(target_points))
        self.assertEqual(len(source_points), len(contours[0][0]) + 1)
        np.testing.assert_array_equal(source_points, target_points)

    def test_right_click_deletes_a_node_and_updates_the_mask(self):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        mask = np.zeros((64, 64), dtype=np.float32)
        mask[10:50, 10:50] = 1.0
        contours = extract_mask_contours(mask)
        window = SceneSeparationWindow.__new__(SceneSeparationWindow)
        window.source_frame = frame
        window.preview_layer = 0
        window.mesh_editing = True
        window._preview_bounds = (0, 0, 64, 64, 64, 64)
        window.base_layer_masks = [mask.copy()]
        window.deformed_layer_masks = [mask.copy()]
        window.mask_source_contours = [copy_mask_contours(contours)]
        window.mask_target_contours = [copy_mask_contours(contours)]
        window._mesh_edit_changed_indices = set()
        window.processing_status = Mock()
        window._redraw_preview = Mock()
        window.layer_masks = [
            ("Mask", window._mask_rgba(frame, mask), mask.copy())
        ]
        original = window.layer_masks[0][2].copy()

        window._delete_mask_node(SimpleNamespace(x=10, y=10))

        self.assertEqual(len(window.mask_target_contours[0][0][0]), 3)
        self.assertIn(0, window._mesh_edit_changed_indices)
        self.assertFalse(np.array_equal(window.layer_masks[0][2], original))

    def test_right_click_keeps_at_least_three_nodes(self):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        mask = np.zeros((64, 64), dtype=np.float32)
        cv2.fillPoly(
            mask,
            [np.asarray(((10, 10), (50, 10), (30, 50)), dtype=np.int32)],
            1.0,
        )
        contours = extract_mask_contours(mask)
        window = SceneSeparationWindow.__new__(SceneSeparationWindow)
        window.source_frame = frame
        window.preview_layer = 0
        window.mesh_editing = True
        window._preview_bounds = (0, 0, 64, 64, 64, 64)
        window.mask_source_contours = [copy_mask_contours(contours)]
        window.mask_target_contours = [copy_mask_contours(contours)]
        window.processing_status = Mock()
        window._redraw_preview = Mock()
        original_contour = window.mask_target_contours[0][0][0].copy()

        window._delete_mask_node(SimpleNamespace(x=10, y=10))

        np.testing.assert_array_equal(
            window.mask_target_contours[0][0][0],
            original_contour,
        )
        window.processing_status.set.assert_called_once_with(
            "A mask edge needs at least three points"
        )

    def test_simplified_contours_stay_close_to_normalized_mask(self):
        mask = np.zeros((64, 64), dtype=np.float32)
        cv2.circle(mask, (32, 32), 18, 1.0, thickness=-1)
        normalized = normalize_mask_edges(mask)
        contours = extract_mask_contours(normalized)
        rebuilt = rasterize_mask_contours(normalized.shape, contours)

        self.assertLessEqual(
            np.count_nonzero(rebuilt != normalized),
            16,
        )

    def test_dragging_a_contour_point_updates_the_mask_edge(self):
        mask = np.zeros((64, 64), dtype=np.float32)
        cv2.circle(mask, (32, 32), 18, 1.0, thickness=-1)
        contours = extract_mask_contours(normalize_mask_edges(mask))
        target_contours = copy_mask_contours(contours)
        points, depth = target_contours[0]
        top_point = int(np.argmin(points[:, 1]))
        updated_points = points.copy()
        updated_points[top_point, 1] -= 5.0

        self.assertTrue(is_valid_contour_edit(points, updated_points))
        target_contours[0] = (updated_points, depth)
        edited = rasterize_mask_contours(mask.shape, target_contours)

        self.assertFalse(np.array_equal(edited, rasterize_mask_contours(
            mask.shape,
            contours,
        )))
        control_edges = _draw_mask_contours(edited, target_contours)
        self.assertGreater(np.count_nonzero(control_edges), 0)

    def test_self_intersecting_contour_edit_is_rejected(self):
        source = np.asarray(
            ((10, 10), (30, 10), (30, 30), (10, 30)),
            dtype=np.float32,
        )
        crossed = source.copy()
        crossed[1] = (5, 35)

        self.assertFalse(is_valid_contour_edit(source, crossed))

    def test_redundant_points_are_removed_but_edge_details_remain(self):
        source = np.asarray(
            ((10, 10), (20, 10), (30, 10), (30, 30), (10, 30)),
            dtype=np.float32,
        )
        target = source.copy()
        source_result, target_result, removed = (
            remove_redundant_contour_points(source, target)
        )

        self.assertEqual(removed, 1)
        self.assertEqual(len(source_result), 4)
        self.assertEqual(len(target_result), 4)

        detailed_source = source.copy()
        detailed_source[1, 1] = 12.0
        _, _, detail_removed = remove_redundant_contour_points(
            detailed_source,
            detailed_source,
        )
        self.assertEqual(detail_removed, 0)

    def test_redundant_nodes_are_removed_when_edits_are_applied(self):
        frame = np.zeros((40, 40, 3), dtype=np.uint8)
        points = np.asarray(
            ((5, 5), (15, 5), (25, 5), (25, 25), (5, 25)),
            dtype=np.float32,
        )
        contours = [(points, 0)]
        mask = rasterize_mask_contours((40, 40), contours)
        window = SceneSeparationWindow.__new__(SceneSeparationWindow)
        window.source_frame = frame
        window.base_layer_masks = [mask.copy()]
        window.deformed_layer_masks = [mask.copy()]
        window.mask_source_contours = [copy_mask_contours(contours)]
        window.mask_target_contours = [copy_mask_contours(contours)]
        window._mesh_edit_start_masks = [mask.copy()]
        window._mesh_edit_changed_indices = {0}
        window.layer_masks = [
            ("Mask", window._mask_rgba(frame, mask), mask.copy())
        ]

        window._commit_mesh_edits()

        self.assertEqual(len(window.mask_source_contours[0][0][0]), 4)
        self.assertEqual(len(window.mask_target_contours[0][0][0]), 4)

    def test_front_edit_updates_backing_layers_only_on_finish(self):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        front = np.zeros((64, 64), dtype=np.float32)
        cv2.circle(front, (32, 32), 18, 1.0, thickness=-1)
        front = normalize_mask_edges(front)
        back, front = compose_layer_masks([np.zeros_like(front), front])
        back_contours = extract_mask_contours(back)
        front_contours = extract_mask_contours(front)
        moved_front = copy_mask_contours(front_contours)
        points, depth = moved_front[0]
        top_point = int(np.argmin(points[:, 1]))
        points[top_point, 1] -= 5.0
        moved_front[0] = (points, depth)

        window = SceneSeparationWindow.__new__(SceneSeparationWindow)
        window.source_frame = frame
        window.base_layer_masks = [back.copy(), front.copy()]
        window.deformed_layer_masks = [back.copy(), front.copy()]
        window.mask_source_contours = [back_contours, front_contours]
        window.mask_target_contours = [
            copy_mask_contours(back_contours),
            moved_front,
        ]
        window._mesh_edit_start_masks = [back.copy(), front.copy()]
        window._mesh_edit_changed_indices = {1}
        window.mesh_editing = True
        window.mesh_edit_button = Mock()
        window.preview_canvas = Mock()
        window.processing_status = Mock()
        window._redraw_preview = Mock()
        window.layer_masks = [
            ("Background", window._mask_rgba(frame, back), back.copy()),
            ("Foreground", window._mask_rgba(frame, front), front.copy()),
        ]
        original_back = window.layer_masks[0][2].copy()

        window._apply_mask_contours(1)

        np.testing.assert_array_equal(window.layer_masks[0][2], original_back)

        window._toggle_mesh_editing()

        self.assertFalse(
            np.array_equal(window.layer_masks[0][2], original_back)
        )
        np.testing.assert_array_equal(
            window.layer_masks[0][2] + window.layer_masks[1][2],
            np.ones_like(front),
        )

    def test_front_mask_changes_reveal_and_recompose_layers_behind(self):
        back = np.zeros((8, 8), dtype=np.float32)
        middle = np.zeros_like(back)
        front = np.zeros_like(back)
        middle[2:6, 2:6] = 1.0
        front[3:7, 3:7] = 1.0

        previous_masks = compose_layer_masks([back, middle, front])
        updated_front = np.zeros_like(front)
        updated_front[:2, :2] = 1.0
        candidates = [mask.copy() for mask in previous_masks]
        candidates[2] = updated_front
        _, (back_mask, middle_mask, front_mask) = propagate_layer_mask_change(
            candidates,
            previous_masks,
            2,
        )

        self.assertEqual(front_mask[0, 0], 1.0)
        self.assertEqual(middle_mask[4, 4], 1.0)
        self.assertEqual(front_mask[4, 4], 0.0)
        self.assertEqual(back_mask[7, 7], 1.0)
        np.testing.assert_array_equal(
            back_mask + middle_mask + front_mask,
            np.ones_like(back),
        )


if __name__ == "__main__":
    unittest.main()
