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

def geojson_to_svg(lots_files, grass_files, water_files, road_files, output_file_base, canvas_width=1440, canvas_height=840):
    lots_gdf = combine_geojson_files(lots_files)
    grass_gdf = combine_geojson_files(grass_files)
    water_gdf = combine_geojson_files(water_files)
    road_gdf = combine_geojson_files(road_files)

    all_gdfs = [gdf for gdf in [lots_gdf, grass_gdf, water_gdf, road_gdf] if gdf is not None and not gdf.empty]
    if not all_gdfs:
        raise ValueError("No valid geometries found in the input files.")

    combined_bounds = gpd.GeoDataFrame(pd.concat(all_gdfs)).total_bounds
    minx, miny, maxx, maxy = combined_bounds

    geom_width = maxx - minx
    geom_height = maxy - miny
    scale_x = canvas_width / geom_width
    scale_y = canvas_height / geom_height
    scale = min(scale_x, scale_y)

    x_padding = (canvas_width - (geom_width * scale)) / 2
    y_padding = (canvas_height - (geom_height * scale)) / 2

    # Generate print version
    svg_print = create_svg_root(canvas_width, canvas_height)
    populate_svg(svg_print, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots=True, colorize=True)
    save_svg(svg_print, f"{output_file_base}_print.svg")

    # Generate digital version
    svg_digital = create_svg_root(canvas_width, canvas_height)
    populate_svg(svg_digital, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots=True, colorize=False)
    save_svg(svg_digital, f"{output_file_base}_digital.svg")

def create_svg_root(canvas_width, canvas_height):
    return ET.Element("svg", {
        "version": "1.0",
        "xmlns": "http://www.w3.org/2000/svg",
        "xmlns:xlink": "http://www.w3.org/1999/xlink",
        "x": "0px",
        "y": "0px",
        "width": f"{canvas_width}px",
        "height": f"{canvas_height}px",
        "viewBox": f"0 0 {canvas_width} {canvas_height}",
        "xml:space": "preserve",
        "preserveAspectRatio": "xMinYMin",
        "style": "width:100%",
        "class": "tsPlotmap"
    })

def populate_svg(svg, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots, colorize):
    open_roads_group = ET.SubElement(svg, "g", {"id": "open_roads"})

    if grass_gdf is not None and not grass_gdf.empty:
        add_layer_to_svg(grass_gdf, "grass", "grass", "#808057", minx, miny, maxy, scale, x_padding, y_padding, open_roads_group)
    
    if road_gdf is not None and not road_gdf.empty:
        add_layer_to_svg(road_gdf, "road", "road", "#DBCDAE", minx, miny, maxy, scale, x_padding, y_padding, open_roads_group)
    
    if water_gdf is not None and not water_gdf.empty:
        add_layer_to_svg(water_gdf, "lakes", "lakes", "#73B0CC", minx, miny, maxy, scale, x_padding, y_padding, open_roads_group)

    if lots_gdf is not None and not lots_gdf.empty:
        process_lots(lots_gdf, svg, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots, colorize)

