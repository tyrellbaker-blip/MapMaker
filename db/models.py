"""
SQLAlchemy ORM models for the Map Maker application.

This module defines the database schema using SQLAlchemy's declarative system.
Each class represents a table in the SQLite database, and instances of these
classes represent rows in those tables.

Phase 4: Database Schema

Architecture:
    Map -> Layer -> Elements

    Every drawable/editable element belongs to a layer.
    Every layer belongs to a map.

Tables:
    - maps: Root entity for saved maps
    - layers: Grouping containers within maps
    - paths: Freehand pen strokes (Phase 2/3)
    - symbols: Map markers/icons (future)
    - text_labels: Text annotations (future)
    - regions: Filled polygons (future)
    - user_icons: Custom uploaded icons (future)

Authors: Ty Baker, Everett Loxley
Created: March 19, 2026
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base


# Base class for all models
Base = declarative_base()


def _utc_now():
    """Return current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


# =============================================================================
# Phase 4: Map Model
# =============================================================================

class Map(Base):
    """
    Represents a saved map document.

    The Map is the root entity that contains layers, which in turn contain
    all map elements. When a user saves their work, a Map record is created
    (or updated) with its associated layers and elements.

    Attributes:
        id: Unique identifier for the map.
        name: Display name of the map (shown in save/load dialogs).
        background_image_path: File path to the background image, if any.
        width: Canvas width in pixels (nullable, for future use).
        height: Canvas height in pixels (nullable, for future use).
        created_at: When the map was first created.
        updated_at: When the map was last modified.
        layers: Collection of Layer objects belonging to this map.
    """
    __tablename__ = 'maps'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    background_image_path = Column(String(1024), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationships
    # cascade="all, delete-orphan" means when a Map is deleted, all its layers
    # are also deleted automatically
    layers = relationship(
        "Layer",
        back_populates="map",
        cascade="all, delete-orphan",
        order_by="Layer.order_index"
    )

    def __repr__(self):
        return f"<Map(id={self.id}, name='{self.name}')>"


# =============================================================================
# Phase 4: Layer Model
# =============================================================================

class Layer(Base):
    """
    Represents a grouping layer for organizing map elements.

    Layers allow users to organize their map elements into logical groups
    that can be shown/hidden, locked, or reordered. All drawable elements
    must belong to a layer.

    For Phase 4, a single "Default Layer" is used for all content.

    Attributes:
        id: Unique identifier for the layer.
        map_id: Foreign key linking to the parent Map.
        name: Display name of the layer.
        order_index: Stacking order (lower = rendered first/behind).
        is_visible: Whether the layer is currently visible.
        is_locked: Whether the layer is locked for editing.
        created_at: When the layer was created.
        updated_at: When the layer was last modified.
        map: Reference to the parent Map object.
        paths: Collection of Path objects on this layer.
        symbols: Collection of Symbol objects on this layer.
        text_labels: Collection of TextLabel objects on this layer.
        regions: Collection of Region objects on this layer.
        user_icons: Collection of UserIcon objects on this layer.
    """
    __tablename__ = 'layers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    map_id = Column(Integer, ForeignKey('maps.id'), nullable=False)
    name = Column(String(255), nullable=False, default="Default Layer")
    order_index = Column(Integer, nullable=False, default=0)
    is_visible = Column(Boolean, nullable=False, default=True)
    is_locked = Column(Boolean, nullable=False, default=False)
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationship back to the parent Map
    map = relationship("Map", back_populates="layers")

    # Relationships to elements (all cascade delete with the layer)
    paths = relationship(
        "Path",
        back_populates="layer",
        cascade="all, delete-orphan"
    )
    symbols = relationship(
        "Symbol",
        back_populates="layer",
        cascade="all, delete-orphan"
    )
    text_labels = relationship(
        "TextLabel",
        back_populates="layer",
        cascade="all, delete-orphan"
    )
    regions = relationship(
        "Region",
        back_populates="layer",
        cascade="all, delete-orphan"
    )
    user_icons = relationship(
        "UserIcon",
        back_populates="layer",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Layer(id={self.id}, name='{self.name}', map_id={self.map_id})>"


# =============================================================================
# Phase 4: Path Model (Freehand Strokes)
# =============================================================================

class Path(Base):
    """
    Represents a freehand stroke drawn on the canvas.

    Each stroke is stored as a series of point coordinates that can be used
    to reconstruct a QPainterPath. The points_json field contains a JSON-encoded
    list of {x, y} coordinates.

    Points format:
        [
            {"x": 100.0, "y": 100.0},
            {"x": 105.5, "y": 102.3},
            {"x": 110.0, "y": 105.0},
            ...
        ]

    Attributes:
        id: Unique identifier for the path.
        layer_id: Foreign key linking to the parent Layer.
        stroke_color: Stroke color as hex string (e.g., "#FF0000" for red).
        stroke_width: Stroke width in pixels.
        points_json: JSON string containing the ordered point list.
        created_at: When the path was created.
        updated_at: When the path was last modified.
        layer: Reference to the parent Layer object.
    """
    __tablename__ = 'paths'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    stroke_color = Column(String(9), nullable=False, default="#000000")
    stroke_width = Column(Float, nullable=False, default=6.0)
    points_json = Column(Text, nullable=False)
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationship back to the parent Layer
    layer = relationship("Layer", back_populates="paths")

    def __repr__(self):
        return f"<Path(id={self.id}, layer_id={self.layer_id}, color='{self.stroke_color}')>"


# =============================================================================
# Phase 4: Symbol Model (Future)
# =============================================================================

class Symbol(Base):
    """
    Represents a map symbol/marker placed on the canvas.

    Symbols are predefined icons (like map markers, POI icons, etc.)
    that can be placed at specific locations on the map.

    NOTE: UI for this model will be added in a future phase.

    Attributes:
        id: Unique identifier for the symbol.
        layer_id: Foreign key linking to the parent Layer.
        asset_path: Path to the symbol asset file.
        x: X coordinate on the canvas.
        y: Y coordinate on the canvas.
        scale: Scale factor for the symbol.
        rotation: Rotation angle in degrees.
        created_at: When the symbol was created.
        updated_at: When the symbol was last modified.
        layer: Reference to the parent Layer object.
    """
    __tablename__ = 'symbols'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    asset_path = Column(String(1024), nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    scale = Column(Float, nullable=False, default=1.0)
    rotation = Column(Float, nullable=False, default=0.0)
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationship back to the parent Layer
    layer = relationship("Layer", back_populates="symbols")

    def __repr__(self):
        return f"<Symbol(id={self.id}, asset_path='{self.asset_path}')>"


# =============================================================================
# Phase 4: TextLabel Model (Future)
# =============================================================================

class TextLabel(Base):
    """
    Represents a text annotation on the map.

    Text labels allow users to add names, descriptions, or other text
    to specific locations on their map.

    NOTE: UI for this model will be added in a future phase.

    Attributes:
        id: Unique identifier for the text label.
        layer_id: Foreign key linking to the parent Layer.
        text: The text content.
        x: X coordinate on the canvas.
        y: Y coordinate on the canvas.
        font_family: Font family name.
        font_size: Font size in points.
        color: Text color as hex string.
        created_at: When the text label was created.
        updated_at: When the text label was last modified.
        layer: Reference to the parent Layer object.
    """
    __tablename__ = 'text_labels'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    text = Column(Text, nullable=False)
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    font_family = Column(String(128), nullable=False, default="Arial")
    font_size = Column(Float, nullable=False, default=12.0)
    color = Column(String(9), nullable=False, default="#000000")
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationship back to the parent Layer
    layer = relationship("Layer", back_populates="text_labels")

    def __repr__(self):
        return f"<TextLabel(id={self.id}, text='{self.text[:20]}...')>"


# =============================================================================
# Phase 4: Region Model (Future)
# =============================================================================

class Region(Base):
    """
    Represents a filled area/polygon on the map.

    Regions are closed shapes that can be filled with color and used
    to mark territories, zones, or areas of interest.

    NOTE: UI for this model will be added in a future phase.

    Attributes:
        id: Unique identifier for the region.
        layer_id: Foreign key linking to the parent Layer.
        name: Display name for the region.
        fill_color: Fill color as hex string.
        stroke_color: Stroke/border color as hex string.
        stroke_width: Stroke/border width in pixels.
        points_json: JSON-encoded polygon vertex coordinates.
        created_at: When the region was created.
        updated_at: When the region was last modified.
        layer: Reference to the parent Layer object.
    """
    __tablename__ = 'regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    name = Column(String(255), nullable=False, default="")
    fill_color = Column(String(9), nullable=False, default="#CCCCCC")
    stroke_color = Column(String(9), nullable=False, default="#000000")
    stroke_width = Column(Float, nullable=False, default=1.0)
    points_json = Column(Text, nullable=False)
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationship back to the parent Layer
    layer = relationship("Layer", back_populates="regions")

    def __repr__(self):
        return f"<Region(id={self.id}, name='{self.name}')>"


# =============================================================================
# Phase 4: UserIcon Model (Future)
# =============================================================================

class UserIcon(Base):
    """
    Represents a custom icon uploaded by the user.

    User icons are custom images that users can upload and place on
    their maps, in addition to the built-in symbols.

    NOTE: UI for this model will be added in a future phase.

    Attributes:
        id: Unique identifier for the user icon.
        layer_id: Foreign key linking to the parent Layer.
        label: Display label for the icon.
        x: X coordinate on the canvas.
        y: Y coordinate on the canvas.
        icon_path: Path to the uploaded icon file (nullable).
        created_at: When the user icon was created.
        updated_at: When the user icon was last modified.
        layer: Reference to the parent Layer object.
    """
    __tablename__ = 'user_icons'

    id = Column(Integer, primary_key=True, autoincrement=True)
    layer_id = Column(Integer, ForeignKey('layers.id'), nullable=False)
    label = Column(String(255), nullable=False, default="")
    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)
    icon_path = Column(String(1024), nullable=True)
    created_at = Column(String(64), default=lambda: _utc_now().isoformat(), nullable=False)
    updated_at = Column(String(64), default=lambda: _utc_now().isoformat(),
                       onupdate=lambda: _utc_now().isoformat(), nullable=False)

    # Relationship back to the parent Layer
    layer = relationship("Layer", back_populates="user_icons")

    def __repr__(self):
        return f"<UserIcon(id={self.id}, label='{self.label}')>"
