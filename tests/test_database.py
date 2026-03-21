"""
Tests for the database module (Phase 4).

This module tests the SQLite persistence layer including:
    - Database initialization
    - ORM models (Map, Layer, Path)
    - MapRepository save/load/list/delete operations
    - Default layer architecture
    - Stale map-id handling

Test coverage:
    Phase 4:
        - Database initialization creates tables
        - Map model can be created and queried
        - Layer model links Map to elements
        - Path model stores and retrieves ordered point data
        - MapRepository.save_map() creates new maps with default layer
        - MapRepository.save_map() updates existing maps
        - MapRepository.save_map() handles stale map_id gracefully
        - MapRepository.load_map() retrieves map data
        - MapRepository.list_maps() returns all maps
        - MapRepository.delete_map() removes maps
        - Path data round-trips correctly through JSON serialization
"""

import json

from db.database import get_session, get_engine
from db.models import Map, Layer, Path
from db.map_repository import MapRepository, DEFAULT_LAYER_NAME, DEFAULT_LAYER_ORDER_INDEX


# =============================================================================
# Phase 4: Database Initialization Tests
# =============================================================================

class TestDatabaseInitialization:
    """Tests for database initialization."""

    def test_database_creates_tables(self, test_db):
        """
        Initializing the database should create the required tables.

        The init_database() call in the fixture should create all tables
        defined in models.py.
        """
        engine = get_engine()
        with engine.connect() as conn:
            # Check that required tables exist
            assert engine.dialect.has_table(conn, 'maps')
            assert engine.dialect.has_table(conn, 'layers')
            assert engine.dialect.has_table(conn, 'paths')

    def test_get_session_returns_valid_session(self, test_db):
        """
        get_session() should return a valid SQLAlchemy session.
        """
        session = get_session()
        try:
            # Session should be usable for queries
            result = session.query(Map).all()
            assert isinstance(result, list)
        finally:
            session.close()


# =============================================================================
# Phase 4: Map Model Tests
# =============================================================================

class TestMapModel:
    """Tests for the Map ORM model."""

    def test_map_can_be_created(self, test_db):
        """
        A Map can be created and saved to the database.
        """
        session = get_session()
        try:
            map_obj = Map(name="Test Map")
            session.add(map_obj)
            session.commit()

            assert map_obj.id is not None
            assert map_obj.name == "Test Map"
        finally:
            session.close()

    def test_map_has_timestamps(self, test_db):
        """
        A Map should have created_at and updated_at timestamps.
        """
        session = get_session()
        try:
            map_obj = Map(name="Timestamp Test")
            session.add(map_obj)
            session.commit()

            assert map_obj.created_at is not None
            assert map_obj.updated_at is not None
        finally:
            session.close()

    def test_map_can_have_background_path(self, test_db):
        """
        A Map can store a background image path.
        """
        session = get_session()
        try:
            map_obj = Map(
                name="Background Test",
                background_image_path="/path/to/image.png"
            )
            session.add(map_obj)
            session.commit()

            # Query back
            loaded_map = session.query(Map).filter(Map.id == map_obj.id).first()
            assert loaded_map.background_image_path == "/path/to/image.png"
        finally:
            session.close()


# =============================================================================
# Phase 4: Layer Model Tests
# =============================================================================

