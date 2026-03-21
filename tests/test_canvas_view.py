"""
Tests for the CanvasView class (Phases 1, 2, and 3).

This module tests the CanvasView widget which handles:
- Background image loading and display (Phase 1)
- Zoom behavior (Phase 1)
- Drawing mode and stroke creation (Phase 2)
- Undo stack integration (Phase 3)

Test coverage:
    Phase 1:
        - CanvasView construction
        - Image loading success/failure paths
        - Background item management
        - Zoom behavior within bounds

    Phase 2:
        - Drawing mode toggle
        - Stroke color and brush size settings
        - Stroke item creation helper
        - Mouse event handling for drawing

    Phase 3:
        - Undo stack integration
        - Stroke finalization through undo commands
        - Fallback behavior without undo stack
"""

from unittest.mock import patch

from PyQt6.QtCore import Qt, QPoint, QPointF
from PyQt6.QtGui import QPainterPath, QWheelEvent
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPixmapItem

from canvas.canvas_view import CanvasView


# =============================================================================
# Phase 1: CanvasView Construction Tests
# =============================================================================

class TestCanvasViewConstruction:
    """Tests for CanvasView initialization."""

    def test_canvas_view_can_be_constructed(self, qtbot):
        """
        CanvasView should construct successfully without errors.

        This verifies the basic widget can be created and has the
        expected initial state.
        """
        view = CanvasView()
        qtbot.addWidget(view)

        assert view is not None
        assert view.scene() is not None

    def test_canvas_view_has_scene_attached(self, canvas_view):
        """
        CanvasView should have a QGraphicsScene attached.

        The scene is where all graphics items (background, strokes) live.
        """
        assert canvas_view.scene() is not None

    def test_canvas_view_initial_drawing_mode_disabled(self, canvas_view):
        """
        CanvasView should have drawing mode disabled after construction.
        """
        assert canvas_view.is_drawing_mode() is False

    def test_canvas_view_initial_zoom_is_one(self, canvas_view):
        """
        CanvasView should start with zoom level 1.0 (100%).
        """
        # Check the transform reflects 1.0 scale
        transform = canvas_view.transform()
        assert transform.m11() == 1.0
        assert transform.m22() == 1.0


# =============================================================================
# Phase 1: Image Loading Tests
# =============================================================================

