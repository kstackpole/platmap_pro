from PySide6.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QVBoxLayout, QPushButton, QDialog, QGraphicsPathItem, QMessageBox,
    QFileDialog, QSizePolicy, QHBoxLayout, QWidget
)
from PySide6.QtGui import QColor, QPainterPath, QPen, QBrush
from PySide6.QtCore import Qt, QRectF
from svg.path import Line, CubicBezier, Move, Close
from shapely.geometry import Point, Polygon
import xml.etree.ElementTree as ET
import sys
import svg.path as svg_path
import xml.dom.minidom as minidom



class CustomGraphicsView(QGraphicsView):
    """Custom QGraphicsView to enable smooth zooming with the mouse wheel and panning with the spacebar."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom_factor = 0.1  # Incremental zoom factor
        self.setDragMode(QGraphicsView.RubberBandDrag)  # Enable rubber band drag for multi-selection
        self.original_transform = self.transform()  # Save the original transform for resetting

    def wheelEvent(self, event):
        """Zoom in/out smoothly with the mouse wheel."""
        delta = event.angleDelta().y() / 120  # Standard mouse wheel step is 120
        factor = 1 + self.zoom_factor * delta

        # Apply zoom transformation
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.scale(factor, factor)

    def keyPressEvent(self, event):
        """Enable panning when the spacebar is pressed or reset the view on Escape."""
        if event.key() == Qt.Key_Space:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
        elif event.key() == Qt.Key_Escape:
            # Reset the view to the initial state
            self.setTransform(self.original_transform)  # Reset the zoom and pan
            self.setDragMode(QGraphicsView.RubberBandDrag)  # Restore drag mode
            self.scene().clearSelection()  # Clear any selections
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        """Disable panning when the spacebar is released."""
        if event.key() == Qt.Key_Space:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        else:
            super().keyReleaseEvent(event)


class SelectableDot(QGraphicsEllipseItem):
    """Custom QGraphicsEllipseItem to support Shift-click and Cmd-click multi-selection."""
    def mousePressEvent(self, event):
        """Enable Shift+Click or Cmd+Click to add/remove dots from the selection."""
        modifiers = event.modifiers()
        if modifiers & (Qt.ShiftModifier | Qt.ControlModifier):  # Cmd is Qt.ControlModifier on macOS
            self.setSelected(not self.isSelected())  # Toggle selection
        else:
            super().mousePressEvent(event)  # Default behavior for single selection

class EditableSVG(QDialog):
    def __init__(self, svg_file=None, output_file=None):
        super().__init__()
        self.svg_file = svg_file
        self.output_file = output_file

        # Initialize attributes
        self.groups = []  # List of (dot_item, circle_elem) pairs
        self.svg_tree = None
        self.root = None

        # Set up window properties
        self.setWindowTitle("SVG Editor")
        self.setGeometry(50, 50, 1400, 900)

        # Main layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Graphics View for displaying SVG
        self.graphics_view = CustomGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.graphics_view.setScene(self.scene)
        self.layout.addWidget(self.graphics_view)

        # Add the overlay toolbar
        self.add_toolbar()

        # Load SVG if provided
        if self.svg_file:
            self.load_svg(self.svg_file)

    def add_toolbar(self):
        """Add an overlay toolbar with zoom buttons and a swap button."""
        # Create a transparent widget to overlay the graphics view
        toolbar = QWidget(self)
        toolbar.setStyleSheet(
            """
            background: rgba(0, 0, 0, 0.6); 
            border-radius: 8px;
            padding: 5px;
            """
        )
        toolbar.setFixedSize(150, 40)

        # Position the toolbar in the top-left corner of the graphics view
        toolbar.move(20, 20)

        # Create layout and buttons for the toolbar
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Zoom In Button
        zoom_in_button = QPushButton("+")
        zoom_in_button.setFixedSize(20, 20)
        zoom_in_button.setToolTip("Zoom In")
        zoom_in_button.setStyleSheet(
            """
            QPushButton {
                background-color: #444; 
                color: white; 
                border: none; 
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #666;
            }
            """
        )
        zoom_in_button.clicked.connect(self.zoom_in)

        # Zoom Out Button
        zoom_out_button = QPushButton("-")
        zoom_out_button.setFixedSize(20, 20)
        zoom_out_button.setToolTip("Zoom Out")
        zoom_out_button.setStyleSheet(
            """
            QPushButton {
                background-color: #444; 
                color: white; 
                border: none; 
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #666;
            }
            """
        )
        zoom_out_button.clicked.connect(self.zoom_out)

        # Swap Button
        swap_button = QPushButton("Swap")
        swap_button.setFixedSize(50, 20)
        swap_button.setToolTip("Swap Selected Dots")
        swap_button.setStyleSheet(
            """
            QPushButton {
                background-color: #444; 
                color: white; 
                border: none; 
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #666;
            }
            """
        )
        swap_button.clicked.connect(self.swap_selected_dots)

        # Add buttons to the layout
        layout.addWidget(zoom_in_button)
        layout.addWidget(zoom_out_button)
        layout.addWidget(swap_button)
        toolbar.setLayout(layout)

        self.toolbar = toolbar  # Keep a reference to the toolbar widget

    def open_new_file(self):
        """Open a new SVG file and set the output file path."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self, "Open SVG File", "", "SVG Files (*.svg);;All Files (*)"
        )
        if file_path:
            self.svg_file = file_path
            self.output_file = file_path  # Use the same file path for saving by default
            self.load_svg(self.svg_file)

    def zoom_in(self):
        """Zoom in on the map."""
        self.graphics_view.scale(1.2, 1.2)

    def zoom_out(self):
        """Zoom out on the map."""
        self.graphics_view.scale(0.8, 0.8)

    def load_svg(self, svg_file):
        """Load the SVG file into the editor."""
        if not svg_file:
            return

        try:
            # Parse SVG XML
            self.svg_tree = ET.parse(svg_file)
            self.root = self.svg_tree.getroot()

            # Adjust the scene with the viewBox and get dimensions
            width, height = self.setup_scene_viewbox()

            # Render the SVG content onto the scene
            self.render_static_svg()

            # Load editable groups
            self.load_groups()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load SVG file:\n{str(e)}")

    def auto_arrange_dots(self):
        """Automatically arrange dots at the corners of each lot's path shape."""
        namespace = {"svg": "http://www.w3.org/2000/svg"}

        for group_elem in self.root.findall(".//svg:g", namespace):
            path_elem = group_elem.find("svg:path", namespace)
            if path_elem is not None:
                d_attr = path_elem.get("d")
                parsed_path = svg_path.parse_path(d_attr)

                # Extract all points from the path to create a polygon
                path_points = []
                for segment in parsed_path:
                    if isinstance(segment, (Line, Move, Close)):
                        path_points.append((segment.start.real, segment.start.imag))
                        path_points.append((segment.end.real, segment.end.imag))
                    elif isinstance(segment, CubicBezier):
                        path_points.append((segment.start.real, segment.start.imag))
                        path_points.append((segment.end.real, segment.end.imag))
                        path_points.append((segment.control1.real, segment.control1.imag))
                        path_points.append((segment.control2.real, segment.control2.imag))

                lot_polygon = Polygon(path_points)
                min_x, min_y, max_x, max_y = lot_polygon.bounds
                inset = max((max_x - min_x) * 0.08, 10)

                # Define corner positions with inset
                corner_positions = [
                    (min_x + inset, min_y + inset),
                    (max_x - inset, min_y + inset),
                    (min_x + inset, max_y - inset),
                    (max_x - inset, max_y - inset),
                ]

                # Ensure dots are inside the polygon
                valid_positions = [
                    (cx, cy) for cx, cy in corner_positions if lot_polygon.contains(Point(cx, cy))
                ]

                # Assign dots to valid positions
                dot_classes = ["constStatus", "lotPremium", "soldStatus"]
                for i, (cx, cy) in enumerate(valid_positions[:len(dot_classes)]):
                    dot_class = dot_classes[i]
                    circle_elem = group_elem.find(f"svg:g[@class='{dot_class}']/svg:circle", namespace)
                    if circle_elem is not None:
                        circle_elem.set("cx", str(cx))
                        circle_elem.set("cy", str(cy))
                        circle_elem.set("r", str(5))
                        # Update the dot in the scene
                        for dot, original_circle in self.groups:
                            if original_circle == circle_elem:
                                dot.setRect(cx - 5, cy - 5, 10, 10)

        self.scene.update()
        QMessageBox.information(self, "Auto Arrange", "Dots have been arranged automatically.")

    def swap_selected_dots(self):
        """Swap the physical positions of exactly two selected dots, keeping their color/class the same."""
        # Get the selected items
        selected_dots = [dot for dot, _ in self.groups if dot.isSelected()]

        if len(selected_dots) != 2:
            QMessageBox.warning(self, "Swap Error", "Please select exactly two dots to swap.")
            return

        # Get the two selected dots
        dot1, dot2 = selected_dots
        pos1 = dot1.sceneBoundingRect().center()
        pos2 = dot2.sceneBoundingRect().center()

        # Swap positions in the scene
        dot1.setRect(pos2.x() - 5, pos2.y() - 5, 10, 10)
        dot2.setRect(pos1.x() - 5, pos1.y() - 5, 10, 10)

        # Update the corresponding SVG elements for only the two swapped dots
        for dot, circle_elem in self.groups:
            if dot == dot1:
                circle_elem.set("cx", str(pos2.x()))
                circle_elem.set("cy", str(pos2.y()))
            elif dot == dot2:
                circle_elem.set("cx", str(pos1.x()))
                circle_elem.set("cy", str(pos1.y()))

        # Redraw the scene to reflect the new positions
        self.scene.removeItem(dot1)
        self.scene.removeItem(dot2)

        self.scene.addItem(dot1)
        self.scene.addItem(dot2)

        # Call `update` on the scene and dots
        dot1.update()
        dot2.update()
        self.scene.update()


    def setup_scene_viewbox(self):
        """Set up scene dimensions based on the SVG viewBox and resize the window accordingly."""
        self.scene.clear()
        viewBox = self.root.get("viewBox") if self.root is not None else None
        if viewBox:
            # Parse viewBox attributes
            min_x, min_y, width, height = map(float, viewBox.split())
            self.scene.setSceneRect(min_x, min_y, width, height)
            self.resize_window_to_fit_svg(width, height)
            return width, height
        else:
            # Default scene size if no viewBox is available
            self.scene.setSceneRect(0, 0, 1400, 900)
            self.resize_window_to_fit_svg(1400, 900)
            return 1400, 900

    def resize_window_to_fit_svg(self, width, height):
        """Resize the main window to fit the SVG dimensions initially."""
        padding = 50
        self.graphics_view.setSceneRect(0, 0, width, height)
        self.graphics_view.setMinimumSize(100, 100)
        self.graphics_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.resize(width + padding, height + padding)

    def render_static_svg(self):
        """Render static elements like paths, circles, and other shapes, excluding paths inside the 'text' group."""
        namespace = {"svg": "http://www.w3.org/2000/svg"}

        # Find the 'text' group
        text_group = self.root.find(".//svg:g[@id='text']", namespace)
        text_paths = set()

        if text_group is not None:
            # Collect all paths inside the 'text' group
            for path_elem in text_group.findall(".//svg:path", namespace):
                text_paths.add(path_elem)

        # Render all paths not in the 'text' group
        for path_elem in self.root.findall(".//svg:path", namespace):
            if path_elem in text_paths:
                continue  # Skip paths in the 'text' group

            # Process and render the path
            d_attr = path_elem.get("d")
            if d_attr:
                parsed_path = svg_path.parse_path(d_attr)
                painter_path = QPainterPath()
                for element in parsed_path:
                    if isinstance(element, svg_path.Move):
                        painter_path.moveTo(element.start.real, element.start.imag)
                    elif isinstance(element, svg_path.Line):
                        painter_path.lineTo(element.end.real, element.end.imag)
                    elif isinstance(element, svg_path.CubicBezier):
                        painter_path.cubicTo(
                            element.control1.real, element.control1.imag,
                            element.control2.real, element.control2.imag,
                            element.end.real, element.end.imag,
                        )
                static_path_item = QGraphicsPathItem(painter_path)
                static_path_item.setPen(QPen(QColor(path_elem.get("stroke", "#000000"))))
                static_path_item.setBrush(QBrush(QColor(path_elem.get("fill", "transparent"))))
                self.scene.addItem(static_path_item)


    def load_groups(self):
        """Load editable groups and visually distinguish them by color."""
        namespace = {"svg": "http://www.w3.org/2000/svg"}
        color_map = {"constStatus": "blue", "lotPremium": "red", "soldStatus": "green"}
        standard_radius = 5

        for group in self.root.findall(".//svg:g", namespace):
            class_attr = group.get("class")
            if class_attr in color_map:
                circle = group.find("svg:circle", namespace)
                text = group.find("svg:text", namespace)  # Find the associated text element

                if circle is not None:
                    # Load circle details
                    circle.set("r", str(standard_radius))
                    cx, cy = float(circle.get("cx")), float(circle.get("cy"))
                    dot = SelectableDot(QRectF(cx - standard_radius, cy - standard_radius,
                                            standard_radius * 2, standard_radius * 2))
                    dot.setBrush(QColor(color_map[class_attr]))
                    dot.setPen(Qt.NoPen)

                    dot.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
                    dot.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
                    dot.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
                    dot.setZValue(10)

                    self.scene.addItem(dot)

                    # Append dot, circle, and text to the groups
                    self.groups.append((dot, circle, text))


    def save_changes(self):
        """Save updated positions of dots and associated text elements to the SVG file."""
        # Declare the SVG namespace
        svg_ns = "http://www.w3.org/2000/svg"
        ET.register_namespace("", svg_ns)  # Set empty prefix for default namespace

        # Update positions of the dots and associated text elements
        for dot, circle, text in self.groups:
            new_cx = dot.sceneBoundingRect().center().x()
            new_cy = dot.sceneBoundingRect().center().y()

            # Update circle position
            circle.set("cx", str(new_cx))
            circle.set("cy", str(new_cy))

            # Find parent group manually
            parent = circle.find("..")
            parent_class = parent.get("class") if parent is not None else ""

            # Update text transform property (instead of x and y)
            if text is not None:
                if parent_class == "constStatus":
                    transform_matrix = f"matrix(1 0 0 1 {new_cx} {new_cy})"
                elif parent_class == "lotPremium":
                    transform_matrix = f"matrix(1 0 0 1 {new_cx} {new_cy})"
                else:
                    transform_matrix = f"matrix(1 0 0 1 {new_cx} {new_cy})"
                text.set("transform", transform_matrix)

        # Convert XML to string and pretty print
        xml_str = ET.tostring(self.svg_tree.getroot(), encoding="utf-8").decode("utf-8")
        parsed_xml = minidom.parseString(xml_str)
        pretty_xml = parsed_xml.toprettyxml(indent="  ")

        # Remove excessive blank lines
        pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])

        # Ensure the header remains unchanged and remove duplicate header if exists
        svg_header = """<svg version=\"1.0\" xmlns=\"http://www.w3.org/2000/svg\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" x=\"0px\" y=\"0px\" width=\"1440px\" height=\"840px\" viewBox=\"0 0 1440 840\" xml:space=\"preserve\" preserveAspectRatio=\"xMinYMin\" style=\"width:100%\" class=\"tsPlotmap\">"""
        pretty_xml = pretty_xml.replace('<?xml version="1.0" ?>', svg_header, 1)
        pretty_xml = pretty_xml.replace(svg_header, "", 1)

        # Write the modified SVG tree back to the file
        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        QMessageBox.information(self, "Success", f"Changes saved to {self.output_file}")



if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = EditableSVG("example.svg", "output_updated.svg")
    editor.exec()
    sys.exit(app.exec())