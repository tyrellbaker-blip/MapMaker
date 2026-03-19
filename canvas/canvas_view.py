"""
Canvas view module for the Map Maker application.
Provides the main canvas where the map background image is displayed.
Supports freehand drawing on top of the background image.

Authors: Ty Baker, Everett Loxley
Created: March 19, 2026

Features:
    - Background image loading with Pillow validation
    - Automatic resizing for images exceeding 4000x4000 pixels
    - Mouse wheel zoom (0.1x to 10x range)
    - Freehand drawing with customizable color and brush size
    - Strokes stored as QGraphicsPathItems on the scene
"""

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QMessageBox,
    QGraphicsPathItem
)
from PyQt6.QtGui import QPixmap, QImage, QPainterPath, QPen, QColor
from PyQt6.QtCore import Qt
from PIL import Image
import io


class CanvasView(QGraphicsView):
    """
    Custom QGraphicsView that displays a background image for map creation.

    Features:
    - Loads and validates images using Pillow
    - Resizes images exceeding 4000x4000 while preserving aspect ratio
    - Displays image as a locked, non-selectable background
    - Supports mouse wheel zoom with configurable bounds
    - Freehand drawing with configurable color and brush size
    """

    # Zoom constraints
    MIN_ZOOM = 0.1
    MAX_ZOOM = 10.0

    # Maximum image dimensions
    MAX_IMAGE_SIZE = 4000

    # Default drawing settings
    DEFAULT_STROKE_COLOR = QColor(0, 0, 0)  # Black
    DEFAULT_BRUSH_SIZE = 6  # Medium

    def __init__(self, parent=None):
        super().__init__(parent)

        # Create and set the graphics scene
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

        # Store reference to the background image item
        self._background_item = None

        # Track current zoom level (1.0 = 100%)
        self._current_zoom = 1.0

        # Drawing mode state
        self._drawing_mode = False
        self._is_drawing = False  # True while actively drawing a stroke

        # Current drawing settings
        self._stroke_color = self.DEFAULT_STROKE_COLOR
        self._brush_size = self.DEFAULT_BRUSH_SIZE

        # Current path being drawn
        self._current_path = None
        self._current_path_item = None

        # Configure view settings
        self._setup_view()

    def _setup_view(self):
        """Configure the graphics view settings."""
        # Enable smooth scaling for better image quality when zooming
        self.setRenderHint(self.renderHints().SmoothPixmapTransform, True)

        # Set anchor point for transformations to mouse position
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # Set resize anchor to keep content centered
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        # Enable scrollbars when content exceeds viewport
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Set a neutral background color
        self.setStyleSheet("QGraphicsView { background-color: #2b2b2b; }")

    def load_image(self, file_path: str) -> bool:
        """
        Load and display an image from the given file path.

        Args:
            file_path: Path to the image file to load

        Returns:
            True if image was loaded successfully, False otherwise
        """
        try:
            # Use Pillow to open and validate the image
            pil_image = Image.open(file_path)

            # Verify the image is valid by loading pixel data
            pil_image.verify()

            # Re-open after verify (verify() can only be called once)
            pil_image = Image.open(file_path)

            # Resize if image exceeds maximum dimensions
            pil_image = self._resize_if_needed(pil_image)

            # Convert PIL image to QPixmap
            pixmap = self._pil_to_qpixmap(pil_image)

            # Display the image on the canvas
            self._set_background_image(pixmap)

            return True

        except Exception as e:
            # Show error dialog for invalid images
            QMessageBox.critical(
                self,
                "Image Load Error",
                f"Failed to load image:\n{str(e)}"
            )
            return False

    def _resize_if_needed(self, image: Image.Image) -> Image.Image:
        """
        Resize image if it exceeds maximum dimensions while preserving aspect ratio.

        Args:
            image: PIL Image to potentially resize

        Returns:
            Original or resized PIL Image
        """
        width, height = image.size

        # Check if resizing is needed
        if width <= self.MAX_IMAGE_SIZE and height <= self.MAX_IMAGE_SIZE:
            return image

        # Calculate new dimensions preserving aspect ratio
        if width > height:
            new_width = self.MAX_IMAGE_SIZE
            new_height = int(height * (self.MAX_IMAGE_SIZE / width))
        else:
            new_height = self.MAX_IMAGE_SIZE
            new_width = int(width * (self.MAX_IMAGE_SIZE / height))

        # Resize using high-quality resampling
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return resized_image

    def _pil_to_qpixmap(self, pil_image: Image.Image) -> QPixmap:
        """
        Convert a PIL Image to a QPixmap.

        Args:
            pil_image: PIL Image to convert

        Returns:
            QPixmap representation of the image
        """
        # Convert to RGB if necessary (handles RGBA, palette mode, etc.)
        if pil_image.mode == "RGBA":
            # Preserve alpha channel
            data = pil_image.tobytes("raw", "RGBA")
            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                QImage.Format.Format_RGBA8888
            )
        else:
            # Convert to RGB for other modes
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")
            data = pil_image.tobytes("raw", "RGB")
            qimage = QImage(
                data,
                pil_image.width,
                pil_image.height,
                QImage.Format.Format_RGB888
            )

        return QPixmap.fromImage(qimage)

    def _set_background_image(self, pixmap: QPixmap):
        """
        Set the background image on the canvas.

        Args:
            pixmap: QPixmap to display as background
        """
        # Remove existing background if present
        if self._background_item is not None:
            self._scene.removeItem(self._background_item)

        # Create pixmap item and add to scene at origin
        self._background_item = QGraphicsPixmapItem(pixmap)
        self._background_item.setPos(0, 0)

        # Lock the item: disable selection and movement
        self._background_item.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsSelectable, False
        )
        self._background_item.setFlag(
            QGraphicsPixmapItem.GraphicsItemFlag.ItemIsMovable, False
        )

        # Add to scene
        self._scene.addItem(self._background_item)

        # Set scene rect to match image bounds
        self._scene.setSceneRect(self._background_item.boundingRect())

        # Reset zoom and fit image in viewport
        self._reset_zoom()
        self._fit_in_view()

    def _reset_zoom(self):
        """Reset the view transform to identity (no zoom)."""
        self.resetTransform()
        self._current_zoom = 1.0

    def _fit_in_view(self):
        """Fit the background image within the viewport."""
        if self._background_item is not None:
            # Fit the scene rect in view while maintaining aspect ratio
            self.fitInView(
                self._background_item.boundingRect(),
                Qt.AspectRatioMode.KeepAspectRatio
            )
            # Update current zoom level based on transform
            self._current_zoom = self.transform().m11()

    def wheelEvent(self, event):
        """
        Handle mouse wheel events for zooming.

        Args:
            event: QWheelEvent containing scroll information
        """
        # Get scroll delta (positive = zoom in, negative = zoom out)
        delta = event.angleDelta().y()

        # Calculate zoom factor (1.15 = 15% zoom per scroll step)
        zoom_factor = 1.15 if delta > 0 else 1 / 1.15

        # Calculate new zoom level
        new_zoom = self._current_zoom * zoom_factor

        # Clamp zoom to min/max bounds
        if new_zoom < self.MIN_ZOOM:
            zoom_factor = self.MIN_ZOOM / self._current_zoom
            new_zoom = self.MIN_ZOOM
        elif new_zoom > self.MAX_ZOOM:
            zoom_factor = self.MAX_ZOOM / self._current_zoom
            new_zoom = self.MAX_ZOOM

        # Only apply zoom if within bounds
        if self.MIN_ZOOM <= new_zoom <= self.MAX_ZOOM:
            self._current_zoom = new_zoom
            self.scale(zoom_factor, zoom_factor)

        # Consume the event
        event.accept()

    # =========================================================================
    # Drawing Mode Methods
    # =========================================================================

    def set_drawing_mode(self, enabled: bool):
        """
        Enable or disable drawing mode.

        Args:
            enabled: True to enable drawing mode, False to disable
        """
        self._drawing_mode = enabled

        # Change cursor to indicate drawing mode
        if enabled:
            self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def is_drawing_mode(self) -> bool:
        """Return whether drawing mode is currently active."""
        return self._drawing_mode

    def set_stroke_color(self, color: QColor):
        """
        Set the color for new strokes.

        Args:
            color: QColor to use for drawing
        """
        self._stroke_color = color

    def get_stroke_color(self) -> QColor:
        """Return the current stroke color."""
        return self._stroke_color

    def set_brush_size(self, size: int):
        """
        Set the brush size for new strokes.

        Args:
            size: Brush width in pixels
        """
        self._brush_size = size

    def get_brush_size(self) -> int:
        """Return the current brush size."""
        return self._brush_size

    # =========================================================================
    # Mouse Event Handlers for Drawing
    # =========================================================================

    def mousePressEvent(self, event):
        """
        Handle mouse press events.
        Starts a new stroke if in drawing mode.

        Args:
            event: QMouseEvent containing mouse information
        """
        if self._drawing_mode and event.button() == Qt.MouseButton.LeftButton:
            # Start a new stroke
            self._is_drawing = True

            # Convert viewport position to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Create a new path starting at the mouse position
            self._current_path = QPainterPath()
            self._current_path.moveTo(scene_pos)

            # Create the path item with current pen settings
            self._current_path_item = QGraphicsPathItem(self._current_path)

            # Configure the pen for this stroke
            pen = QPen(self._stroke_color)
            pen.setWidth(self._brush_size)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            self._current_path_item.setPen(pen)

            # Make the stroke non-selectable and non-movable
            self._current_path_item.setFlag(
                QGraphicsPathItem.GraphicsItemFlag.ItemIsSelectable, False
            )
            self._current_path_item.setFlag(
                QGraphicsPathItem.GraphicsItemFlag.ItemIsMovable, False
            )

            # Add the path item to the scene
            self._scene.addItem(self._current_path_item)

            event.accept()
        else:
            # Pass to parent for default handling (panning, etc.)
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events.
        Extends the current stroke if drawing.

        Args:
            event: QMouseEvent containing mouse information
        """
        if self._is_drawing and self._current_path is not None:
            # Convert viewport position to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Extend the path to the new position
            self._current_path.lineTo(scene_pos)

            # Update the path item with the extended path
            self._current_path_item.setPath(self._current_path)

            event.accept()
        else:
            # Pass to parent for default handling
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events.
        Finalizes the current stroke if drawing.

        Args:
            event: QMouseEvent containing mouse information
        """
        if self._is_drawing and event.button() == Qt.MouseButton.LeftButton:
            # Finalize the stroke
            self._is_drawing = False

            # Clear references to current path (it remains in the scene)
            self._current_path = None
            self._current_path_item = None

            event.accept()
        else:
            # Pass to parent for default handling
            super().mouseReleaseEvent(event)
