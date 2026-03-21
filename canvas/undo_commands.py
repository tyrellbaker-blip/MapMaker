"""
Undo command classes for the Map Maker application.

This module contains QUndoCommand subclasses that represent reversible actions
in the editor. Each command encapsulates a single undoable operation, storing
all the information needed to both perform (redo) and reverse (undo) that action.

The undo/redo system works by pushing commands onto a QUndoStack owned by
MainWindow. When a command is pushed, its redo() method is called automatically.
When the user triggers undo, the command's undo() method is called. When they
trigger redo, redo() is called again.

Authors: Ty Baker, Everett Loxley
Created: March 19, 2026

Phase 3:
    - AddStrokeCommand: Handles adding/removing pen strokes from the scene
"""

from PyQt6.QtGui import QUndoCommand
from PyQt6.QtWidgets import QGraphicsScene, QGraphicsPathItem


# =============================================================================
# Phase 3: Stroke Commands
# =============================================================================

class AddStrokeCommand(QUndoCommand):
    """
    An undoable command that adds a pen stroke to the graphics scene.

    This command owns the reversible action of adding a QGraphicsPathItem
    (a completed pen stroke) to the scene. The command stores references to
    both the scene and the stroke item, allowing it to add or remove the
    stroke when redo() or undo() are called.

    Why the command owns the scene change:
    - The user draws a stroke, which creates a temporary preview item.
    - On mouse release, that item is removed and this command is pushed.
    - When pushed, redo() is called automatically, adding the item to the scene.
    - This means the command is the authoritative owner of the "add" action.
    - If the user undoes, undo() removes the item.
    - If the user redoes, redo() adds it back.

    This design ensures that all scene modifications flow through the undo
    system, making the history consistent and predictable.

    Attributes:
        _scene: The QGraphicsScene where the stroke lives.
        _stroke_item: The QGraphicsPathItem representing the completed stroke.
    """

    def __init__(self, scene: QGraphicsScene, stroke_item: QGraphicsPathItem):
        """
        Initialize the AddStrokeCommand.

        Args:
            scene: The graphics scene that will contain the stroke.
            stroke_item: The completed stroke item to be added/removed.
        """
        super().__init__("Add Stroke")

        # Store references needed to perform and reverse the action.
        # The scene is where items are displayed.
        # The stroke_item is the specific path item we're adding.
        self._scene = scene
        self._stroke_item = stroke_item

    def redo(self):
        """
        Execute or re-execute the command: add the stroke to the scene.

        This method is called automatically when the command is first pushed
        onto the undo stack, and again whenever the user triggers "redo"
        after having undone this command.

        We guard against adding the item if it's already in the scene to
        prevent duplicate additions (which would cause Qt warnings/errors).
        """
        # Only add the item if it's not already in the scene.
        # This guard prevents errors if redo() is called when the item
        # is somehow already present (defensive programming).
        if self._stroke_item.scene() is None:
            self._scene.addItem(self._stroke_item)

    def undo(self):
        """
        Reverse the command: remove the stroke from the scene.

        This method is called when the user triggers "undo" while this
        command is at the top of the undo stack.

        We guard against removing the item if it's not currently in the
        scene to prevent errors from attempting to remove a non-existent item.
        """
        # Only remove the item if it's currently in the scene.
        # This guard prevents errors if undo() is called when the item
        # has already been removed (defensive programming).
        if self._stroke_item.scene() is not None:
            self._scene.removeItem(self._stroke_item)
