"""
Main window module for the Map Maker application.
Provides the primary application window with toolbar and canvas.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QToolBar, QFileDialog, QApplication,
    QColorDialog, QComboBox, QLabel
)
from PyQt6.QtGui import QAction, QColor, QPixmap, QIcon
from PyQt6.QtCore import Qt

from canvas.canvas_view import CanvasView


class MainWindow(QMainWindow):
    """
    Main application window for the Map Maker.

    Features:
    - Toolbar with image upload functionality
    - Canvas view for displaying and interacting with maps
    - Centered window positioning
    - Drawing tools: color picker, brush size, pen tool
    """

    # Default window dimensions
    DEFAULT_WIDTH = 1200
    DEFAULT_HEIGHT = 800

    # Supported image file formats
    IMAGE_FILTER = "Images (*.png *.jpg *.jpeg);;PNG Files (*.png);;JPEG Files (*.jpg *.jpeg)"

    # Brush size options: (display name, pixel size)
    BRUSH_SIZES = [
        ("Small (2px)", 2),
        ("Medium (6px)", 6),
        ("Large (12px)", 12),
    ]

    def __init__(self):
        super().__init__()

        # Current drawing color (default: black)
        self._current_color = QColor(0, 0, 0)

        # Reference to pen tool action for toggle state
        self._pen_action = None

        # Reference to color picker button for updating its icon
        self._color_action = None

        # Set window properties
        self._setup_window()

        # Create the canvas view (central widget)
        self._setup_canvas()

        # Create the toolbar
        self._setup_toolbar()

        # Center window on screen
        self._center_on_screen()

    def _setup_window(self):
        """Configure the main window properties."""
        self.setWindowTitle("Map Maker")
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

    def _setup_canvas(self):
        """Create and set the canvas view as the central widget."""
        self._canvas_view = CanvasView(self)
        self.setCentralWidget(self._canvas_view)

    def _setup_toolbar(self):
        """Create the main toolbar with actions."""
        # Create toolbar
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        # Create upload action
        upload_action = QAction("Upload Image", self)
        upload_action.setStatusTip("Upload a background image for the map")
        upload_action.triggered.connect(self._on_upload_clicked)
        toolbar.addAction(upload_action)

        # Add separator between file operations and drawing tools
        toolbar.addSeparator()

        # Create pen tool action (toggleable)
        self._pen_action = QAction("Pen Tool", self)
        self._pen_action.setStatusTip("Activate pen tool to draw on the canvas")
        self._pen_action.setCheckable(True)
        self._pen_action.toggled.connect(self._on_pen_tool_toggled)
        toolbar.addAction(self._pen_action)

        # Create color picker action with colored icon
        self._color_action = QAction("Color", self)
        self._color_action.setStatusTip("Choose stroke color")
        self._color_action.triggered.connect(self._on_color_picker_clicked)
        self._update_color_icon()
        toolbar.addAction(self._color_action)

        # Create brush size selector
        toolbar.addWidget(QLabel("  Brush: "))
        self._brush_combo = QComboBox()
        for name, size in self.BRUSH_SIZES:
            self._brush_combo.addItem(name, size)
        # Set default to Medium (index 1)
        self._brush_combo.setCurrentIndex(1)
        self._brush_combo.currentIndexChanged.connect(self._on_brush_size_changed)
        toolbar.addWidget(self._brush_combo)

    def _center_on_screen(self):
        """Center the window on the primary screen."""
        # Get the primary screen geometry
        screen = QApplication.primaryScreen()
        if screen is not None:
            screen_geometry = screen.availableGeometry()

            # Calculate center position
            x = (screen_geometry.width() - self.width()) // 2
            y = (screen_geometry.height() - self.height()) // 2

            # Move window to center
            self.move(screen_geometry.x() + x, screen_geometry.y() + y)

    def _on_upload_clicked(self):
        """Handle the upload button click event."""
        # Open file dialog filtered to image types
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Map Background Image",
            "",
            self.IMAGE_FILTER
        )

        # If user selected a file, pass it to the canvas
        if file_path:
            self._canvas_view.load_image(file_path)

    def _on_pen_tool_toggled(self, checked: bool):
        """
        Handle pen tool button toggle.

        Args:
            checked: True if pen tool is now active, False if deactivated
        """
        self._canvas_view.set_drawing_mode(checked)

    def _on_color_picker_clicked(self):
        """Handle color picker button click."""
        # Open color dialog with current color as default
        color = QColorDialog.getColor(
            self._current_color,
            self,
            "Select Stroke Color"
        )

        # If user selected a valid color (didn't cancel)
        if color.isValid():
            self._current_color = color
            self._canvas_view.set_stroke_color(color)
            self._update_color_icon()

    def _update_color_icon(self):
        """Update the color picker button icon to show current color."""
        # Create a small colored square as the icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(self._current_color)
        self._color_action.setIcon(QIcon(pixmap))

    def _on_brush_size_changed(self, index: int):
        """
        Handle brush size combo box selection change.

        Args:
            index: Index of selected item in combo box
        """
        # Get the pixel size associated with the selected item
        size = self._brush_combo.itemData(index)
        if size is not None:
            self._canvas_view.set_brush_size(size)