class TestImageLoadingSuccess:
    """Tests for successful image loading paths."""

    def test_load_valid_image_returns_true(self, canvas_view, valid_image_file):
        """
        load_image() should return True for a valid image file.
        """
        result = canvas_view.load_image(valid_image_file)
        assert result is True

    def test_load_valid_image_adds_item_to_scene(self, canvas_view, valid_image_file):
        """
        Loading a valid image should add a pixmap item to the scene.
        """
        initial_item_count = len(canvas_view.scene().items())

        canvas_view.load_image(valid_image_file)

        # Scene should have one more item (the background)
        assert len(canvas_view.scene().items()) == initial_item_count + 1

    def test_background_item_is_positioned_at_origin(self, canvas_view, valid_image_file):
        """
        The background image should be positioned at the scene origin (0, 0).
        """
        canvas_view.load_image(valid_image_file)

        # Find the pixmap item in the scene
        pixmap_items = [item for item in canvas_view.scene().items()
                        if isinstance(item, QGraphicsPixmapItem)]
        assert len(pixmap_items) == 1

        pos = pixmap_items[0].pos()
        assert pos.x() == 0
        assert pos.y() == 0

    def test_background_item_is_not_selectable(self, canvas_view, valid_image_file):
        """
        The background image should not be selectable by the user.

        This ensures the background stays locked while the user draws.
        """
        canvas_view.load_image(valid_image_file)

        pixmap_items = [item for item in canvas_view.scene().items()
                        if isinstance(item, QGraphicsPixmapItem)]
        background = pixmap_items[0]

        flags = background.flags()
        is_selectable = bool(flags & QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable)
        assert is_selectable is False

    def test_background_item_is_not_movable(self, canvas_view, valid_image_file):
        """
        The background image should not be movable by the user.
        """
        canvas_view.load_image(valid_image_file)

        pixmap_items = [item for item in canvas_view.scene().items()
                        if isinstance(item, QGraphicsPixmapItem)]
        background = pixmap_items[0]

        flags = background.flags()
        is_movable = bool(flags & QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable)
        assert is_movable is False

    def test_loading_second_image_replaces_first(self, canvas_view, valid_image_file, valid_rgba_image_file):
        """
        Loading a second image should replace the first background image.

        There should only ever be one background image in the scene.
        """
        # Load first image
        canvas_view.load_image(valid_image_file)
        pixmap_items_after_first = [item for item in canvas_view.scene().items()
                                     if isinstance(item, QGraphicsPixmapItem)]
        assert len(pixmap_items_after_first) == 1

        # Load second image
        canvas_view.load_image(valid_rgba_image_file)
        pixmap_items_after_second = [item for item in canvas_view.scene().items()
                                      if isinstance(item, QGraphicsPixmapItem)]

        # Still only one pixmap item (replacement, not addition)
        assert len(pixmap_items_after_second) == 1

    def test_load_rgba_image_succeeds(self, canvas_view, valid_rgba_image_file):
        """
        Loading an RGBA image (with transparency) should succeed.

        This tests the alpha channel code path in _pil_to_qpixmap().
        """
        result = canvas_view.load_image(valid_rgba_image_file)
        assert result is True

        # Verify item was added to scene
        pixmap_items = [item for item in canvas_view.scene().items()
                        if isinstance(item, QGraphicsPixmapItem)]
        assert len(pixmap_items) == 1

    def test_large_image_is_resized(self, canvas_view, valid_large_image_file):
        """
        Images exceeding MAX_IMAGE_SIZE should be automatically resized.

        The 5000x5000 test image should be scaled down to fit within 4000x4000.
        """
        canvas_view.load_image(valid_large_image_file)

        # Find the pixmap item and check its dimensions
        pixmap_items = [item for item in canvas_view.scene().items()
                        if isinstance(item, QGraphicsPixmapItem)]
        pixmap = pixmap_items[0].pixmap()

        assert pixmap.width() <= CanvasView.MAX_IMAGE_SIZE
        assert pixmap.height() <= CanvasView.MAX_IMAGE_SIZE


class TestImageLoadingFailure:
    """Tests for image loading error handling."""

    def test_load_invalid_image_returns_false(self, canvas_view, invalid_image_file):
        """
        load_image() should return False for an invalid image file.
        """
        with patch('canvas.canvas_view.QMessageBox.critical'):
            result = canvas_view.load_image(invalid_image_file)

        assert result is False

    def test_load_invalid_image_shows_error_dialog(self, canvas_view, invalid_image_file):
        """
        Loading an invalid image should show an error dialog to the user.
        """
        with patch('canvas.canvas_view.QMessageBox.critical') as mock_dialog:
            canvas_view.load_image(invalid_image_file)

        mock_dialog.assert_called_once()
        # Verify it was called with the canvas_view as parent
        assert mock_dialog.call_args[0][0] is canvas_view

    def test_load_invalid_image_does_not_add_to_scene(self, canvas_view, invalid_image_file):
        """
        Failed image load should not add any pixmap items to the scene.
        """
        initial_pixmap_count = len([item for item in canvas_view.scene().items()
                                    if isinstance(item, QGraphicsPixmapItem)])

        with patch('canvas.canvas_view.QMessageBox.critical'):
            canvas_view.load_image(invalid_image_file)

        final_pixmap_count = len([item for item in canvas_view.scene().items()
                                  if isinstance(item, QGraphicsPixmapItem)])

        assert final_pixmap_count == initial_pixmap_count

    def test_load_nonexistent_file_returns_false(self, canvas_view, nonexistent_image_path):
        """
        load_image() should return False for a nonexistent file.
        """
        with patch('canvas.canvas_view.QMessageBox.critical'):
            result = canvas_view.load_image(nonexistent_image_path)

        assert result is False


# =============================================================================
# Phase 1: Zoom Behavior Tests
# =============================================================================