class TestLayerModel:
    """Tests for the Layer ORM model."""

    def test_layer_can_be_created(self, test_db):
        """
        A Layer can be created and associated with a Map.
        """
        session = get_session()
        try:
            map_obj = Map(name="Layer Test Map")
            session.add(map_obj)
            session.flush()

            layer_obj = Layer(
                map_id=map_obj.id,
                name="Test Layer",
                order_index=0
            )
            session.add(layer_obj)
            session.commit()

            assert layer_obj.id is not None
            assert layer_obj.map_id == map_obj.id
            assert layer_obj.name == "Test Layer"
        finally:
            session.close()

    def test_layer_has_visibility_and_lock(self, test_db):
        """
        A Layer should have is_visible and is_locked properties.
        """
        session = get_session()
        try:
            map_obj = Map(name="Layer Props Test")
            session.add(map_obj)
            session.flush()

            layer_obj = Layer(
                map_id=map_obj.id,
                name="Props Layer",
                order_index=0,
                is_visible=True,
                is_locked=False
            )
            session.add(layer_obj)
            session.commit()

            assert layer_obj.is_visible is True
            assert layer_obj.is_locked is False
        finally:
            session.close()

    def test_layers_deleted_with_map(self, test_db):
        """
        Deleting a Map should cascade delete its Layers.
        """
        session = get_session()
        try:
            map_obj = Map(name="Cascade Test")
            session.add(map_obj)
            session.flush()

            layer_obj = Layer(
                map_id=map_obj.id,
                name="Cascade Layer",
                order_index=0
            )
            session.add(layer_obj)
            session.commit()

            layer_id = layer_obj.id
            map_id = map_obj.id

            # Delete the map
            session.delete(map_obj)
            session.commit()

            # Layer should also be deleted
            assert session.query(Layer).filter(Layer.id == layer_id).first() is None
            assert session.query(Map).filter(Map.id == map_id).first() is None
        finally:
            session.close()


# =============================================================================
# Phase 4: Path Model Tests
# =============================================================================

class TestPathModel:
    """Tests for the Path ORM model."""

    def test_path_can_be_created(self, test_db):
        """
        A Path can be created and associated with a Layer.
        """
        session = get_session()
        try:
            # Create a map and layer first
            map_obj = Map(name="Path Test Map")
            session.add(map_obj)
            session.flush()

            layer_obj = Layer(
                map_id=map_obj.id,
                name="Path Layer",
                order_index=0
            )
            session.add(layer_obj)
            session.flush()

            # Create a path with ordered points (not command stream)
            points_json = json.dumps([
                {"x": 0.0, "y": 0.0},
                {"x": 100.0, "y": 100.0}
            ])
            path_obj = Path(
                layer_id=layer_obj.id,
                points_json=points_json,
                stroke_color="#FF0000",
                stroke_width=6.0
            )
            session.add(path_obj)
            session.commit()

            assert path_obj.id is not None
            assert path_obj.layer_id == layer_obj.id
        finally:
            session.close()

    def test_path_stores_color_and_width(self, test_db):
        """
        A Path stores stroke_color and stroke_width properties correctly.
        """
        session = get_session()
        try:
            map_obj = Map(name="Style Test Map")
            session.add(map_obj)
            session.flush()

            layer_obj = Layer(
                map_id=map_obj.id,
                name="Style Layer",
                order_index=0
            )
            session.add(layer_obj)
            session.flush()

            path_obj = Path(
                layer_id=layer_obj.id,
                points_json="[]",
                stroke_color="#00FF00",
                stroke_width=12.0
            )
            session.add(path_obj)
            session.commit()

            # Query back
            loaded_path = session.query(Path).filter(Path.id == path_obj.id).first()
            assert loaded_path.stroke_color == "#00FF00"
            assert loaded_path.stroke_width == 12.0
        finally:
            session.close()

    def test_paths_deleted_with_layer(self, test_db):
        """
        Deleting a Layer should cascade delete its Paths.
        """
        session = get_session()
        try:
            # Create map with layer and path
            map_obj = Map(name="Path Cascade Test")
            session.add(map_obj)
            session.flush()

            layer_obj = Layer(
                map_id=map_obj.id,
                name="Cascade Layer",
                order_index=0
            )
            session.add(layer_obj)
            session.flush()

            path_obj = Path(
                layer_id=layer_obj.id,
                points_json="[]",
                stroke_color="#000000",
                stroke_width=6.0
            )
            session.add(path_obj)
            session.commit()

            path_id = path_obj.id
            map_id = map_obj.id

            # Delete the map (which cascades to layer, then to path)
            session.delete(map_obj)
            session.commit()

            # Path should also be deleted
            assert session.query(Path).filter(Path.id == path_id).first() is None
        finally:
            session.close()


# =============================================================================
# Phase 4: MapRepository Save Tests
# =============================================================================

