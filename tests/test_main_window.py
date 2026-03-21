"""
Tests for the MainWindow class (Phases 1, 2, and 3).

This module tests the MainWindow widget which is the top-level application window.
MainWindow is responsible for:
- Creating and wiring the CanvasView (Phase 1)
- Owning the undo stack (Phase 3)
- Providing toolbar controls for all tools

Test coverage:
    Phase 1:
        - MainWindow construction
        - Canvas creation and wiring
        - Window properties

    Phase 2:
        - Pen tool toggle updates canvas
        - Color picker updates canvas
        - Brush size updates canvas

    Phase 3:
        - Undo stack ownership
        - Undo stack passed to canvas
        - Undo/redo actions in toolbar
"""

from unittest.mock import patch

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QColor, QUndoStack
from PyQt6.QtWidgets import QToolBar, QComboBox, QGraphicsPathItem

from ui.main_window import MainWindow
from canvas.canvas_view import CanvasView


# =============================================================================
# Phase 1: MainWindow Construction Tests
# =============================================================================

class TestMainWindowConstruction:
    """Tests for MainWindow initialization."""

    def test_main_window_can_be_constructed(self, qtbot):
        """
        MainWindow should construct successfully without errors.
        """
        window = MainWindow()
        qtbot.addWidget(window)

        assert window is not None

    def test_main_window_has_correct_title(self, main_window):
        """
        MainWindow should have the title 'Map Maker'.
        """
        assert main_window.windowTitle() == "Map Maker"

    def test_main_window_has_default_size(self, main_window):
        """
        MainWindow should have the expected default size.
        """
        assert main_window.width() == MainWindow.DEFAULT_WIDTH
        assert main_window.height() == MainWindow.DEFAULT_HEIGHT


class TestCanvasWiring:
    """Tests for canvas view creation and wiring."""

    def test_main_window_creates_canvas_view(self, main_window):
        """
        MainWindow should create a CanvasView as its central widget.
        """
        assert main_window._canvas_view is not None
        assert isinstance(main_window._canvas_view, CanvasView)

    def test_canvas_view_is_central_widget(self, main_window):
        """
        The CanvasView should be set as the central widget.
        """
        assert main_window.centralWidget() is main_window._canvas_view

    def test_main_window_passes_undo_stack_to_canvas(self, main_window):
        """
        MainWindow should pass its undo stack to the CanvasView.

        This is critical for Phase 3 undo/redo functionality.
        """
        # The canvas should have the same undo stack as the main window
        assert main_window._canvas_view._undo_stack is main_window._undo_stack


# =============================================================================
# Phase 3: Undo Stack Ownership Tests
# =============================================================================

class TestUndoStackOwnership:
    """Tests for undo stack ownership and configuration."""

    def test_main_window_owns_undo_stack(self, main_window):
        """
        MainWindow should own a QUndoStack instance.

        The undo stack is an application-level resource owned by MainWindow.
        """
        assert main_window._undo_stack is not None
        assert isinstance(main_window._undo_stack, QUndoStack)

    def test_undo_stack_parent_is_main_window(self, main_window):
        """
        The undo stack's parent should be the MainWindow.

        This ensures proper Qt object lifecycle management.
        """
        assert main_window._undo_stack.parent() is main_window


# =============================================================================
# Phase 1: Toolbar Tests
# =============================================================================

class TestToolbar:
    """Tests for toolbar creation and configuration."""

    def test_main_window_has_toolbar(self, main_window):
        """
        MainWindow should have a toolbar.
        """
        toolbars = main_window.findChildren(QToolBar)
        assert len(toolbars) > 0

    def test_toolbar_is_not_movable(self, main_window):
        """
        The toolbar should not be movable by the user.
        """
        toolbar = main_window.findChild(QToolBar)
        assert toolbar.isMovable() is False


# =============================================================================
# Phase 2: Pen Tool Tests
# =============================================================================