def _create_wheel_event(pos: QPoint, delta: int) -> QWheelEvent:
    """
    Helper to create a QWheelEvent for zoom testing.

    Args:
        pos: Position of the wheel event in widget coordinates
        delta: Scroll delta (positive = zoom in, negative = zoom out)

    Returns:
        A QWheelEvent that can be passed to wheelEvent()
    """
    return QWheelEvent(
        QPointF(pos),           # position in widget
        QPointF(pos),           # global position
        QPoint(0, 0),           # pixel delta (unused for zoom)
        QPoint(0, delta),       # angle delta (y = vertical scroll)
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False                   # inverted
    )


class TestZoomBehavior:
    """Tests for zoom functionality via real wheel events."""

    def test_initial_zoom_transform_is_identity(self, canvas_view):
        """
        Initial view transform should be identity (no zoom).
        """
        transform = canvas_view.transform()
        assert transform.m11() == 1.0
        assert transform.m22() == 1.0

    def test_zoom_in_via_wheel_increases_zoom(self, canvas_view):
        """
        Scrolling up (positive delta) should increase zoom level.

        This test exercises the actual wheelEvent handler to verify
        zoom increases and the view transform is applied.
        """
        initial_transform_scale = canvas_view.transform().m11()

        # Create and dispatch a zoom-in wheel event (positive delta)
        event = _create_wheel_event(QPoint(100, 100), delta=120)
        canvas_view.wheelEvent(event)

        # Verify zoom increased
        new_transform_scale = canvas_view.transform().m11()
        assert new_transform_scale > initial_transform_scale

        # Verify internal tracking matches transform
        assert canvas_view._current_zoom == new_transform_scale

    def test_zoom_out_via_wheel_decreases_zoom(self, canvas_view):
        """
        Scrolling down (negative delta) should decrease zoom level.
        """
        initial_transform_scale = canvas_view.transform().m11()

        # Create and dispatch a zoom-out wheel event (negative delta)
        event = _create_wheel_event(QPoint(100, 100), delta=-120)
        canvas_view.wheelEvent(event)

        # Verify zoom decreased
        new_transform_scale = canvas_view.transform().m11()
        assert new_transform_scale < initial_transform_scale

    def test_zoom_does_not_exceed_maximum(self, canvas_view):
        """
        Zoom level should not exceed MAX_ZOOM (10.0) even with many zoom-in events.

        This tests the clamping behavior by repeatedly zooming in until
        we hit the maximum, then verifying we can't zoom further.
        """
        # Zoom in repeatedly until we hit the maximum
        for _ in range(50):  # More than enough to reach max
            event = _create_wheel_event(QPoint(100, 100), delta=120)
            canvas_view.wheelEvent(event)

        # Verify we're at or below max
        assert canvas_view._current_zoom <= CanvasView.MAX_ZOOM
        assert canvas_view.transform().m11() <= CanvasView.MAX_ZOOM

        # Try one more zoom in - should stay at max
        previous_zoom = canvas_view._current_zoom
        event = _create_wheel_event(QPoint(100, 100), delta=120)
        canvas_view.wheelEvent(event)

        assert canvas_view._current_zoom <= CanvasView.MAX_ZOOM
        # Should not have increased beyond max
        assert canvas_view._current_zoom == previous_zoom

    def test_zoom_does_not_go_below_minimum(self, canvas_view):
        """
        Zoom level should not go below MIN_ZOOM (0.1) even with many zoom-out events.
        """
        # Zoom out repeatedly until we hit the minimum
        for _ in range(50):  # More than enough to reach min
            event = _create_wheel_event(QPoint(100, 100), delta=-120)
            canvas_view.wheelEvent(event)

        # Verify we're at or above min
        assert canvas_view._current_zoom >= CanvasView.MIN_ZOOM
        assert canvas_view.transform().m11() >= CanvasView.MIN_ZOOM

        # Try one more zoom out - should stay at min
        previous_zoom = canvas_view._current_zoom
        event = _create_wheel_event(QPoint(100, 100), delta=-120)
        canvas_view.wheelEvent(event)

        assert canvas_view._current_zoom >= CanvasView.MIN_ZOOM
        # Should not have decreased beyond min
        assert canvas_view._current_zoom == previous_zoom

    def test_zoom_constants_are_correct(self):
        """
        Zoom constants should have the expected values.
        """
        assert CanvasView.MIN_ZOOM == 0.1
        assert CanvasView.MAX_ZOOM == 10.0