class TestMapRepositorySave:
    """Tests for MapRepository.save_map()."""

    def test_save_new_map_returns_id(self, map_repository, sample_path_data):
        """
        save_map() should return the ID of the newly created map.
        """
        map_id = map_repository.save_map(
            name="New Map",
            paths=sample_path_data
        )

        assert map_id is not None
        assert isinstance(map_id, int)
        assert map_id > 0

    def test_save_map_stores_name(self, map_repository):
        """
        save_map() should store the map name correctly.
        """
        map_id = map_repository.save_map(
            name="Named Map",
            paths=[]
        )

        # Verify by loading
        map_data = map_repository.load_map(map_id)
        assert map_data["name"] == "Named Map"

    def test_save_map_stores_background_path(self, map_repository):
        """
        save_map() should store the background image path.
        """
        map_id = map_repository.save_map(
            name="Background Map",
            paths=[],
            background_image_path="/path/to/bg.png"
        )

        map_data = map_repository.load_map(map_id)
        assert map_data["background_image_path"] == "/path/to/bg.png"

    def test_save_map_stores_paths(self, map_repository, sample_path_data):
        """
        save_map() should store all paths correctly.
        """
        map_id = map_repository.save_map(
            name="Paths Map",
            paths=sample_path_data
        )

        map_data = map_repository.load_map(map_id)
        assert len(map_data["paths"]) == 2

    def test_save_map_creates_default_layer(self, map_repository, sample_path_data):
        """
        save_map() should create a default layer for all content.
        """
        map_id = map_repository.save_map(
            name="Default Layer Test",
            paths=sample_path_data
        )

        # Verify default layer exists
        session = get_session()
        try:
            layer = session.query(Layer).filter(
                Layer.map_id == map_id,
                Layer.name == DEFAULT_LAYER_NAME,
                Layer.order_index == DEFAULT_LAYER_ORDER_INDEX
            ).first()
            assert layer is not None
        finally:
            session.close()

    def test_update_existing_map(self, map_repository, sample_path_data):
        """
        save_map() with map_id should update an existing map.
        """
        # Create initial map
        map_id = map_repository.save_map(
            name="Original Name",
            paths=sample_path_data[:1]  # One path
        )

        # Update it
        map_repository.save_map(
            name="Updated Name",
            paths=sample_path_data,  # Two paths
            map_id=map_id
        )

        # Verify updates
        map_data = map_repository.load_map(map_id)
        assert map_data["name"] == "Updated Name"
        assert len(map_data["paths"]) == 2

    def test_save_with_stale_map_id_creates_new(self, map_repository, sample_path_data):
        """
        save_map() with a non-existent map_id should create a new map.

        This handles the case where a user deletes a map in a Load dialog
        while still editing it, then tries to save - it should create
        a new map rather than failing.
        """
        # Save with a map_id that doesn't exist
        new_map_id = map_repository.save_map(
            name="Recovered Map",
            paths=sample_path_data,
            map_id=99999  # This ID doesn't exist
        )

        # Should have created a new map
        assert new_map_id is not None
        assert new_map_id != 99999

        # Verify the map was saved
        map_data = map_repository.load_map(new_map_id)
        assert map_data["name"] == "Recovered Map"
        assert len(map_data["paths"]) == 2


# =============================================================================
# Phase 4: MapRepository Load Tests
# =============================================================================

class TestMapRepositoryLoad:
    """Tests for MapRepository.load_map()."""

    def test_load_returns_map_data(self, map_repository, sample_path_data):
        """
        load_map() should return complete map data.
        """
        map_id = map_repository.save_map(
            name="Load Test",
            paths=sample_path_data,
            background_image_path="/bg.png"
        )

        map_data = map_repository.load_map(map_id)

        assert map_data["id"] == map_id
        assert map_data["name"] == "Load Test"
        assert map_data["background_image_path"] == "/bg.png"
        assert "paths" in map_data

    def test_load_returns_none_for_missing_map(self, map_repository):
        """
        load_map() should return None for non-existent map ID.
        """
        result = map_repository.load_map(99999)
        assert result is None

    def test_load_deserializes_path_data(self, map_repository, sample_path_data):
        """
        load_map() should deserialize points from JSON.
        """
        map_id = map_repository.save_map(
            name="Deserialize Test",
            paths=sample_path_data
        )

        map_data = map_repository.load_map(map_id)
        first_path = map_data["paths"][0]

        # points should be a list, not a JSON string
        assert isinstance(first_path["points"], list)
        assert first_path["points"][0]["x"] == 0.0
        assert first_path["points"][0]["y"] == 0.0

    def test_load_preserves_path_properties(self, map_repository, sample_path_data):
        """
        load_map() should preserve path stroke_color and stroke_width.
        """
        map_id = map_repository.save_map(
            name="Properties Test",
            paths=sample_path_data
        )

        map_data = map_repository.load_map(map_id)
        first_path = map_data["paths"][0]

        assert first_path["stroke_color"] == "#FF0000"
        assert first_path["stroke_width"] == 6.0


