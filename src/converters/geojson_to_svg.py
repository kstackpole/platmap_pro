#!/usr/bin/env python3
"""
geojson_to_svg.py

This module provides functionality to convert GeoJSON files containing lot, grass, water, and road data 
into an SVG format suitable for creating interactive maps. It supports scaling, grouping, and 
organizing SVG elements.

Author: Kyle Stackpole
Copyright: 2024, Kyle Stackpole
Version: 1.0.3
Email: kyle.stackpole@mdch.com
Status: Development
"""

import pandas as pd
import geopandas as gpd
import xml.etree.ElementTree as ET
from shapely.geometry import MultiPolygon, Polygon
from utils.transformations import transform_coords

def geojson_to_svg(lots_files, grass_files, water_files, road_files, output_file, canvas_width=1440, canvas_height=840):
    """Convert GeoJSON files into a proportional SVG with consistent aspect ratio scaling."""
    # Combine all GeoJSON files into GeoDataFrames
    lots_gdf = combine_geojson_files(lots_files)
    grass_gdf = combine_geojson_files(grass_files)
    water_gdf = combine_geojson_files(water_files)
    road_gdf = combine_geojson_files(road_files)

    # Combine all geometries for bounding box calculation
    all_gdfs = [gdf for gdf in [lots_gdf, grass_gdf, water_gdf, road_gdf] if gdf is not None and not gdf.empty]
    if not all_gdfs:
        raise ValueError("No valid geometries found in the input files.")

    combined_bounds = gpd.GeoDataFrame(pd.concat(all_gdfs)).total_bounds
    minx, miny, maxx, maxy = combined_bounds

    # Calculate the width and height of the geometry bounds
    geom_width = maxx - minx
    geom_height = maxy - miny

    # Calculate proportional scaling factor
    scale_x = canvas_width / geom_width
    scale_y = canvas_height / geom_height
    scale = min(scale_x, scale_y)  # Use the smaller scaling factor to maintain aspect ratio

    # Calculate padding to center the geometry on the canvas
    x_padding = (canvas_width - (geom_width * scale)) / 2
    y_padding = (canvas_height - (geom_height * scale)) / 2

    # Create the SVG file with dots
    svg_with_dots = create_svg_root(canvas_width, canvas_height)
    populate_svg(svg_with_dots, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots=True)
    save_svg(svg_with_dots, output_file)

    # Create the SVG file without dots
    svg_without_dots = create_svg_root(canvas_width, canvas_height)
    populate_svg(svg_without_dots, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots=False)
    print_output_file = output_file.replace(".svg", "_print.svg")
    save_svg(svg_without_dots, print_output_file)

def create_svg_root(canvas_width, canvas_height):
    """Create the root SVG element."""
    return ET.Element("svg", {
        "version": "1.1",
        "xmlns": "http://www.w3.org/2000/svg",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "x": "0px",
        "y": "0px",
        "width": f"{canvas_width}px",
        "height": f"{canvas_height}px",
        "viewBox": f"0 0 {canvas_width} {canvas_height}",
        "xml:space": "preserve",
        "preserveAspectRatio": "xMidYMid meet"
    })

def populate_svg(svg, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots):
    """Populate the SVG with layers and lots."""
    # Add grass layer first
    if grass_gdf is not None and not grass_gdf.empty:
        add_layer_to_svg(grass_gdf, "grass", "#808057", minx, miny, maxy, scale, x_padding, y_padding, svg)

    # Add roads layer on top of grass
    if road_gdf is not None and not road_gdf.empty:
        add_layer_to_svg(road_gdf, "roads", "#FFFFFF", minx, miny, maxy, scale, x_padding, y_padding, svg)

    # Add water layer
    if water_gdf is not None and not water_gdf.empty:
        add_layer_to_svg(water_gdf, "water", "#73B0CC", minx, miny, maxy, scale, x_padding, y_padding, svg)

    # Add lots layer
    if lots_gdf is not None and not lots_gdf.empty:
        process_lots(lots_gdf, svg, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots)


