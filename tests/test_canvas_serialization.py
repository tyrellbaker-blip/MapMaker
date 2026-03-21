"""
Tests for the canvas serialization methods (Phase 4).

This module tests the serialization and deserialization of canvas data
for save/load functionality. It covers:
    - Extracting path data from QGraphicsPathItems (serialize_paths)
    - Loading paths from saved data (load_serialized_paths)
    - Path data round-trip integrity
    - Canvas clearing (clear_map_content)

Test coverage:
    Phase 4:
        - serialize_paths() extracts path data correctly
        - load_serialized_paths() reconstructs paths from saved data
        - Path data round-trips preserve coordinates
        - Path data round-trips preserve colors
        - Path data round-trips preserve widths
        - clear_map_content() removes strokes and background
        - get_background_image_path() returns correct path
        - set_background_image_path() updates the path
"""

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainterPath, QPen, QColor
from PyQt6.QtWidgets import QGraphicsPathItem, QGraphicsPixmapItem


# =============================================================================
# Phase 4: Path Extraction Tests
# =============================================================================

class TestSerializePaths:
    """Tests for CanvasView.serialize_paths()."""

    def test_serialize_paths_empty_canvas(self, canvas_view):
        """
        serialize_paths() should return empty list for empty canvas.
        """
        result = canvas_view.serialize_paths()
        assert result == []

    def test_serialize_paths_extracts_points(self, canvas_view):
        """
        serialize_paths() should extract path coordinates as ordered points.
        """
        # Create a path item manually
        path = QPainterPath()
        path.moveTo(10, 20)
        path.lineTo(30, 40)

        item = QGraphicsPathItem(path)
        pen = QPen(QColor("#FF0000"))
        pen.setWidth(6)
        item.setPen(pen)

        canvas_view.get_scene_for_testing().addItem(item)

        result = canvas_view.serialize_paths()

        assert len(result) == 1
        points = result[0]["points"]
        assert len(points) == 2
        # First point from moveTo
        assert points[0]["x"] == 10.0
        assert points[0]["y"] == 20.0
        # Second point from lineTo
        assert points[1]["x"] == 30.0
        assert points[1]["y"] == 40.0

    def test_serialize_paths_extracts_stroke_color(self, canvas_view):
        """
        serialize_paths() should extract stroke color as hex.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(10, 10)

        item = QGraphicsPathItem(path)
        pen = QPen(QColor(255, 128, 0))  # Orange
        item.setPen(pen)

        canvas_view.get_scene_for_testing().addItem(item)

        result = canvas_view.serialize_paths()
        # Color should be hex format (lowercase)
        assert result[0]["stroke_color"].lower() == "#ff8000"

    def test_serialize_paths_extracts_stroke_width(self, canvas_view):
        """
        serialize_paths() should extract stroke width.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(10, 10)

        item = QGraphicsPathItem(path)
        pen = QPen()
        pen.setWidth(12)
        item.setPen(pen)

        canvas_view.get_scene_for_testing().addItem(item)

        result = canvas_view.serialize_paths()
        assert result[0]["stroke_width"] == 12

    def test_serialize_paths_multiple_strokes(self, canvas_view):
        """
        serialize_paths() should extract all strokes.
        """
        # Add multiple path items
        for i in range(3):
            path = QPainterPath()
            path.moveTo(i * 10, i * 10)
            path.lineTo(i * 10 + 5, i * 10 + 5)
            item = QGraphicsPathItem(path)
            canvas_view.get_scene_for_testing().addItem(item)

        result = canvas_view.serialize_paths()
        assert len(result) == 3


# =============================================================================
# Phase 4: Path Loading Tests
# =============================================================================

