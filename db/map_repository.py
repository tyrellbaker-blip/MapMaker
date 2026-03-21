"""
Map repository for the Map Maker application.

This module provides a high-level API for saving and loading maps. It
encapsulates all database operations behind a clean interface, so the
rest of the application doesn't need to know about SQLAlchemy details.

Phase 4: Map persistence with default layer architecture.

Architecture:
    - All content is stored on a "Default Layer" (name="Default Layer", order_index=0)
    - Paths belong to layers, layers belong to maps
    - Repository returns plain Python data structures, not Qt or ORM objects

Authors: Ty Baker, Everett Loxley
Created: March 19, 2026
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from db.database import get_session
from db.models import Map, Layer, Path


# =============================================================================
# Phase 4: Constants
# =============================================================================

DEFAULT_LAYER_NAME = "Default Layer"
DEFAULT_LAYER_ORDER_INDEX = 0


class MapRepository:
    """
    Repository for map persistence operations.

    This class provides methods for saving, loading, and listing maps from
    the database. It handles all database session management internally,
    so callers don't need to worry about commits or cleanup.

    The repository works with dictionaries for input/output, making it
    easy to interface with the rest of the application without tight
    coupling to SQLAlchemy models.

    Path Data Format (input/output):
        [
            {
                "points": [{"x": 10.0, "y": 20.0}, {"x": 15.0, "y": 25.0}],
                "stroke_color": "#FF0000",
                "stroke_width": 6.0
            }
        ]
    """

    # =========================================================================
    # Phase 4: Save Operations
    # =========================================================================

    def save_map(
        self,
        name: str,
        paths: List[Dict[str, Any]],
        background_image_path: Optional[str] = None,
        map_id: Optional[int] = None
    ) -> int:
        """
        Save a map to the database.

        If map_id is provided and the map exists, updates it. If map_id is
        provided but the map doesn't exist (was deleted), treats it as a
        new save. If map_id is None, creates a new map.

        All paths are stored on the default layer.

        Args:
            name: Display name for the map.
            paths: List of path dictionaries, each containing:
                - points: List of {x, y} coordinates
                - stroke_color: Hex color string (e.g., "#FF0000")
                - stroke_width: Stroke width in pixels
            background_image_path: Optional file path to background image.
            map_id: Optional ID of existing map to update.

        Returns:
            The ID of the saved map.
        """
        session = get_session()
        try:
            map_obj = None

            # Try to find existing map if map_id provided
            if map_id is not None:
                map_obj = session.query(Map).filter(Map.id == map_id).first()

            if map_obj is not None:
                # Update existing map
                map_obj.name = name
                map_obj.background_image_path = background_image_path
                map_obj.updated_at = datetime.now(timezone.utc).isoformat()

                # Get or create default layer
                default_layer = self._get_or_create_default_layer(session, map_obj)

                # Clear existing paths on the default layer and add new ones
                session.query(Path).filter(Path.layer_id == default_layer.id).delete()
                self._add_paths_to_layer(session, default_layer, paths)
            else:
                # Create new map (either map_id was None or map was deleted)
                map_obj = Map(
                    name=name,
                    background_image_path=background_image_path
                )
                session.add(map_obj)
                session.flush()  # Generate map_obj.id

                # Create default layer
                default_layer = Layer(
                    map_id=map_obj.id,
                    name=DEFAULT_LAYER_NAME,
                    order_index=DEFAULT_LAYER_ORDER_INDEX
                )
                session.add(default_layer)
                session.flush()

                # Add paths
                self._add_paths_to_layer(session, default_layer, paths)

            session.commit()
            return map_obj.id

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _get_or_create_default_layer(self, session, map_obj: Map) -> Layer:
        """
        Get the default layer for a map, creating it if it doesn't exist.

        Args:
            session: The active database session.
            map_obj: The Map object.

        Returns:
            The default Layer object.
        """
        default_layer = session.query(Layer).filter(
            Layer.map_id == map_obj.id,
            Layer.name == DEFAULT_LAYER_NAME,
            Layer.order_index == DEFAULT_LAYER_ORDER_INDEX
        ).first()

        if default_layer is None:
            default_layer = Layer(
                map_id=map_obj.id,
                name=DEFAULT_LAYER_NAME,
                order_index=DEFAULT_LAYER_ORDER_INDEX
            )
            session.add(default_layer)
            session.flush()

        return default_layer

    def _add_paths_to_layer(
        self,
        session,
        layer: Layer,
        paths: List[Dict[str, Any]]
    ) -> None:
        """
        Add path records to a layer.

        Args:
            session: The active database session.
            layer: The Layer object to add paths to.
            paths: List of path dictionaries with points, stroke_color, stroke_width.
        """
        for path_dict in paths:
            points = path_dict.get("points", [])

            # Convert points to JSON string
            points_json = json.dumps(points)

            path = Path(
                layer_id=layer.id,
                points_json=points_json,
                stroke_color=path_dict.get("stroke_color", "#000000"),
                stroke_width=path_dict.get("stroke_width", 6.0)
            )
            session.add(path)

    # =========================================================================
    # Phase 4: Load Operations
    # =========================================================================

    def load_map(self, map_id: int) -> Optional[Dict[str, Any]]:
        """
        Load a map from the database.

        Returns a dictionary containing all map data, including paths from
        the default layer. Returns None if the map doesn't exist.

        Args:
            map_id: The ID of the map to load.

        Returns:
            Dictionary containing:
                - id: Map ID
                - name: Map name
                - background_image_path: Path to background image (or None)
                - width: Canvas width (or None)
                - height: Canvas height (or None)
                - paths: List of path dictionaries from the default layer

            Returns None if map_id doesn't exist.
        """
        session = get_session()
        try:
            map_obj = session.query(Map).filter(Map.id == map_id).first()
            if map_obj is None:
                return None

            # Get default layer
            default_layer = session.query(Layer).filter(
                Layer.map_id == map_obj.id,
                Layer.name == DEFAULT_LAYER_NAME,
                Layer.order_index == DEFAULT_LAYER_ORDER_INDEX
            ).first()

            # Extract paths from default layer
            paths = []
            if default_layer is not None:
                for path_obj in default_layer.paths:
                    paths.append(self._path_to_dict(path_obj))

            return {
                "id": map_obj.id,
                "name": map_obj.name,
                "background_image_path": map_obj.background_image_path,
                "width": map_obj.width,
                "height": map_obj.height,
                "paths": paths
            }

        finally:
            session.close()

    def _path_to_dict(self, path_obj: Path) -> Dict[str, Any]:
        """
        Convert a Path ORM object to a dictionary.

        Args:
            path_obj: The Path ORM object.

        Returns:
            Dictionary with points, stroke_color, stroke_width.
        """
        try:
            points = json.loads(path_obj.points_json)
        except (json.JSONDecodeError, TypeError):
            points = []

        return {
            "points": points,
            "stroke_color": path_obj.stroke_color,
            "stroke_width": path_obj.stroke_width
        }

    # =========================================================================
    # Phase 4: List Operations
    # =========================================================================

    def list_maps(self) -> List[Dict[str, Any]]:
        """
        Get a list of all saved maps.

        Returns summary information about each map (without loading all
        path data). This is efficient for displaying in a "Load Map" dialog.

        Returns:
            List of dictionaries, each containing:
                - id: Map ID
                - name: Map name
                - path_count: Number of paths on the default layer
        """
        session = get_session()
        try:
            maps = session.query(Map).order_by(Map.updated_at.desc()).all()

            result = []
            for map_obj in maps:
                # Count paths on default layer
                default_layer = session.query(Layer).filter(
                    Layer.map_id == map_obj.id,
                    Layer.name == DEFAULT_LAYER_NAME,
                    Layer.order_index == DEFAULT_LAYER_ORDER_INDEX
                ).first()

                path_count = 0
                if default_layer is not None:
                    path_count = session.query(Path).filter(
                        Path.layer_id == default_layer.id
                    ).count()

                result.append({
                    "id": map_obj.id,
                    "name": map_obj.name,
                    "path_count": path_count
                })

            return result

        finally:
            session.close()

    # =========================================================================
    # Phase 4: Delete Operations
    # =========================================================================

    def delete_map(self, map_id: int) -> bool:
        """
        Delete a map and all its associated data.

        This permanently removes the map, its layers, and all layer elements
        from the database. The cascade delete in the model definitions ensures
        all related data is also deleted.

        Args:
            map_id: The ID of the map to delete.

        Returns:
            True if the map was deleted, False if it didn't exist.
        """
        session = get_session()
        try:
            map_obj = session.query(Map).filter(Map.id == map_id).first()
            if map_obj is None:
                return False

            session.delete(map_obj)
            session.commit()
            return True

        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # =========================================================================
    # Phase 4: Utility Methods
    # =========================================================================

    def map_exists(self, map_id: int) -> bool:
        """
        Check if a map exists in the database.

        Args:
            map_id: The ID of the map to check.

        Returns:
            True if the map exists, False otherwise.
        """
        session = get_session()
        try:
            return session.query(Map).filter(Map.id == map_id).count() > 0
        finally:
            session.close()