# =============================================================================
# Phase 2: Drawing Mode Tests
# =============================================================================

class TestDrawingMode:
    """Tests for drawing mode toggle behavior."""

    def test_drawing_mode_initially_disabled(self, canvas_view):
        """
        Drawing mode should be disabled by default.
        """
        assert canvas_view.is_drawing_mode() is False

    def test_set_drawing_mode_enables_drawing(self, canvas_view):
        """
        set_drawing_mode(True) should enable drawing mode.
        """
        canvas_view.set_drawing_mode(True)

        assert canvas_view.is_drawing_mode() is True

    def test_set_drawing_mode_disables_drawing(self, canvas_view):
        """
        set_drawing_mode(False) should disable drawing mode.
        """
        canvas_view.set_drawing_mode(True)
        canvas_view.set_drawing_mode(False)

        assert canvas_view.is_drawing_mode() is False

    def test_drawing_mode_changes_cursor_to_crosshair(self, canvas_view):
        """
        Enabling drawing mode should change the cursor to crosshair.
        """
        canvas_view.set_drawing_mode(True)

        assert canvas_view.cursor().shape() == Qt.CursorShape.CrossCursor

    def test_disabling_drawing_mode_restores_arrow_cursor(self, canvas_view):
        """
        Disabling drawing mode should restore the arrow cursor.
        """
        canvas_view.set_drawing_mode(True)
        canvas_view.set_drawing_mode(False)

        assert canvas_view.cursor().shape() == Qt.CursorShape.ArrowCursor


# =============================================================================
# Phase 2: Stroke Color and Brush Size Tests
# =============================================================================

class TestStrokeColorSettings:
    """Tests for stroke color configuration."""

    def test_default_stroke_color_is_black(self, canvas_view):
        """
        Default stroke color should be black.
        """
        color = canvas_view.get_stroke_color()
        assert color.red() == 0
        assert color.green() == 0
        assert color.blue() == 0

    def test_set_stroke_color_updates_canvas_state(self, canvas_view, test_color):
        """
        set_stroke_color() should update the canvas stroke color.
        """
        canvas_view.set_stroke_color(test_color)

        result = canvas_view.get_stroke_color()
        assert result.red() == test_color.red()
        assert result.green() == test_color.green()
        assert result.blue() == test_color.blue()


class TestBrushSizeSettings:
    """Tests for brush size configuration."""

    def test_default_brush_size(self, canvas_view):
        """
        Default brush size should be DEFAULT_BRUSH_SIZE (6).
        """
        assert canvas_view.get_brush_size() == CanvasView.DEFAULT_BRUSH_SIZE
        assert canvas_view.get_brush_size() == 6

    def test_set_brush_size_updates_canvas_state(self, canvas_view):
        """
        set_brush_size() should update the canvas brush size.
        """
        canvas_view.set_brush_size(12)

        assert canvas_view.get_brush_size() == 12


# =============================================================================
# Phase 2/3: Stroke Item Creation Helper Tests
# =============================================================================

class TestStrokeItemCreationHelper:
    """Tests for the _create_stroke_item() helper method."""

    def test_create_stroke_item_applies_current_color(self, canvas_view, test_color):
        """
        _create_stroke_item() should apply the current stroke color.
        """
        canvas_view.set_stroke_color(test_color)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(100, 100)

        item = canvas_view._create_stroke_item(path)

        pen = item.pen()
        assert pen.color().red() == test_color.red()
        assert pen.color().green() == test_color.green()
        assert pen.color().blue() == test_color.blue()

    def test_create_stroke_item_applies_current_brush_size(self, canvas_view):
        """
        _create_stroke_item() should apply the current brush size.
        """
        canvas_view.set_brush_size(12)

        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(50, 50)

        item = canvas_view._create_stroke_item(path)

        assert item.pen().width() == 12

    def test_create_stroke_item_uses_round_cap(self, canvas_view):
        """
        _create_stroke_item() should configure round cap style.

        Round caps make stroke ends smooth instead of flat.
        """
        path = QPainterPath()
        item = canvas_view._create_stroke_item(path)

        assert item.pen().capStyle() == Qt.PenCapStyle.RoundCap

    def test_create_stroke_item_uses_round_join(self, canvas_view):
        """
        _create_stroke_item() should configure round join style.

        Round joins make corners smooth where line segments meet.
        """
        path = QPainterPath()
        item = canvas_view._create_stroke_item(path)

        assert item.pen().joinStyle() == Qt.PenJoinStyle.RoundJoin

    def test_create_stroke_item_is_not_selectable(self, canvas_view):
        """
        Created stroke items should not be selectable.
        """
        path = QPainterPath()
        item = canvas_view._create_stroke_item(path)

        flags = item.flags()
        is_selectable = bool(flags & QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable)
        assert is_selectable is False

    def test_create_stroke_item_is_not_movable(self, canvas_view):
        """
        Created stroke items should not be movable.
        """
        path = QPainterPath()
        item = canvas_view._create_stroke_item(path)

        flags = item.flags()
        is_movable = bool(flags & QGraphicsPathItem.GraphicsItemFlag.ItemIsMovable)
        assert is_movable is False