class TestLoadSerializedPaths:
    """Tests for CanvasView.load_serialized_paths()."""

    def test_load_paths_creates_items(self, canvas_view, sample_path_data):
        """
        load_serialized_paths() should create QGraphicsPathItems in the scene.
        """
        canvas_view.load_serialized_paths(sample_path_data)

        scene = canvas_view.get_scene_for_testing()
        path_items = [item for item in scene.items()
                      if isinstance(item, QGraphicsPathItem)]

        assert len(path_items) == 2

    def test_load_paths_reconstructs_geometry(self, canvas_view):
        """
        load_serialized_paths() should reconstruct path geometry correctly.
        """
        paths = [{
            "points": [
                {"x": 100.0, "y": 200.0},
                {"x": 300.0, "y": 400.0}
            ],
            "stroke_color": "#000000",
            "stroke_width": 6
        }]

        canvas_view.load_serialized_paths(paths)

        scene = canvas_view.get_scene_for_testing()
        path_items = [item for item in scene.items()
                      if isinstance(item, QGraphicsPathItem)]

        assert len(path_items) == 1
        painter_path = path_items[0].path()
        assert painter_path.elementCount() == 2

    def test_load_paths_applies_color(self, canvas_view):
        """
        load_serialized_paths() should apply the saved color.
        """
        paths = [{
            "points": [
                {"x": 0.0, "y": 0.0},
                {"x": 100.0, "y": 100.0}
            ],
            "stroke_color": "#FF0000",
            "stroke_width": 6
        }]

        canvas_view.load_serialized_paths(paths)

        scene = canvas_view.get_scene_for_testing()
        path_items = [item for item in scene.items()
                      if isinstance(item, QGraphicsPathItem)]

        pen = path_items[0].pen()
        assert pen.color().name().lower() == "#ff0000"

    def test_load_paths_applies_width(self, canvas_view):
        """
        load_serialized_paths() should apply the saved width.
        """
        paths = [{
            "points": [
                {"x": 0.0, "y": 0.0},
                {"x": 100.0, "y": 100.0}
            ],
            "stroke_color": "#000000",
            "stroke_width": 12
        }]

        canvas_view.load_serialized_paths(paths)

        scene = canvas_view.get_scene_for_testing()
        path_items = [item for item in scene.items()
                      if isinstance(item, QGraphicsPathItem)]

        pen = path_items[0].pen()
        assert pen.width() == 12

    def test_load_paths_skips_short_paths(self, canvas_view):
        """
        load_serialized_paths() should skip paths with fewer than 2 points.
        """
        paths = [
            {
                "points": [{"x": 0.0, "y": 0.0}],  # Only one point - skip
                "stroke_color": "#000000",
                "stroke_width": 6
            },
            {
                "points": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 100.0, "y": 100.0}
                ],
                "stroke_color": "#FF0000",
                "stroke_width": 6
            }
        ]

        canvas_view.load_serialized_paths(paths)

        scene = canvas_view.get_scene_for_testing()
        path_items = [item for item in scene.items()
                      if isinstance(item, QGraphicsPathItem)]

        # Only the path with 2+ points should be added
        assert len(path_items) == 1


# =============================================================================
# Phase 4: Round-Trip Tests
# =============================================================================

class TestPathRoundTrip:
    """Tests for path data round-trip integrity."""

    def test_round_trip_preserves_coordinates(self, canvas_view):
        """
        Path coordinates should survive a save/load round-trip.
        """
        # Create original path
        original_path = QPainterPath()
        original_path.moveTo(100.5, 200.5)
        original_path.lineTo(300.5, 400.5)
        original_path.lineTo(500.5, 600.5)

        item = QGraphicsPathItem(original_path)
        pen = QPen(QColor("#000000"))
        pen.setWidth(6)
        item.setPen(pen)

        canvas_view.get_scene_for_testing().addItem(item)

        # Extract and reload
        paths = canvas_view.serialize_paths()
        canvas_view.clear_map_content()
        canvas_view.load_serialized_paths(paths)

        # Verify
        scene = canvas_view.get_scene_for_testing()
        loaded_items = [i for i in scene.items() if isinstance(i, QGraphicsPathItem)]
        loaded_path = loaded_items[0].path()

        # Check coordinates match
        for i in range(original_path.elementCount()):
            orig_elem = original_path.elementAt(i)
            loaded_elem = loaded_path.elementAt(i)
            assert abs(orig_elem.x - loaded_elem.x) < 0.01
            assert abs(orig_elem.y - loaded_elem.y) < 0.01

    def test_round_trip_preserves_color(self, canvas_view):
        """
        Stroke color should survive a save/load round-trip.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(100, 100)

        item = QGraphicsPathItem(path)
        original_color = QColor(128, 64, 32)
        pen = QPen(original_color)
        pen.setWidth(6)
        item.setPen(pen)

        canvas_view.get_scene_for_testing().addItem(item)

        # Round-trip
        paths = canvas_view.serialize_paths()
        canvas_view.clear_map_content()
        canvas_view.load_serialized_paths(paths)

        # Verify
        scene = canvas_view.get_scene_for_testing()
        loaded_items = [i for i in scene.items() if isinstance(i, QGraphicsPathItem)]
        loaded_color = loaded_items[0].pen().color()

        assert loaded_color.red() == original_color.red()
        assert loaded_color.green() == original_color.green()
        assert loaded_color.blue() == original_color.blue()

    def test_round_trip_preserves_width(self, canvas_view):
        """
        Stroke width should survive a save/load round-trip.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(100, 100)

        item = QGraphicsPathItem(path)
        pen = QPen()
        pen.setWidth(15)
        item.setPen(pen)

        canvas_view.get_scene_for_testing().addItem(item)

        # Round-trip
        paths = canvas_view.serialize_paths()
        canvas_view.clear_map_content()
        canvas_view.load_serialized_paths(paths)

        # Verify
        scene = canvas_view.get_scene_for_testing()
        loaded_items = [i for i in scene.items() if isinstance(i, QGraphicsPathItem)]
        loaded_width = loaded_items[0].pen().width()

        assert loaded_width == 15


