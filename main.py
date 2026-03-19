"""
Map Maker Application
A desktop application for creating custom maps with background images.

Entry point for the application.
"""

import sys
from PyQt6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main():
    """Initialize and run the Map Maker application."""
    # Create the Qt application instance
    app = QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Start the event loop and exit when done
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