def process_lots(gdf, svg, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots, colorize):
    lots_group = ET.SubElement(svg, "g", {"id": "lots"})
    text_group = ET.SubElement(svg, "g", {"id": "text"})
    community_groups = {}
    community_text_groups = {}

    plan_colors = ["#6C889E", "#5D5249", "#B9AE5A", "#123449", "#076587", "#894747"]
    plan_color_map = {}
    default_color = "#DBCDAE"
    unused_lots = []

    for _, row in gdf.iterrows():
        community_id = str(row.get('excel_Community', '')).strip()
        lot_job = str(row.get('excel_Lot Job', '')).strip()
        legal_lot = str(row.get('excel_Legal Lot', '')).strip()
        plan = str(row.get('excel_Plan', '')).strip()
        lot_premium = row.get('excel_LotPremium', '').strip()
        sold_status = row.get('excel_SoldStatus', '').strip()
        const_status = row.get('excel_ConstStatus', '').strip()

        if not lot_job.isdigit():
            unused_lots.append(row.geometry)
            continue

        if community_id not in community_groups:
            community_group = ET.SubElement(lots_group, "g", {"id": f"{community_id}-lots"})
            community_groups[community_id] = community_group

            community_text_group = ET.SubElement(text_group, "g", {"id": f"{community_id}-text"})
            community_text_groups[community_id] = community_text_group

        if colorize:
            if plan not in plan_color_map and plan:
                plan_color_map[plan] = plan_colors[len(plan_color_map) % len(plan_colors)]
            fill_color = plan_color_map.get(plan, default_color)
        else:
            fill_color = default_color

        lot_group = ET.SubElement(community_groups[community_id], "g", {
            "id": f"{community_id}-{lot_job}",
            "class": "notavailable"
        })
        process_geometry(row.geometry, minx, miny, maxy, scale, x_padding, y_padding, lot_group, fill_color)

        centroid = row.geometry.centroid
        cx, cy = transform_coords(centroid.x, centroid.y, minx, miny, scale, maxy, x_padding, y_padding)

        if not colorize:
            data_group = ET.SubElement(lot_group, "g")
            const_status_group = ET.SubElement(data_group, "g", {"class": "constStatus"})
            ET.SubElement(const_status_group, "circle", {
                "fill": "#444445",
                "cx": str(cx + 5),
                "cy": str(cy),
                "r": "4"
            })
            ET.SubElement(const_status_group, "text", {
                "transform": f"matrix(1 0 0 1 {cx + 5} {cy})",
                "fill": "#FFFFFF",
                "font-family": "'ArialMT'",
                "font-size": "4px"
            })
            lot_premium_group = ET.SubElement(data_group, "g", {"class": "lotPremium"})
            ET.SubElement(lot_premium_group, "circle", {
                "fill": "#FFFFFF",
                "cx": str(cx - 5),
                "cy": str(cy),
                "r": "4"
            })
            ET.SubElement(lot_premium_group, "text", {
                "transform": f"matrix(1 0 0 1 {cx - 5} {cy})",
                "fill": "#FFFFFF",
                "font-family": "'ArialMT'",
                "font-size": "4px"
            })
            sold_status_group = ET.SubElement(data_group, "g", {"class": "soldStatus"})
            ET.SubElement(sold_status_group, "circle", {
                "fill": "#FFFFFF",
                "cx": str(cx),
                "cy": str(cy - 5),
                "r": "4"
            })
        if 0 <= cx <= canvas_width and 0 <= cy <= canvas_height:
            transform_matrix = f"matrix(1,0,0,1,{cx},{cy})"
            if colorize:
                text_element = ET.SubElement(community_text_groups[community_id], "text", {
                    "transform": transform_matrix,
                    "font-size": "12px",
                    "text-anchor": "middle",
                    "fill": "#000000",
                    "data-lot-id": f"{community_id}-{lot_job}"
                })
            else:
                text_element = ET.SubElement(community_text_groups[community_id], "text", {
                    "transform": transform_matrix,
                    "class": "commMapTxt",
                    "data-lot-id": f"{community_id}-{lot_job}"
                })
            text_element.text = legal_lot

    if unused_lots:
        unused_group = ET.SubElement(lots_group, "g", {"id": "unused", "class": "notavailable"})
        for geometry in unused_lots:
            process_geometry(geometry, minx, miny, maxy, scale, x_padding, y_padding, unused_group, "#d3d3d3")


def add_layer_to_svg(gdf, layer_id, layer_class, fill_color, minx, miny, maxy, scale, x_padding, y_padding, parent_group):
    layer_group = ET.SubElement(parent_group, "g", {"id": layer_id, "class": layer_class})
    for _, row in gdf.iterrows():
        process_geometry(row.geometry, minx, miny, maxy, scale, x_padding, y_padding, layer_group, fill_color)

def process_geometry(geometry, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill):
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == 'Polygon':
        write_polygon(geometry, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill)
    elif geometry.geom_type == 'MultiPolygon':
        for polygon in geometry.geoms:
            write_polygon(polygon, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill)

def write_polygon(polygon, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill):
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
    if not files:
        return None
    gdf = gpd.GeoDataFrame(pd.concat([gpd.read_file(file) for file in files], ignore_index=True))
    if gdf.crs is None:
        gdf.set_crs("EPSG:4326", inplace=True)
    return gdf.to_crs("EPSG:3857")

def save_svg(svg, output_file):
    tree = ET.ElementTree(svg)
    import xml.dom.minidom as minidom
    
    xml_str = ET.tostring(svg, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(pretty_xml)
