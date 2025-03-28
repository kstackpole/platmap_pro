#!/usr/bin/env python3
"""
gui_main.py

This module provides the main gui for the application including the ability to switch contexts 
between creating new maps and editing existing ones

Author: Kyle Stackpole
Copyright: 2024, Kyle Stackpole
Version: 1.0.2
Email: kyle.stackpole@mdch.com
Status: Development
"""

import sys
import os
from converters.geojson_to_svg import geojson_to_svg  # Import your SVG converter
from gui.svg_editor import EditableSVG  # Import svg_editor correctly
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QLabel, QPushButton, QFileDialog,
    QWidget, QMessageBox, QToolBar, QStackedWidget, QListWidget, QGridLayout, QListWidget, QHBoxLayout
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QUrl

class DragDropListWidget(QListWidget):
    def __init__(self, parent_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setAcceptDrops(True)
        self.parent_window = parent_window  # Store reference to MainWindow

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        """Handle the file drop event."""
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                if file_path.lower().endswith(".geojson"):  # Ensure only GeoJSON files are added
                    self.addItem(file_path)  # Add file path to the list widget
                    self.parent_window.file_paths[self.objectName()].append(file_path)  # Store file path
            self.parent_window.check_run_conditions()  # Ensure Run button updates


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Platmap Pro")
        self.setGeometry(100, 100, 700, 400)

        # Store file paths
        self.file_paths = {"Lots": [], "Grass": [], "Water": [], "Road": []}
        self.output_file = None

        # Initialize SVG Editor with reference to MainWindow
        self.svg_editor = EditableSVG(None, None)
        self.svg_editor.parent_window = self  # Provide reference to MainWindow

        # Toolbar
        self.init_toolbar()

        # Central widget
        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)

        # Main Context
        self.main_context = self.create_main_context()
        self.central_widget.addWidget(self.main_context)

        # SVG Editor Context
        self.svg_editor_context = self.create_svg_editor_context()
        self.central_widget.addWidget(self.svg_editor_context)

    def init_toolbar(self):
        """Initialize the toolbar."""
        toolbar = QToolBar("Tools", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # New Map Action
        new_map_action = QAction("Create new map", self)
        new_map_action.triggered.connect(lambda: self.switch_context(0))
        toolbar.addAction(new_map_action)

        # SVG Editor Action
        svg_editor_action = QAction("Open SVG Editor", self)
        svg_editor_action.triggered.connect(lambda: self.switch_context(1))
        toolbar.addAction(svg_editor_action)

    def switch_context(self, index):
        """Switch between main context and SVG editor context."""
        self.central_widget.setCurrentIndex(index)

    def create_main_context(self):
        """Create the main context with file selection and run button."""
        container = QWidget()
        layout = QVBoxLayout()

        # Title Label
        title_label = QLabel("Create New Interactive Map")
        title_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(title_label)

        # File Sections
        self.file_list_widgets = {}

        for file_type in ["Lots", "Grass", "Water", "Road"]:
            section_layout = self.create_file_section(file_type)
            layout.addLayout(section_layout)

        # Output File Selection
        self.output_file_label = QLabel("No output file selected.")
        layout.addWidget(self.output_file_label)

        output_file_button = QPushButton("Select Output File")
        output_file_button.clicked.connect(self.select_output_file)
        layout.addWidget(output_file_button)

        # Run Button
        self.run_button = QPushButton("Run")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_conversion)
        layout.addWidget(self.run_button)

        container.setLayout(layout)
        return container

    def create_file_section(self, file_type):
        """Create a section with a label, drag-and-drop list, and Add/Remove buttons."""
        section_layout = QVBoxLayout()

        # Label
        section_label = QLabel(f"{file_type} Files:")
        section_layout.addWidget(section_label)

        # Drag and Drop List
        file_list = DragDropListWidget(self)
        file_list.setObjectName(file_type)
        self.file_list_widgets[file_type] = file_list
        section_layout.addWidget(file_list)

        # Add and Remove Buttons
        button_layout = QHBoxLayout()
        
        add_button = QPushButton(f"Add {file_type} Files")
        add_button.clicked.connect(lambda: self.add_files(file_type))
        button_layout.addWidget(add_button)

        remove_button = QPushButton(f"Remove {file_type} Files")
        remove_button.clicked.connect(lambda: self.remove_files(file_type))
        button_layout.addWidget(remove_button)

        section_layout.addLayout(button_layout)

        return section_layout

    def create_file_input(self, layout, label_text, row):
        """Create a file input row in the grid."""
        add_button = QPushButton(f"Add {label_text} Files")
        add_button.clicked.connect(lambda: self.add_files(label_text))
        layout.addWidget(add_button, row, 0)

        remove_button = QPushButton(f"Remove {label_text} Files")
        remove_button.clicked.connect(lambda: self.remove_files(label_text))
        layout.addWidget(remove_button, row, 1)

    def add_files(self, file_type):
        """Add files for the given file type."""
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self, f"Select {file_type} Files", "", "GeoJSON Files (*.geojson);;All Files (*)"
        )
        if file_paths:
            self.file_paths[file_type].extend(file_paths)
            self.update_file_list(file_type)

    def remove_files(self, file_type):
        """Remove selected files from the list."""
        widget = self.file_list_widgets[file_type]
        selected_items = widget.selectedItems()
        
        for item in selected_items:
            self.file_paths[file_type].remove(item.text())
            widget.takeItem(widget.row(item))  # Remove from UI

        self.check_run_conditions()  # Ensure Run button is updated

    def update_file_list(self, file_type):
        """Update the file list widget for the given file type, preventing duplicates."""
        widget = self.file_list_widgets[file_type]
        widget.clear()
        
        # Ensure each file is listed only once
        unique_files = list(set(self.file_paths[file_type]))
        self.file_paths[file_type] = unique_files  # Remove duplicates
        widget.addItems(unique_files)

        self.check_run_conditions()  # Ensure Run button is enabled when conditions are met

    def select_output_file(self):
        """Select the output file."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getSaveFileName(
            self, "Select Output File", "", "SVG Files (*.svg);;All Files (*)"
        )
        if file_path:
            self.output_file = file_path
            self.output_file_label.setText(f"Selected output file: {file_path}")
        else:
            self.output_file = None
            self.output_file_label.setText("No output file selected.")
        self.check_run_conditions()

    def check_run_conditions(self):
        """Enable the run button if conditions are met."""
        lots_files_selected = bool(self.file_paths["Lots"])
        output_file_selected = bool(self.output_file)
        self.run_button.setEnabled(lots_files_selected and output_file_selected)

    def run_conversion(self):
        """Run the conversion process."""
        try:
            # Check if files exist
            for file_type, paths in self.file_paths.items():
                for path in paths:
                    if not os.path.exists(path):
                        raise FileNotFoundError(f"File not found: {path}")

            geojson_to_svg(
                self.file_paths["Lots"],
                self.file_paths["Grass"],
                self.file_paths["Water"],
                self.file_paths["Road"],
                self.output_file
            )
            QMessageBox.information(self, "Success", f"SVG file created: {self.output_file}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred:\n{str(e)}")

    def create_svg_editor_context(self):
        """Create the SVG editor context with a toolbar for buttons."""
        container = QWidget()
        layout = QVBoxLayout()

        # Create a toolbar for the SVG editor actions
        editor_toolbar = QToolBar("SVG Editor Tools", self)
        editor_toolbar.setMovable(False)
        editor_toolbar.setStyleSheet("""
            QToolBar {
                background-color: #2E2E2E;
                spacing: 8px;
                padding: 5px;
            }
            QToolButton {
                color: white;
                padding: 5px;
            }
        """)

        # Add actions to the toolbar
        save_action = QAction("Save Changes", self)
        save_action.triggered.connect(self.svg_editor.save_changes)
        editor_toolbar.addAction(save_action)

        auto_arrange_action = QAction("Auto Arrange Dots", self)
        auto_arrange_action.triggered.connect(self.svg_editor.auto_arrange_dots)
        editor_toolbar.addAction(auto_arrange_action)

        open_file_action = QAction("Open SVG File", self)
        open_file_action.triggered.connect(self.svg_editor.open_new_file)
        editor_toolbar.addAction(open_file_action)

        # Add the toolbar to the layout
        layout.addWidget(editor_toolbar)
        layout.addWidget(self.svg_editor)  # Keep the editor view below the toolbar

        container.setLayout(layout)
        return container
    
    def resize_to_svg(self, width, height):
        """Resize the main window to fit the dimensions of the SVG."""
        # Add some padding to the dimensions for better visibility
        width += 50
        height += 50

        # Set a maximum size limit to avoid over-scaling on extremely large SVGs
        screen_geometry = QApplication.primaryScreen().availableGeometry()
        max_width = screen_geometry.width()
        max_height = screen_geometry.height()

        self.resize(min(width, max_width), min(height, max_height))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