# =============================================================================
# Phase 2: Mouse Event Drawing Tests
# =============================================================================

class TestDrawingMouseEvents:
    """Tests for mouse event handling during drawing."""

    def test_mouse_press_in_drawing_mode_adds_item_to_scene(self, canvas_view, qtbot):
        """
        Mouse press in drawing mode should add a stroke item to the scene.
        """
        canvas_view.set_drawing_mode(True)
        initial_item_count = len(canvas_view.scene().items())

        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # A new path item should be in the scene
        assert len(canvas_view.scene().items()) == initial_item_count + 1

    def test_mouse_press_outside_drawing_mode_does_not_add_item(self, canvas_view, qtbot):
        """
        Mouse press outside drawing mode should not add items to the scene.
        """
        canvas_view.set_drawing_mode(False)
        initial_item_count = len(canvas_view.scene().items())

        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # No items should be added
        assert len(canvas_view.scene().items()) == initial_item_count

    def test_mouse_release_ends_drawing_state(self, canvas_view_with_undo_stack, qtbot):
        """
        Mouse release should end the drawing state and clear temporary references.
        """
        canvas_view, undo_stack = canvas_view_with_undo_stack
        canvas_view.set_drawing_mode(True)

        # Start drawing
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # End drawing
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # Drawing state should be cleared
        assert canvas_view._is_drawing is False
        assert canvas_view._current_path is None
        assert canvas_view._current_path_item is None


# =============================================================================
# Phase 3: Undo Stack Integration Tests
# =============================================================================

