"""
Tests for the undo command classes (Phase 3).

This module tests the AddStrokeCommand class which handles undoable
stroke operations. These are unit tests that verify the command's
redo() and undo() methods work correctly in isolation.

Test coverage:
    - AddStrokeCommand.redo() adds item to scene
    - AddStrokeCommand.undo() removes item from scene
    - Guards against duplicate add operations
    - Guards against duplicate remove operations
    - Command text is set correctly
"""

from PyQt6.QtWidgets import QGraphicsPathItem
from PyQt6.QtGui import QPainterPath

from canvas.undo_commands import AddStrokeCommand


# =============================================================================
# Phase 3: AddStrokeCommand Unit Tests
# =============================================================================

class TestAddStrokeCommandRedo:
    """Tests for AddStrokeCommand.redo() behavior."""

    def test_redo_adds_item_to_empty_scene(self, sample_scene):
        """
        redo() should add the stroke item to a scene that doesn't contain it.

        This is the primary use case: when a command is first pushed to the
        undo stack, redo() is called automatically to add the item.
        """
        # Create a path item that is NOT in the scene
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(100, 100)
        stroke_item = QGraphicsPathItem(path)

        # Verify item is not in scene initially
        assert stroke_item.scene() is None

        # Create command and call redo
        command = AddStrokeCommand(sample_scene, stroke_item)
        command.redo()

        # Verify item is now in the scene
        assert stroke_item.scene() is sample_scene
        assert stroke_item in sample_scene.items()

    def test_redo_guards_against_duplicate_add(self, sample_scene):
        """
        redo() should not add an item that is already in the scene.

        The guard prevents Qt errors/warnings from duplicate additions.
        This tests the defensive programming in the redo() method.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(50, 50)
        stroke_item = QGraphicsPathItem(path)

        # Manually add item to scene first
        sample_scene.addItem(stroke_item)
        initial_item_count = len(sample_scene.items())

        # Create command and call redo (item already in scene)
        command = AddStrokeCommand(sample_scene, stroke_item)
        command.redo()

        # Item count should not change (no duplicate was added)
        assert len(sample_scene.items()) == initial_item_count
        assert stroke_item.scene() is sample_scene


class TestAddStrokeCommandUndo:
    """Tests for AddStrokeCommand.undo() behavior."""

    def test_undo_removes_item_from_scene(self, sample_scene):
        """
        undo() should remove the stroke item from the scene.

        This is the primary undo use case: after a stroke has been added,
        calling undo() should remove it from the scene.
        """
        path = QPainterPath()
        path.moveTo(10, 10)
        path.lineTo(90, 90)
        stroke_item = QGraphicsPathItem(path)

        # Add item to scene first
        sample_scene.addItem(stroke_item)
        assert stroke_item.scene() is sample_scene

        # Create command and call undo
        command = AddStrokeCommand(sample_scene, stroke_item)
        command.undo()

        # Verify item is no longer in the scene
        assert stroke_item.scene() is None
        assert stroke_item not in sample_scene.items()

    def test_undo_guards_against_removing_absent_item(self, sample_scene):
        """
        undo() should not attempt to remove an item that isn't in the scene.

        The guard prevents Qt errors from attempting to remove an item
        that doesn't exist in the scene.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(25, 25)
        stroke_item = QGraphicsPathItem(path)

        # Item is NOT in scene
        assert stroke_item.scene() is None

        # Create command and call undo (should not raise)
        command = AddStrokeCommand(sample_scene, stroke_item)
        command.undo()  # Should complete without error

        # Item should still not be in scene
        assert stroke_item.scene() is None


class TestAddStrokeCommandUndoRedoCycle:
    """Tests for complete undo/redo cycles."""

    def test_undo_redo_cycle_restores_item(self, sample_scene):
        """
        A complete undo/redo cycle should restore the item to the scene.

        This tests the typical user workflow: draw stroke, undo, redo.
        """
        path = QPainterPath()
        path.moveTo(0, 0)
        path.lineTo(100, 100)
        stroke_item = QGraphicsPathItem(path)

        command = AddStrokeCommand(sample_scene, stroke_item)

        # Initial redo: item should be added
        command.redo()
        assert stroke_item.scene() is sample_scene

        # Undo: item should be removed
        command.undo()
        assert stroke_item.scene() is None

        # Redo again: item should be restored
        command.redo()
        assert stroke_item.scene() is sample_scene

    def test_multiple_undo_redo_cycles(self, sample_scene):
        """
        Multiple undo/redo cycles should work correctly.

        This ensures the command remains functional through multiple
        undo/redo operations without degradation.
        """
        path = QPainterPath()
        path.moveTo(5, 5)
        path.lineTo(95, 95)
        stroke_item = QGraphicsPathItem(path)

        command = AddStrokeCommand(sample_scene, stroke_item)

        # Run through 3 complete cycles
        for _ in range(3):
            command.redo()
            assert stroke_item.scene() is sample_scene

            command.undo()
            assert stroke_item.scene() is None


class TestAddStrokeCommandMetadata:
    """Tests for command metadata and text."""

    def test_command_has_descriptive_text(self, sample_scene):
        """
        The command should have descriptive text for the undo/redo UI.

        Qt uses this text to display what action will be undone/redone.
        """
        path = QPainterPath()
        stroke_item = QGraphicsPathItem(path)

        command = AddStrokeCommand(sample_scene, stroke_item)

        assert command.text() == "Add Stroke"


class TestAddStrokeCommandWithMultipleItems:
    """Tests involving multiple stroke items."""

    def test_multiple_commands_affect_only_their_own_items(self, sample_scene):
        """
        Each command should only affect its own stroke item.

        This ensures commands don't accidentally modify other items.
        """
        # Create two separate strokes and commands
        path1 = QPainterPath()
        path1.moveTo(0, 0)
        path1.lineTo(50, 50)
        stroke1 = QGraphicsPathItem(path1)

        path2 = QPainterPath()
        path2.moveTo(50, 50)
        path2.lineTo(100, 100)
        stroke2 = QGraphicsPathItem(path2)

        command1 = AddStrokeCommand(sample_scene, stroke1)
        command2 = AddStrokeCommand(sample_scene, stroke2)

        # Add both items
        command1.redo()
        command2.redo()
        assert len(sample_scene.items()) == 2

        # Undo only command2
        command2.undo()
        assert stroke1.scene() is sample_scene  # stroke1 still present
        assert stroke2.scene() is None          # stroke2 removed
        assert len(sample_scene.items()) == 1

        # Undo command1
        command1.undo()
        assert stroke1.scene() is None
        assert len(sample_scene.items()) == 0
