"""
Shared pytest fixtures for the Map Maker test suite.

This module provides reusable fixtures for testing the Map Maker application.
Fixtures create test objects and temporary resources that multiple test modules
can use, reducing code duplication and ensuring consistent test setup.

Key fixtures:
    - qtbot: Provided by pytest-qt for Qt widget testing
    - main_window: A fully constructed MainWindow instance
    - canvas_view: A standalone CanvasView instance
    - canvas_view_with_undo_stack: A CanvasView with an undo stack attached
    - valid_image_file: A temporary valid PNG image file
    - invalid_image_file: A temporary file that is not a valid image
    - sample_scene: A QGraphicsScene for isolated command testing
    - test_db: A temporary SQLite database for Phase 4 testing
    - map_repository: A MapRepository connected to the test database
"""

import pytest
import tempfile
import os
from PIL import Image

from PyQt6.QtWidgets import QGraphicsScene
from PyQt6.QtGui import QUndoStack, QColor

from ui.main_window import MainWindow
from canvas.canvas_view import CanvasView
from db.database import init_database, get_session
from db.map_repository import MapRepository
from db.models import Base


# =============================================================================
# Window and Widget Fixtures
# =============================================================================

@pytest.fixture
def main_window(qtbot):
    """
    Create a fully initialized MainWindow instance.

    The MainWindow includes the toolbar, canvas view, and undo stack.
    This fixture is used for integration tests that need the complete
    application UI.

    Args:
        qtbot: pytest-qt's bot for Qt widget testing

    Yields:
        MainWindow: A fully constructed main window instance
    """
    window = MainWindow()
    qtbot.addWidget(window)
    yield window


@pytest.fixture
def canvas_view(qtbot):
    """
    Create a standalone CanvasView instance without an undo stack.

    This fixture is useful for testing canvas behavior in isolation,
    especially for Phase 1 and Phase 2 features that don't require
    undo/redo integration.

    Args:
        qtbot: pytest-qt's bot for Qt widget testing

    Yields:
        CanvasView: A canvas view without an undo stack
    """
    view = CanvasView()
    qtbot.addWidget(view)
    yield view


@pytest.fixture
def canvas_view_with_undo_stack(qtbot):
    """
    Create a CanvasView instance with an attached undo stack.

    This fixture is used for Phase 3 tests that require undo/redo
    functionality. The undo stack is created and attached just like
    MainWindow would do it.

    Args:
        qtbot: pytest-qt's bot for Qt widget testing

    Yields:
        tuple: (CanvasView, QUndoStack) - the canvas and its undo stack
    """
    view = CanvasView()
    undo_stack = QUndoStack()
    view.set_undo_stack(undo_stack)
    qtbot.addWidget(view)
    yield view, undo_stack


# =============================================================================
# Scene Fixtures (for isolated command testing)
# =============================================================================

@pytest.fixture
def sample_scene():
    """
    Create a standalone QGraphicsScene for testing commands in isolation.

    This fixture is useful for unit testing AddStrokeCommand without
    needing a full CanvasView. It provides a clean scene for each test.

    Yields:
        QGraphicsScene: An empty graphics scene
    """
    scene = QGraphicsScene()
    yield scene


# =============================================================================
# Image File Fixtures
# =============================================================================

@pytest.fixture
def valid_image_file():
    """
    Create a temporary valid PNG image file for testing image loading.

    Creates a small 100x100 red PNG image that can be used to test
    successful image loading paths. The file is automatically cleaned
    up after the test completes.

    Yields:
        str: Path to the temporary image file
    """
    # Create a temporary file that won't be auto-deleted on close
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)

    # Create a simple 100x100 red image using Pillow
    img = Image.new('RGB', (100, 100), color='red')
    img.save(path, 'PNG')

    yield path

    # Cleanup: remove the temporary file
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def valid_large_image_file():
    """
    Create a temporary large image file that exceeds MAX_IMAGE_SIZE.

    This fixture creates a 5000x5000 image to test the automatic
    resizing behavior when loading oversized images.

    Yields:
        str: Path to the temporary large image file
    """
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)

    # Create a 5000x5000 image (exceeds the 4000x4000 limit)
    img = Image.new('RGB', (5000, 5000), color='blue')
    img.save(path, 'PNG')

    yield path

    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def valid_rgba_image_file():
    """
    Create a temporary RGBA image file with transparency.

    This fixture tests the alpha channel preservation code path
    in the image loading logic.

    Yields:
        str: Path to the temporary RGBA image file
    """
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)

    # Create an RGBA image with semi-transparent pixels
    img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 128))
    img.save(path, 'PNG')

    yield path

    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def invalid_image_file():
    """
    Create a temporary file that is not a valid image.

    This fixture creates a text file with a .png extension to test
    the error handling when attempting to load invalid image files.

    Yields:
        str: Path to the invalid image file
    """
    fd, path = tempfile.mkstemp(suffix='.png')
    os.close(fd)

    # Write non-image content to the file
    with open(path, 'w') as f:
        f.write("This is not a valid image file")

    yield path

    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def nonexistent_image_path():
    """
    Provide a path to a file that does not exist.

    This fixture is used to test error handling when attempting
    to load a file that doesn't exist.

    Returns:
        str: Path to a nonexistent file
    """
    return "/nonexistent/path/to/image.png"


# =============================================================================
# Color Fixtures
# =============================================================================

@pytest.fixture
def test_color():
    """
    Provide a test color for stroke color testing.

    Returns:
        QColor: A red color for testing
    """
    return QColor(255, 0, 0)  # Red


# =============================================================================
# Phase 4: Database Fixtures
# =============================================================================

@pytest.fixture
def test_db():
    """
    Create a temporary SQLite database for testing.

    This fixture creates a fresh database in a temporary file that is
    cleaned up after the test completes. Each test gets its own
    isolated database.

    Yields:
        str: Path to the temporary database file
    """
    # Create a temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)

    # Initialize the database with this path
    init_database(db_path)

    yield db_path

    # Cleanup: remove the temporary database file
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture
def map_repository(test_db):
    """
    Create a MapRepository connected to the test database.

    This fixture depends on test_db to ensure the database is initialized.
    Each test gets a fresh repository and database.

    Args:
        test_db: The test database path fixture

    Yields:
        MapRepository: A repository for map persistence operations
    """
    return MapRepository()


@pytest.fixture
def sample_path_data():
    """
    Provide sample path data for testing serialization.

    Returns a list of path dictionaries in the format expected by
    the MapRepository and CanvasView. Uses ordered point coordinates
    (not command streams).

    Format:
        {
            "points": [{"x": float, "y": float}, ...],
            "stroke_color": "#RRGGBB",
            "stroke_width": float
        }

    Returns:
        list: Sample path data with two strokes
    """
    return [
        {
            "points": [
                {"x": 0.0, "y": 0.0},
                {"x": 100.0, "y": 100.0},
                {"x": 200.0, "y": 50.0}
            ],
            "stroke_color": "#FF0000",
            "stroke_width": 6.0
        },
        {
            "points": [
                {"x": 50.0, "y": 50.0},
                {"x": 150.0, "y": 150.0}
            ],
            "stroke_color": "#0000FF",
            "stroke_width": 12.0
        }
    ]