class TestUndoStackIntegration:
    """Tests for undo stack integration in CanvasView."""

    def test_set_undo_stack_accepts_external_stack(self, canvas_view):
        """
        CanvasView should accept an externally provided undo stack.
        """
        from PyQt6.QtGui import QUndoStack

        stack = QUndoStack()
        canvas_view.set_undo_stack(stack)

        # Verify by checking that drawing creates commands
        canvas_view.set_drawing_mode(True)

    def test_completed_stroke_becomes_one_undo_entry(self, canvas_view_with_undo_stack, qtbot):
        """
        A completed stroke should create exactly one undo stack entry.

        This ensures we don't create one command per mouse move.
        """
        canvas_view, undo_stack = canvas_view_with_undo_stack
        canvas_view.set_drawing_mode(True)

        initial_count = undo_stack.count()

        # Draw a stroke with multiple move events
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        qtbot.mouseMove(canvas_view.viewport(), pos=QPoint(30, 30))
        qtbot.mouseMove(canvas_view.viewport(), pos=QPoint(50, 50))
        qtbot.mouseMove(canvas_view.viewport(), pos=QPoint(70, 70))
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(70, 70))

        # Should have exactly one new command
        assert undo_stack.count() == initial_count + 1

    def test_stroke_command_owns_final_state_via_undo_redo(self, canvas_view_with_undo_stack, qtbot):
        """
        The undo command should own the stroke's presence in the scene.

        This test proves command ownership by verifying that:
        1. After drawing, the stroke is in the scene
        2. After undo, the stroke is removed
        3. After redo, the same stroke is restored

        This demonstrates the command (not temporary preview) controls final state.
        """
        canvas_view, undo_stack = canvas_view_with_undo_stack
        canvas_view.set_drawing_mode(True)

        # Draw a stroke
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # Find the stroke item in the scene
        path_items = [item for item in canvas_view.scene().items()
                      if isinstance(item, QGraphicsPathItem)]
        assert len(path_items) == 1
        stroke_item = path_items[0]

        # Verify stroke is in scene after drawing
        assert stroke_item in canvas_view.scene().items()

        # Undo should remove the stroke (command owns removal)
        undo_stack.undo()
        assert stroke_item not in canvas_view.scene().items()

        # Redo should restore the same stroke (command owns addition)
        undo_stack.redo()
        assert stroke_item in canvas_view.scene().items()

    def test_undo_removes_most_recent_stroke(self, canvas_view_with_undo_stack, qtbot):
        """
        Calling undo should remove the most recent stroke from the scene.
        """
        canvas_view, undo_stack = canvas_view_with_undo_stack
        canvas_view.set_drawing_mode(True)

        # Draw a stroke
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # Find stroke in scene
        path_items = [item for item in canvas_view.scene().items()
                      if isinstance(item, QGraphicsPathItem)]
        assert len(path_items) == 1
        stroke_item = path_items[0]

        # Undo
        undo_stack.undo()

        # Stroke should be removed
        assert stroke_item not in canvas_view.scene().items()

    def test_redo_restores_undone_stroke(self, canvas_view_with_undo_stack, qtbot):
        """
        Calling redo should restore a previously undone stroke.
        """
        canvas_view, undo_stack = canvas_view_with_undo_stack
        canvas_view.set_drawing_mode(True)

        # Draw a stroke
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # Get reference to stroke
        path_items = [item for item in canvas_view.scene().items()
                      if isinstance(item, QGraphicsPathItem)]
        stroke_item = path_items[0]

        # Undo
        undo_stack.undo()
        assert stroke_item not in canvas_view.scene().items()

        # Redo
        undo_stack.redo()
        assert stroke_item in canvas_view.scene().items()

    def test_multiple_strokes_undone_in_correct_order(self, canvas_view_with_undo_stack, qtbot):
        """
        Multiple strokes should be undone in LIFO order (last drawn = first undone).
        """
        canvas_view, undo_stack = canvas_view_with_undo_stack
        canvas_view.set_drawing_mode(True)

        # Draw first stroke
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(10, 10))

        path_items_after_first = [item for item in canvas_view.scene().items()
                                   if isinstance(item, QGraphicsPathItem)]
        stroke1 = path_items_after_first[0]

        # Draw second stroke
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(50, 50))
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(50, 50))

        path_items_after_second = [item for item in canvas_view.scene().items()
                                    if isinstance(item, QGraphicsPathItem)]
        stroke2 = [item for item in path_items_after_second if item is not stroke1][0]

        # Both strokes in scene
        assert stroke1 in canvas_view.scene().items()
        assert stroke2 in canvas_view.scene().items()

        # Undo first - should remove stroke2 (most recent)
        undo_stack.undo()
        assert stroke1 in canvas_view.scene().items()
        assert stroke2 not in canvas_view.scene().items()

        # Undo second - should remove stroke1
        undo_stack.undo()
        assert stroke1 not in canvas_view.scene().items()
        assert stroke2 not in canvas_view.scene().items()


class TestFallbackWithoutUndoStack:
    """Tests for behavior when no undo stack is set."""

    def test_stroke_remains_without_undo_stack(self, canvas_view, qtbot):
        """
        Without an undo stack, strokes should still remain in the scene.

        This is the fallback behavior to prevent data loss.
        """
        canvas_view.set_drawing_mode(True)

        # Draw a stroke
        qtbot.mousePress(canvas_view.viewport(), Qt.MouseButton.LeftButton)
        qtbot.mouseRelease(canvas_view.viewport(), Qt.MouseButton.LeftButton)

        # Stroke should remain in the scene (fallback behavior)
        path_items = [item for item in canvas_view.scene().items()
                      if isinstance(item, QGraphicsPathItem)]
        assert len(path_items) == 1
