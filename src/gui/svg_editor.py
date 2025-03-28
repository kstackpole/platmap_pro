from PySide6.QtWidgets import (
    QApplication, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QVBoxLayout, QPushButton, QDialog, QGraphicsPathItem, QMessageBox,
    QFileDialog, QSizePolicy, QHBoxLayout, QWidget
)
from PySide6.QtGui import QColor, QPainterPath, QPen, QBrush
from PySide6.QtCore import Qt, QRectF
from PySide6.QtWidgets import QGraphicsItem
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
    """Custom QGraphicsEllipseItem to support linked movement with house icons and other elements."""
    def __init__(self, rect, path_item=None, text_item=None, polygon_item=None):
        super().__init__(rect)
        self.path_item = path_item  # House icon
        self.text_item = text_item  # Text (e.g., lot number)
        self.polygon_item = polygon_item  # Star (lotPremium)

    def itemChange(self, change, value):
        """Ensure that all linked elements move when the dot moves."""
        if change == QGraphicsItem.ItemPositionChange:
            dx = value.x() - self.sceneBoundingRect().center().x()
            dy = value.y() - self.sceneBoundingRect().center().y()

            if self.path_item:
                d_attr = self.path_item.path().elementAt(0)  # Get current path
                try:
                    parsed_path = svg_path.parse_path(d_attr)
                    adjusted_d = []

                    for element in parsed_path:
                        if isinstance(element, (Move, Line)):
                            adjusted_d.append(f"M{element.start.real + dx},{element.start.imag + dy}")
                            adjusted_d.append(f"L{element.end.real + dx},{element.end.imag + dy}")

                        elif isinstance(element, CubicBezier):
                            adjusted_d.append(
                                f"C{element.control1.real + dx},{element.control1.imag + dy} "
                                f"{element.control2.real + dx},{element.control2.imag + dy} "
                                f"{element.end.real + dx},{element.end.imag + dy}"
                            )

                    updated_path = " ".join(adjusted_d)
                    self.path_item.setPath(updated_path)

                except Exception as e:
                    print(f"Error updating path in itemChange: {e}")


            if self.text_item is not None:
                transform_values = self.text_item.get("transform").split()
                old_x = float(transform_values[-2])
                old_y = float(transform_values[-1].replace(")", ""))

                new_x = old_x + dx
                new_y = old_y + dy
                self.text_item.set("transform", f"matrix(1 0 0 1 {new_x} {new_y})")

            if self.polygon_item is not None:
                original_points = self.polygon_item.get("points").split()
                adjusted_points = [
                    f"{float(p.split(',')[0]) + dx},{float(p.split(',')[1]) + dy}"
                    for p in original_points
                ]
                self.polygon_item.set("points", " ".join(adjusted_points))

        return super().itemChange(change, value)


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

        # Call update on the scene and dots
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
        """Render static elements like paths, circles, and other shapes, excluding house icons."""
        namespace = {"svg": "http://www.w3.org/2000/svg"}

        # Find 'text' group to exclude
        text_group = self.root.find(".//svg:g[@id='text']", namespace)
        text_paths = set()

        if text_group is not None:
            for path_elem in text_group.findall(".//svg:path", namespace):
                text_paths.add(path_elem)

        # 🚨 Skip paths inside "soldStatus" groups (house icons)
        for group in self.root.findall(".//svg:g[@class='soldStatus']", namespace):
            for path in group.findall(".//svg:path", namespace):
                text_paths.add(path)

        # ✅ Render paths that are NOT in excluded sets
        for path_elem in self.root.findall(".//svg:path", namespace):
            if path_elem in text_paths:
                continue  # Skip house icons & text paths

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
                text = group.find("svg:text", namespace)
                polygon = group.find("svg:polygon", namespace)
                path = group.find(".//svg:path", namespace)  # Nested house icon path

                if circle is not None:
                    cx, cy = float(circle.get("cx")), float(circle.get("cy"))

                    # Create a dot for selection/movement
                    dot = SelectableDot(QRectF(cx - standard_radius, cy - standard_radius,
                                            standard_radius * 2, standard_radius * 2))
                    dot.setBrush(QColor(color_map[class_attr]))
                    dot.setPen(Qt.NoPen)

                    # Enable movement
                    dot.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
                    dot.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
                    dot.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
                    dot.setZValue(10)
                    self.scene.addItem(dot)

                    # Load and attach house icon correctly
                    path_item = None
                    if path is not None and path.get("data-processed") != "true":
                        d_attr = path.get("d", "")
                        try:
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
                                        element.end.real, element.end.imag
                                    )

                            path_item = QGraphicsPathItem(painter_path)
                            path_item.setPen(QPen(QColor("#000000")))
                            path_item.setBrush(QBrush(QColor("#000000")))
                            path_item.setZValue(11)  # Ensure it renders above dots
                            path_item.setParentItem(dot)  # Attach to the dot

                            path.set("data-processed", "true")  # Prevents duplicate renderings

                        except Exception as e:
                            print(f"Error processing path in load_groups: {e}")

                    # Store elements together so they move as a unit
                    self.groups.append((dot, circle, text, polygon, path, path_item))

    def save_changes(self):
        """Save updated positions of dots and associated elements (text, polygon, path) to the SVG file."""
        svg_ns = "http://www.w3.org/2000/svg"
        ET.register_namespace("", svg_ns)

        for dot, circle, text, polygon, path, path_item in self.groups:
            new_cx = dot.sceneBoundingRect().center().x()
            new_cy = dot.sceneBoundingRect().center().y()

            old_cx = float(circle.get("cx"))
            old_cy = float(circle.get("cy"))

            dx = new_cx - old_cx
            dy = new_cy - old_cy

            circle.set("cx", str(new_cx))
            circle.set("cy", str(new_cy))

            if text is not None:
                transform_values = text.get("transform").split()
                old_x = float(transform_values[-2])
                old_y = float(transform_values[-1].replace(")", ""))

                new_x = old_x + dx
                new_y = old_y + dy

                text.set("transform", f"matrix(1 0 0 1 {new_x} {new_y})")

            if polygon is not None:
                original_points = polygon.get("points").split()
                adjusted_points = [
                    f"{float(p.split(',')[0]) + dx},{float(p.split(',')[1]) + dy}"
                    for p in original_points
                ]
                polygon.set("points", " ".join(adjusted_points))

            if path is not None:
                d_attr = path.get("d", "")
                try:
                    parsed_path = svg_path.parse_path(d_attr)
                    adjusted_d = []

                    for element in parsed_path:
                        if isinstance(element, Move):
                            adjusted_d.append(f"M {element.start.real + dx},{element.start.imag + dy}")
                        elif isinstance(element, Line):
                            adjusted_d.append(f"L {element.end.real + dx},{element.end.imag + dy}")
                        elif isinstance(element, CubicBezier):
                            adjusted_d.append(
                                f"C {element.control1.real + dx},{element.control1.imag + dy} "
                                f"{element.control2.real + dx},{element.control2.imag + dy} "
                                f"{element.end.real + dx},{element.end.imag + dy}"
                            )
                        elif isinstance(element, Close):
                            adjusted_d.append("Z")  # Close path remains unchanged

                    updated_path = " ".join(adjusted_d)
                    path.set("d", updated_path)

                except Exception as e:
                    print(f"Error updating path in save_changes: {e}")

        xml_str = ET.tostring(self.svg_tree.getroot(), encoding="utf-8").decode("utf-8")
        parsed_xml = minidom.parseString(xml_str)
        pretty_xml = parsed_xml.toprettyxml(indent="  ")
        pretty_xml = "\n".join([line for line in pretty_xml.splitlines() if line.strip()])

        with open(self.output_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)

        QMessageBox.information(self, "Success", f"Changes saved to {self.output_file}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = EditableSVG("example.svg", "output_updated.svg")
    editor.exec()
    sys.exit(app.exec())