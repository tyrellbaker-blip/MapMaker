"""
Database engine and session management for the Map Maker application.

This module provides the core database infrastructure using SQLAlchemy:
    - Engine creation and configuration
    - Session factory for database operations
    - Database initialization (table creation)

The database uses SQLite for simplicity and portability. The database file
is stored in the db/ directory alongside the database code.

Phase 4: Database setup with SQLAlchemy ORM.

Authors: Ty Baker, Everett Loxley
Created: March 19, 2026
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from db.models import Base


# =============================================================================
# Phase 4: Database Configuration
# =============================================================================

# Database file name - stored in db/ directory
DATABASE_FILENAME = "mapmaker.db"

# Global engine and session factory
_engine = None
_session_factory = None


def get_database_path() -> str:
    """
    Get the path for the SQLite database file.

    The database is stored in the db/ directory alongside the database code.
    This keeps all database-related files together and out of the working
    directory root.

    Returns:
        The full path to the database file.
    """
    # Get the directory where this module lives (db/)
    db_dir = Path(__file__).parent

    # Ensure the directory exists
    db_dir.mkdir(parents=True, exist_ok=True)

    return str(db_dir / DATABASE_FILENAME)


def get_engine():
    """
    Get the database engine.

    Returns the SQLAlchemy Engine object. If the engine hasn't been
    initialized yet, this will trigger initialization.

    Returns:
        The SQLAlchemy Engine object.

    Raises:
        RuntimeError: If init_database() hasn't been called yet.
    """
    if _engine is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _engine


def get_session_factory():
    """
    Get the session factory for creating database sessions.

    Returns:
        The SQLAlchemy sessionmaker instance.

    Raises:
        RuntimeError: If init_database() hasn't been called yet.
    """
    if _session_factory is None:
        raise RuntimeError(
            "Database not initialized. Call init_database() first."
        )
    return _session_factory


def get_session() -> Session:
    """
    Create and return a new database session.

    Sessions should be used within a try/finally block to ensure proper
    cleanup. Always call session.close() when done.

    Returns:
        A new SQLAlchemy Session object.

    Raises:
        RuntimeError: If init_database() hasn't been called yet.

    Example:
        session = get_session()
        try:
            maps = session.query(Map).all()
            session.commit()
        finally:
            session.close()
    """
    return get_session_factory()()


def init_database(db_path: str = None) -> None:
    """
    Initialize the database engine and create tables if they don't exist.

    This function should be called once at application startup. It:
    1. Creates the SQLAlchemy engine (connection to the database)
    2. Creates all tables defined in the models (if they don't exist)
    3. Sets up the session factory for creating database sessions

    Args:
        db_path: Optional path to the database file. If None, uses the
                 default path from get_database_path(). Primarily used
                 for testing with isolated databases.
    """
    global _engine, _session_factory

    if db_path is None:
        db_path = get_database_path()

    # Ensure parent directory exists for the database file
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)

    # Create the SQLite engine
    # echo=False disables SQL logging (set to True for debugging)
    # check_same_thread=False is needed for SQLite with multiple threads
    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False}
    )

    # Create all tables defined in models.py
    # This is safe to call multiple times - it only creates tables that
    # don't already exist
    Base.metadata.create_all(_engine)

    # Create the session factory
    _session_factory = sessionmaker(bind=_engine)