def process_lots(gdf, svg, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots):
    """Group lots by community and process them into nested groups, including legal lot text and optionally dots."""
    lots_group = ET.SubElement(svg, "g", {"id": "lots"})
    text_group = ET.SubElement(svg, "g", {"id": "text"})
    unused_group = ET.SubElement(lots_group, "g", {"id": "unused", "class": "notavailable"})
    community_groups = {}
    community_text_groups = {}

    for _, row in gdf.iterrows():
        community_id = row['excel_Community'].strip()
        lot_job = row['excel_Lot Job'].strip()
        legal_lot = row.get('excel_Legal Lot', '').strip()

        # Handle unused lots
        if not lot_job.isdigit():
            process_geometry(row.geometry, minx, miny, maxy, scale, x_padding, y_padding, unused_group, "#D9CFC0")
            continue

        # Create community group if it doesn't exist
        if community_id not in community_groups:
            community_group = ET.SubElement(lots_group, "g", {"id": f"{community_id}-lots"})
            community_groups[community_id] = community_group

            # Create a corresponding text group for the community
            community_text_group = ET.SubElement(text_group, "g", {"id": f"{community_id}-text"})
            community_text_groups[community_id] = community_text_group

        # Add lot to community group
        lot_group = ET.SubElement(community_groups[community_id], "g", {
            "id": f"{community_id}-{lot_job}",
            "class": "notavailable"
        })
        process_geometry(row.geometry, minx, miny, maxy, scale, x_padding, y_padding, lot_group, "#DBCDAE")

        # Add legal lot number text to the text group
        centroid = row.geometry.centroid
        cx, cy = transform_coords(centroid.x, centroid.y, minx, miny, scale, maxy, x_padding, y_padding)

        # Ensure text is positioned within the canvas
        if 0 <= cx <= canvas_width and 0 <= cy <= canvas_height:
            text_element = ET.SubElement(community_text_groups[community_id], "text", {
                "x": str(cx),
                "y": str(cy),
                "font-size": "12px",
                "text-anchor": "middle",
                "fill": "#000000",
                "data-lot-id": f"{community_id}-{lot_job}"
            })
            text_element.text = legal_lot

        # Optionally add dynamic dots for constStatus, lotPremium, and soldStatus
        if include_dots:
            offsets = {
                "constStatus": (-5, 0),  # Left of the centroid
                "lotPremium": (0, -5),  # Above the centroid
                "soldStatus": (5, 0)    # Right of the centroid
            }

            for dot_type, (dx, dy) in offsets.items():
                dot_group = ET.SubElement(lot_group, "g", {"class": dot_type})
                
                # Create the circle element for the dot
                ET.SubElement(dot_group, "circle", {
                    "cx": str(cx + dx),
                    "cy": str(cy + dy),
                    "r": "4",
                    "fill": "#FFFFFF" if dot_type != "constStatus" else "#454546",
                    "stroke": "black",
                    "stroke-width": "1"
                })

                # Add an empty text element for constStatus and lotPremium
                if dot_type in ["constStatus", "lotPremium"]:
                    ET.SubElement(dot_group, "text", {
                        "x": str(cx + dx),
                        "y": str(cy + dy),  # Adjust the Y position slightly above the circle
                        "font-size": "10px",
                        "text-anchor": "middle",
                        "fill": "#000000",
                    }).text = ""  # Empty text content


def add_layer_to_svg(gdf, layer_id, fill_color, minx, miny, maxy, scale, x_padding, y_padding, svg):
    """Add a GeoDataFrame layer to the SVG with proportional scaling."""
    layer_group = ET.SubElement(svg, "g", {"id": layer_id, "class": layer_id})
    for _, row in gdf.iterrows():
        process_geometry(
            row.geometry, minx, miny, maxy, scale, x_padding, y_padding, layer_group, fill_color
        )

def process_geometry(geometry, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill):
    """Process and write geometry as SVG."""
    if geometry is None or geometry.is_empty:
        print("Skipping empty geometry")
        return
    if geometry.geom_type == 'Polygon':
        write_polygon(geometry, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill)
    elif geometry.geom_type == 'MultiPolygon':
        for polygon in geometry.geoms:
            write_polygon(polygon, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill)
    else:
        print(f"Unsupported geometry type: {geometry.geom_type}")

def write_polygon(polygon, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill):
    """Write a single polygon to the SVG with scaling."""
    coords = " ".join(
        f"{(x - minx) * scale + x_padding},{((maxy - y) * scale + y_padding)}"
        for x, y in polygon.exterior.coords
    )
    ET.SubElement(parent_group, "path", {
        "d": f"M {coords} Z",
        "fill": fill,
        "stroke": "black",
        "stroke-width": "1"
    })

def combine_geojson_files(files):
    """Combine multiple GeoJSON files into a single GeoDataFrame and reproject to a planar CRS."""
    if not files:
        return None
    gdf = gpd.GeoDataFrame(
        pd.concat([gpd.read_file(file) for file in files], ignore_index=True)
    )
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)  # Default to WGS 84 if CRS is not set
    gdf = gdf.to_crs("EPSG:3857")  # Reproject to Web Mercator
    return gdf

def save_svg(svg, output_file):
    """Save the SVG tree to a file with pretty-printing."""
    tree = ET.ElementTree(svg)
    with open(output_file, "wb") as f:
        tree.write(f, encoding="utf-8", xml_declaration=True)

    # Pretty-print with indentation
    from xml.dom import minidom
    with open(output_file, "r", encoding="utf-8") as f:
        pretty_svg = minidom.parseString(f.read()).toprettyxml(indent="    ")
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(pretty_svg)
