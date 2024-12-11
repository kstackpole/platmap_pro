#!/usr/bin/env python3
"""
Main entry point for the Platmap Pro application.

This script initializes and launches the Platmap Pro GUI for creating interactive maps 
from GeoJSON files. It also sets the application metadata and handles the event loop.

Author: Kyle Stackpole
"""

import sys
import os
import logging
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from gui.gui_main import MainWindow

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Resolve icon path
project_root = Path(__file__).resolve().parent.parent
icon_path = os.path.join(project_root, "assets", "icons", "land-layers.png")
if not Path(icon_path).exists():
    icon_path = "assets/icons/land-layers.png"

logging.debug(f"Resolved icon path: {icon_path}")

# Main application entry point
def main():
    logging.debug("Starting Application")
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(icon_path))
    
    # Set metadata
    app.setApplicationName("Platmap Pro")
    app.setOrganizationName("Richmond American Homes")
    app.setOrganizationDomain("https://www.richmondamerican.com")
    app.setApplicationDisplayName("Platmap Pro")

    # Show main window
    logging.debug("Creating main window")
    window = MainWindow()
    window.show()
    logging.debug("Main window open")

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