class TestPenToolToggle:
    """Tests for pen tool toggle behavior."""

    def test_pen_action_exists(self, main_window):
        """
        MainWindow should have a pen tool action.
        """
        assert main_window._pen_action is not None

    def test_pen_action_is_checkable(self, main_window):
        """
        The pen tool action should be checkable (toggleable).
        """
        assert main_window._pen_action.isCheckable() is True

    def test_pen_action_initially_unchecked(self, main_window):
        """
        The pen tool should start unchecked (drawing mode disabled).
        """
        assert main_window._pen_action.isChecked() is False

    def test_pen_tool_toggle_enables_canvas_drawing_mode(self, main_window):
        """
        Toggling the pen tool ON should enable drawing mode on the canvas.
        """
        main_window._pen_action.setChecked(True)

        assert main_window._canvas_view.is_drawing_mode() is True

    def test_pen_tool_toggle_disables_canvas_drawing_mode(self, main_window):
        """
        Toggling the pen tool OFF should disable drawing mode on the canvas.
        """
        main_window._pen_action.setChecked(True)
        main_window._pen_action.setChecked(False)

        assert main_window._canvas_view.is_drawing_mode() is False


# =============================================================================
# Phase 2: Color Picker Tests
# =============================================================================

class TestColorPicker:
    """Tests for color picker behavior."""

    def test_color_action_exists(self, main_window):
        """
        MainWindow should have a color picker action.
        """
        assert main_window._color_action is not None

    def test_initial_color_is_black(self, main_window):
        """
        The initial color should be black.
        """
        color = main_window._current_color
        assert color.red() == 0
        assert color.green() == 0
        assert color.blue() == 0

    def test_color_picker_updates_canvas_on_valid_selection(self, main_window):
        """
        Selecting a valid color should update the canvas stroke color.
        """
        test_color = QColor(255, 0, 0)  # Red

        # Mock QColorDialog to return a specific color
        with patch('ui.main_window.QColorDialog.getColor', return_value=test_color):
            main_window._on_color_picker_clicked()

        canvas_color = main_window._canvas_view.get_stroke_color()
        assert canvas_color.red() == 255
        assert canvas_color.green() == 0
        assert canvas_color.blue() == 0

    def test_color_picker_does_not_update_on_cancel(self, main_window):
        """
        Canceling the color dialog should not update the canvas color.
        """
        # Get initial color
        initial_color = QColor(main_window._current_color)

        # Mock QColorDialog to return an invalid color (simulates cancel)
        invalid_color = QColor()  # Invalid QColor
        with patch('ui.main_window.QColorDialog.getColor', return_value=invalid_color):
            main_window._on_color_picker_clicked()

        # Color should be unchanged
        assert main_window._current_color == initial_color

    def test_color_icon_updates_after_selection(self, main_window):
        """
        The color button icon should update to show the new color.
        """
        test_color = QColor(0, 255, 0)  # Green

        with patch('ui.main_window.QColorDialog.getColor', return_value=test_color):
            main_window._on_color_picker_clicked()

        # The icon should have been updated (icon is not null)
        assert main_window._color_action.icon().isNull() is False


# =============================================================================
# Phase 2: Brush Size Tests
# =============================================================================

class TestBrushSize:
    """Tests for brush size selection behavior."""

    def test_brush_combo_exists(self, main_window):
        """
        MainWindow should have a brush size combo box.
        """
        assert main_window._brush_combo is not None
        assert isinstance(main_window._brush_combo, QComboBox)

    def test_brush_combo_has_three_options(self, main_window):
        """
        The brush size combo should have three options.
        """
        assert main_window._brush_combo.count() == 3

    def test_brush_combo_default_is_medium(self, main_window):
        """
        The default brush size selection should be Medium (index 1).
        """
        assert main_window._brush_combo.currentIndex() == 1
        assert main_window._brush_combo.currentText() == "Medium (6px)"

    def test_brush_size_small_updates_canvas(self, main_window):
        """
        Selecting Small brush should set canvas brush size to 2.
        """
        main_window._brush_combo.setCurrentIndex(0)  # Small

        assert main_window._canvas_view.get_brush_size() == 2

    def test_brush_size_medium_updates_canvas(self, main_window):
        """
        Selecting Medium brush should set canvas brush size to 6.
        """
        main_window._brush_combo.setCurrentIndex(1)  # Medium

        assert main_window._canvas_view.get_brush_size() == 6

    def test_brush_size_large_updates_canvas(self, main_window):
        """
        Selecting Large brush should set canvas brush size to 12.
        """
        main_window._brush_combo.setCurrentIndex(2)  # Large

        assert main_window._canvas_view.get_brush_size() == 12


# =============================================================================
# Phase 1: Image Upload Tests
# =============================================================================