# =============================================================================
# Phase 4: Clear Canvas Tests
# =============================================================================

class TestClearMapContent:
    """Tests for CanvasView.clear_map_content()."""

    def test_clear_removes_path_items(self, canvas_view):
        """
        clear_map_content() should remove all QGraphicsPathItems.
        """
        # Add some paths
        for _ in range(3):
            path = QPainterPath()
            path.moveTo(0, 0)
            path.lineTo(10, 10)
            item = QGraphicsPathItem(path)
            canvas_view.get_scene_for_testing().addItem(item)

        # Verify paths exist
        scene = canvas_view.get_scene_for_testing()
        assert len([i for i in scene.items() if isinstance(i, QGraphicsPathItem)]) == 3

        # Clear
        canvas_view.clear_map_content()

        # Verify paths are gone
        assert len([i for i in scene.items() if isinstance(i, QGraphicsPathItem)]) == 0

    def test_clear_removes_background(self, canvas_view, valid_image_file):
        """
        clear_map_content() should also remove the background image.
        """
        # Load a background image
        canvas_view.load_image(valid_image_file)

        # Verify background exists
        scene = canvas_view.get_scene_for_testing()
        pixmap_items = [i for i in scene.items() if isinstance(i, QGraphicsPixmapItem)]
        assert len(pixmap_items) == 1

        # Clear
        canvas_view.clear_map_content()

        # Background should be gone
        pixmap_items = [i for i in scene.items() if isinstance(i, QGraphicsPixmapItem)]
        assert len(pixmap_items) == 0

    def test_clear_resets_background_path(self, canvas_view, valid_image_file):
        """
        clear_map_content() should reset the background image path to None.
        """
        # Load a background image
        canvas_view.load_image(valid_image_file)
        assert canvas_view.get_background_image_path() == valid_image_file

        # Clear
        canvas_view.clear_map_content()

        # Background path should be None
        assert canvas_view.get_background_image_path() is None


# =============================================================================
# Phase 4: Background Path Tests
# =============================================================================

class TestGetBackgroundImagePath:
    """Tests for CanvasView.get_background_image_path()."""

    def test_returns_none_when_no_background(self, canvas_view):
        """
        get_background_image_path() should return None when no image is loaded.
        """
        result = canvas_view.get_background_image_path()
        assert result is None

    def test_returns_path_when_loaded(self, canvas_view, valid_image_file):
        """
        get_background_image_path() should return the loaded image path.
        """
        canvas_view.load_image(valid_image_file)

        result = canvas_view.get_background_image_path()
        assert result == valid_image_file


class TestSetBackgroundImagePath:
    """Tests for CanvasView.set_background_image_path()."""

    def test_set_background_image_path_updates_value(self, canvas_view):
        """
        set_background_image_path() should update the stored path.
        """
        canvas_view.set_background_image_path("/some/path/image.png")
        assert canvas_view.get_background_image_path() == "/some/path/image.png"

    def test_set_background_image_path_accepts_none(self, canvas_view, valid_image_file):
        """
        set_background_image_path() should accept None to clear the path.
        """
        canvas_view.load_image(valid_image_file)
        assert canvas_view.get_background_image_path() is not None

        canvas_view.set_background_image_path(None)
        assert canvas_view.get_background_image_path() is None
