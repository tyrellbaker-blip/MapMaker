"""
Database package for the Map Maker application.

This package provides SQLite persistence for map data using SQLAlchemy ORM.
It enables users to save their work and load previously created maps.

Modules:
    - database: Database engine and session management
    - models: SQLAlchemy ORM models for map entities
    - map_repository: High-level API for saving/loading maps

Phase 4 Architecture:
    The database layer follows a repository pattern:

    MainWindow
        └── MapRepository (db/map_repository.py)
                └── Session (db/database.py)
                        └── Models (db/models.py)
                                └── SQLite Database (db/mapmaker.db)

Authors: Ty Baker, Everett Loxley
Created: March 19, 2026
"""

from db.database import init_database, get_session
from db.models import Map, Layer, Path
from db.map_repository import MapRepository

__all__ = [
    'init_database',
    'get_session',
    'Map',
    'Layer',
    'Path',
    'MapRepository',
]