class TestImageUpload:
    """Tests for image upload functionality."""

    def test_upload_triggers_canvas_load_on_file_selection(self, main_window, valid_image_file):
        """
        Selecting a file in the upload dialog should load it into the canvas.
        """
        from PyQt6.QtWidgets import QGraphicsPixmapItem

        canvas = main_window.centralWidget()
        initial_pixmap_count = len([item for item in canvas.scene().items()
                                    if isinstance(item, QGraphicsPixmapItem)])

        # Mock QFileDialog to return our test file
        with patch('ui.main_window.QFileDialog.getOpenFileName',
                   return_value=(valid_image_file, "")):
            main_window._on_upload_clicked()

        # Canvas should have a background image (one more pixmap item)
        final_pixmap_count = len([item for item in canvas.scene().items()
                                  if isinstance(item, QGraphicsPixmapItem)])
        assert final_pixmap_count == initial_pixmap_count + 1

    def test_upload_does_nothing_on_cancel(self, main_window):
        """
        Canceling the file dialog should not affect the canvas.
        """
        from PyQt6.QtWidgets import QGraphicsPixmapItem

        canvas = main_window.centralWidget()
        initial_pixmap_count = len([item for item in canvas.scene().items()
                                    if isinstance(item, QGraphicsPixmapItem)])

        # Mock QFileDialog to return empty string (cancel)
        with patch('ui.main_window.QFileDialog.getOpenFileName',
                   return_value=("", "")):
            main_window._on_upload_clicked()

        # Canvas should not have any new pixmap items
        final_pixmap_count = len([item for item in canvas.scene().items()
                                  if isinstance(item, QGraphicsPixmapItem)])
        assert final_pixmap_count == initial_pixmap_count


# =============================================================================
# Integration Tests: Full Drawing Workflow
# =============================================================================

class TestDrawingIntegration:
    """Integration tests for complete drawing workflow through MainWindow."""

    def test_full_drawing_workflow(self, main_window, qtbot):
        """
        Test a complete drawing workflow: enable tool, set color, draw, undo, redo.
        """
        canvas = main_window.centralWidget()
        undo_stack = main_window._undo_stack

        # 1. Enable pen tool
        main_window._pen_action.setChecked(True)
        assert canvas.is_drawing_mode() is True

        # 2. Set a custom color
        test_color = QColor(255, 128, 0)  # Orange
        with patch('ui.main_window.QColorDialog.getColor', return_value=test_color):
            main_window._on_color_picker_clicked()
        assert canvas.get_stroke_color().red() == 255

        # 3. Set brush size to large
        main_window._brush_combo.setCurrentIndex(2)  # Large
        assert canvas.get_brush_size() == 12

        # 4. Draw a stroke
        qtbot.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(50, 50))
        qtbot.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(50, 50))

        # Find the stroke in the scene
        path_items = [item for item in canvas.scene().items()
                      if isinstance(item, QGraphicsPathItem)]
        assert len(path_items) == 1
        stroke_item = path_items[0]

        # Stroke should be in scene and undo stack
        assert stroke_item in canvas.scene().items()
        assert undo_stack.count() == 1

        # 5. Undo
        undo_stack.undo()
        assert stroke_item not in canvas.scene().items()

        # 6. Redo
        undo_stack.redo()
        assert stroke_item in canvas.scene().items()

    def test_multiple_strokes_integration(self, main_window, qtbot):
        """
        Test drawing multiple strokes and undoing them in order.
        """
        canvas = main_window.centralWidget()
        undo_stack = main_window._undo_stack

        main_window._pen_action.setChecked(True)

        # Draw first stroke
        qtbot.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
        qtbot.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(10, 10))

        path_items_after_first = [item for item in canvas.scene().items()
                                   if isinstance(item, QGraphicsPathItem)]
        stroke1 = path_items_after_first[0]

        # Draw second stroke
        qtbot.mousePress(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(80, 80))
        qtbot.mouseRelease(canvas.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(80, 80))

        path_items_after_second = [item for item in canvas.scene().items()
                                    if isinstance(item, QGraphicsPathItem)]
        stroke2 = [item for item in path_items_after_second if item is not stroke1][0]

        # Both strokes present, 2 commands in stack
        assert undo_stack.count() == 2
        assert stroke1 in canvas.scene().items()
        assert stroke2 in canvas.scene().items()

        # Undo twice
        undo_stack.undo()
        assert stroke2 not in canvas.scene().items()
        assert stroke1 in canvas.scene().items()

        undo_stack.undo()
        assert stroke1 not in canvas.scene().items()

        # Redo both
        undo_stack.redo()
        assert stroke1 in canvas.scene().items()

        undo_stack.redo()
        assert stroke2 in canvas.scene().items()