# =============================================================================
# Phase 4: MapRepository List Tests
# =============================================================================

class TestMapRepositoryList:
    """Tests for MapRepository.list_maps()."""

    def test_list_returns_empty_initially(self, map_repository):
        """
        list_maps() should return an empty list when no maps exist.
        """
        result = map_repository.list_maps()
        assert result == []

    def test_list_returns_all_maps(self, map_repository):
        """
        list_maps() should return all saved maps.
        """
        # Create multiple maps
        map_repository.save_map(name="Map 1", paths=[])
        map_repository.save_map(name="Map 2", paths=[])
        map_repository.save_map(name="Map 3", paths=[])

        result = map_repository.list_maps()
        assert len(result) == 3

    def test_list_returns_summary_info(self, map_repository, sample_path_data):
        """
        list_maps() should return summary info for each map.
        """
        map_repository.save_map(
            name="Summary Test",
            paths=sample_path_data
        )

        result = map_repository.list_maps()
        map_info = result[0]

        assert "id" in map_info
        assert "name" in map_info
        assert "path_count" in map_info
        assert map_info["path_count"] == 2

    def test_list_ordered_by_update_time(self, map_repository):
        """
        list_maps() should return maps ordered by most recently updated.
        """
        id1 = map_repository.save_map(name="First", paths=[])
        id2 = map_repository.save_map(name="Second", paths=[])

        # Update the first map
        map_repository.save_map(name="First Updated", paths=[], map_id=id1)

        result = map_repository.list_maps()
        # First map should now be first (most recently updated)
        assert result[0]["name"] == "First Updated"


# =============================================================================
# Phase 4: MapRepository Delete Tests
# =============================================================================

class TestMapRepositoryDelete:
    """Tests for MapRepository.delete_map()."""

    def test_delete_removes_map(self, map_repository):
        """
        delete_map() should remove the map from the database.
        """
        map_id = map_repository.save_map(name="To Delete", paths=[])

        result = map_repository.delete_map(map_id)

        assert result is True
        assert map_repository.load_map(map_id) is None

    def test_delete_returns_false_for_missing_map(self, map_repository):
        """
        delete_map() should return False for non-existent map ID.
        """
        result = map_repository.delete_map(99999)
        assert result is False

    def test_delete_removes_layers_and_paths(self, map_repository, sample_path_data):
        """
        delete_map() should also delete all associated layers and paths.
        """
        map_id = map_repository.save_map(
            name="Delete With Paths",
            paths=sample_path_data
        )

        # Get the layer ID before deletion
        session = get_session()
        try:
            layer = session.query(Layer).filter(Layer.map_id == map_id).first()
            layer_id = layer.id
        finally:
            session.close()

        # Delete the map
        map_repository.delete_map(map_id)

        # Verify layers and paths are gone
        session = get_session()
        try:
            layer_count = session.query(Layer).filter(Layer.map_id == map_id).count()
            path_count = session.query(Path).filter(Path.layer_id == layer_id).count()
            assert layer_count == 0
            assert path_count == 0
        finally:
            session.close()


# =============================================================================
# Phase 4: MapRepository Utility Tests
# =============================================================================

class TestMapRepositoryUtility:
    """Tests for MapRepository utility methods."""

    def test_map_exists_returns_true_for_existing(self, map_repository):
        """
        map_exists() should return True for existing map.
        """
        map_id = map_repository.save_map(name="Exists", paths=[])
        assert map_repository.map_exists(map_id) is True

    def test_map_exists_returns_false_for_missing(self, map_repository):
        """
        map_exists() should return False for non-existent map.
        """
        assert map_repository.map_exists(99999) is False
