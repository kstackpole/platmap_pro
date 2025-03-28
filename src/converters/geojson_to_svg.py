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
import os
import geopandas as gpd
import xml.etree.ElementTree as ET
from shapely.geometry import MultiPolygon, Polygon
from utils.transformations import transform_coords
from xml.etree.ElementTree import fromstring

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

    output_file_base = os.path.splitext(output_file_base)[0]  # Remove any existing extension
    # Generate print version
    svg_print = create_svg_root(canvas_width, canvas_height)
    populate_svg(svg_print, lots_gdf, grass_gdf, water_gdf, road_gdf, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots=True, colorize=True)
    # Generate print version
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

    if road_gdf is not None and not road_gdf.empty:
        add_layer_to_svg(road_gdf, "road", "road", "#DBCDAE", minx, miny, maxy, scale, x_padding, y_padding, open_roads_group)

    if grass_gdf is not None and not grass_gdf.empty:
        add_layer_to_svg(grass_gdf, "grass", "grass", "#808057", minx, miny, maxy, scale, x_padding, y_padding, open_roads_group)
    
    if water_gdf is not None and not water_gdf.empty:
        add_layer_to_svg(water_gdf, "lakes", "lakes", "#73B0CC", minx, miny, maxy, scale, x_padding, y_padding, open_roads_group)

    if lots_gdf is not None and not lots_gdf.empty:
        process_lots(lots_gdf, svg, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots, colorize)

def process_lots(gdf, svg, minx, miny, maxy, scale, x_padding, y_padding, canvas_width, canvas_height, include_dots, colorize):
    compass_rose_svg = '''
        <g id="compass_rose" transform="matrix(1,0,0,1,590,300)">
            <polygon opacity="0.5" fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="724.8,394.2 722.3,394.3 721.1,394.4 
                719.9,394.7 717.5,395.3 715.3,396.1 713.1,397.1 711.1,398.3 709.2,399.8 707.4,401.4 705.9,403.2 704.5,405.1 703.2,407.1 
                702.2,409.2 701.4,411.4 700.7,413.9 700.3,416.3 700.2,418.8 700.3,421.2 700.7,423.7 701.4,426 702.2,428.2 703.2,430.4 
                704.5,432.4 705.9,434.3 707.4,436.1 709.2,437.6 711.1,439.1 713.1,440.3 715.3,441.3 717.5,442.2 719.9,442.8 722.3,443.1 
                724.8,443.3 727.2,443.1 729.8,442.8 732,442.2 734.3,441.3 736.5,440.3 738.4,439.1 740.3,437.6 742.1,436.1 743.7,434.3 
                745.1,432.4 746.3,430.4 747.4,428.2 748.2,426 748.8,423.7 749.1,421.2 749.3,418.8 749.1,416.3 748.8,413.9 748.2,411.4 
                747.4,409.2 746.3,407.1 745.1,405.1 743.7,403.2 742.1,401.4 740.3,399.8 738.4,398.3 736.5,397.1 734.3,396.1 732,395.3 
                729.8,394.7 727.2,394.3 724.8,394.2 	"/>
            <polygon fill="none" stroke="#FFFFFF" stroke-width="0.6776" points="724.8,394.2 722.3,394.3 721.1,394.4 719.9,394.7 
                717.5,395.3 715.3,396.1 713.1,397.1 711.1,398.3 709.2,399.8 707.4,401.4 705.9,403.2 704.5,405.1 703.2,407.1 702.2,409.2 
                701.4,411.4 700.7,413.9 700.3,416.3 700.2,418.8 700.3,421.2 700.7,423.7 701.4,426 702.2,428.2 703.2,430.4 704.5,432.4 
                705.9,434.3 707.4,436.1 709.2,437.6 711.1,439.1 713.1,440.3 715.3,441.3 717.5,442.2 719.9,442.8 722.3,443.1 724.8,443.3 
                727.2,443.1 729.8,442.8 732,442.2 734.3,441.3 736.5,440.3 738.4,439.1 740.3,437.6 742.1,436.1 743.7,434.3 745.1,432.4 
                746.3,430.4 747.4,428.2 748.2,426 748.8,423.7 749.1,421.2 749.3,418.8 749.1,416.3 748.8,413.9 748.2,411.4 747.4,409.2 
                746.3,407.1 745.1,405.1 743.7,403.2 742.1,401.4 740.3,399.8 738.4,398.3 736.5,397.1 734.3,396.1 732,395.3 729.8,394.7 
                727.2,394.3 724.8,394.2 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="765.7,418.8 734.2,414.8 734.9,418.8 765.7,418.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="724.8,377.8 721,409.3 724.8,408.6 724.8,377.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="724.8,377.8 728.7,409.3 724.8,408.6 724.8,377.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="724.8,459.7 728.7,428.1 724.8,428.9 724.8,459.7 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="724.8,459.7 721,428.1 724.8,428.9 724.8,459.7 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="695.9,389.8 715.4,414.9 717.7,411.6 695.9,389.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="695.9,389.8 721,409.2 717.7,411.6 695.9,389.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="753.7,447.7 734.2,422.5 732,425.9 753.7,447.7 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="753.5,447.7 728.6,428.1 732,425.9 753.5,447.7 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="683.8,418.8 715.4,422.7 714.6,418.8 683.8,418.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="683.8,418.8 715.4,414.8 714.6,418.8 683.8,418.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="765.7,418.8 734.2,422.7 734.9,418.8 765.7,418.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="695.9,447.7 721,428.1 717.7,425.9 695.9,447.7 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="695.9,447.7 715.4,422.4 717.7,425.9 695.9,447.7 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#FFFFFF" points="753.7,389.8 728.6,409.2 732,411.6 753.7,389.8 	"/>
            <polygon fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="753.7,389.8 734.2,414.9 732,411.6 753.7,389.8 	"/>
            <path fill="#422D16" d="M720.8,373.8c0,1.2,0.2,1.6,0.5,1.7c0.3,0.1,0.5,0.1,0.8,0.1c0.2,0,0.3,0,0.3,0.1c0,0.1-0.1,0.2-0.3,0.2
                c-1,0-1.6,0-1.9,0c-0.1,0-0.8,0-1.6,0c-0.2,0-0.3,0-0.3-0.2c0-0.1,0.1-0.1,0.2-0.1c0.2,0,0.5,0,0.7-0.1c0.4-0.1,0.5-0.6,0.5-1.9
                l0.1-9c0-0.3,0-0.5,0.2-0.5c0.2,0,0.3,0.2,0.6,0.5c0.2,0.2,2.5,2.7,4.7,4.9c1,1,3.1,3.2,3.3,3.5h0.1l-0.2-6.8
                c0-0.9-0.2-1.2-0.5-1.4c-0.2-0.1-0.6-0.1-0.8-0.1c-0.2,0-0.2,0-0.2-0.1c0-0.1,0.2-0.1,0.4-0.1c0.8,0,1.5,0,1.8,0c0.2,0,0.7,0,1.5,0
                c0.2,0,0.3,0,0.3,0.1c0,0.1-0.1,0.1-0.3,0.1c-0.2,0-0.3,0-0.5,0c-0.4,0.1-0.5,0.4-0.6,1.3l-0.2,9.6c0,0.3-0.1,0.5-0.2,0.5
                c-0.2,0-0.3-0.2-0.5-0.3c-1-0.9-2.9-2.9-4.5-4.5c-1.7-1.6-3.3-3.5-3.6-3.8h0L720.8,373.8z"/>
            <path fill="#422D16" d="M722.4,474.6c-0.2-0.1-0.3-0.2-0.3-0.5c0-0.8,0.1-1.7,0.1-2c0-0.2,0.1-0.4,0.2-0.4c0.1,0,0.2,0.1,0.2,0.3
                c0,0.2,0.1,0.5,0.1,0.8c0.3,1.1,1.2,1.5,2.2,1.5c1.4,0,2-0.9,2-1.7c0-0.7-0.2-1.5-1.5-2.4l-0.7-0.5c-1.7-1.3-2.2-2.4-2.2-3.6
                c0-1.7,1.4-2.9,3.5-2.9c1,0,1.6,0.2,2,0.3c0.1,0,0.2,0.1,0.2,0.2c0,0.2-0.1,0.6-0.1,1.8c0,0.3,0,0.5-0.2,0.5
                c-0.1,0-0.2-0.1-0.2-0.3c0-0.1-0.1-0.6-0.4-1c-0.2-0.3-0.7-0.7-1.7-0.7c-1.1,0-1.8,0.7-1.8,1.6c0,0.7,0.3,1.2,1.6,2.2l0.4,0.3
                c1.8,1.4,2.5,2.4,2.5,3.9c0,0.9-0.3,1.9-1.4,2.6c-0.8,0.5-1.6,0.6-2.4,0.6C723.8,475,723.1,474.9,722.4,474.6z"/>
            <path fill="#422D16" d="M768.4,417.1c0-2.3,0-2.7,0-3.2c0-0.5-0.2-0.8-0.7-0.9c-0.1,0-0.4,0-0.6,0c-0.2,0-0.3,0-0.3-0.1
                c0-0.1,0.1-0.1,0.3-0.1c0.8,0,1.8,0,2.2,0c0.5,0,3.5,0,3.8,0c0.3,0,0.5-0.1,0.7-0.1c0.1,0,0.2-0.1,0.2-0.1c0.1,0,0.1,0.1,0.1,0.1
                c0,0.1-0.1,0.3-0.1,1c0,0.2,0,0.8-0.1,1c0,0.1,0,0.2-0.2,0.2c-0.1,0-0.1-0.1-0.1-0.2c0-0.1,0-0.4-0.1-0.5c-0.1-0.3-0.3-0.5-1-0.5
                c-0.3,0-1.8-0.1-2.2-0.1c-0.1,0-0.1,0-0.1,0.2v3.8c0,0.1,0,0.2,0.1,0.2c0.3,0,2.1,0,2.4,0c0.4,0,0.6-0.1,0.7-0.2
                c0.1-0.1,0.2-0.2,0.2-0.2c0.1,0,0.1,0,0.1,0.1c0,0.1-0.1,0.3-0.1,1.1c0,0.3-0.1,0.9-0.1,1c0,0.1,0,0.3-0.1,0.3
                c-0.1,0-0.1-0.1-0.1-0.1c0-0.2,0-0.4-0.1-0.5c-0.1-0.3-0.3-0.5-0.9-0.6c-0.3,0-1.8,0-2.2,0c-0.1,0-0.1,0.1-0.1,0.2v1.2
                c0,0.5,0,1.9,0,2.4c0,1,0.3,1.3,1.8,1.3c0.4,0,1,0,1.4-0.2c0.4-0.2,0.6-0.5,0.7-1.1c0-0.2,0.1-0.2,0.2-0.2c0.1,0,0.1,0.1,0.1,0.3
                c0,0.3-0.1,1.4-0.2,1.7c-0.1,0.4-0.2,0.4-0.8,0.4c-2.3,0-3.3-0.1-4.2-0.1c-0.3,0-1.3,0-1.9,0c-0.2,0-0.3,0-0.3-0.2
                c0-0.1,0.1-0.1,0.2-0.1c0.2,0,0.4,0,0.5-0.1c0.3-0.1,0.4-0.4,0.4-0.8c0.1-0.6,0.1-1.8,0.1-3.2V417.1z"/>
            <path fill="#422D16" d="M667.9,414.1c-0.2-0.6-0.3-0.9-0.6-1.1c-0.2-0.1-0.5-0.1-0.6-0.1c-0.2,0-0.2,0-0.2-0.1
                c0-0.1,0.1-0.1,0.3-0.1c0.8,0,1.6,0,1.8,0c0.1,0,0.8,0,1.7,0c0.2,0,0.3,0,0.3,0.1c0,0.1-0.1,0.1-0.3,0.1c-0.1,0-0.3,0-0.4,0.1
                c-0.1,0.1-0.2,0.2-0.2,0.3c0,0.2,0.2,0.7,0.3,1.4c0.3,1,1.7,5.6,1.9,6.4h0l2.9-7.9c0.2-0.4,0.3-0.5,0.4-0.5c0.2,0,0.2,0.2,0.4,0.7
                l3.2,7.6h0c0.3-1,1.5-5,2-6.8c0.1-0.3,0.2-0.7,0.2-0.9c0-0.2-0.1-0.5-0.7-0.5c-0.2,0-0.3,0-0.3-0.1c0-0.1,0.1-0.1,0.3-0.1
                c0.8,0,1.4,0,1.6,0c0.1,0,0.8,0,1.3,0c0.2,0,0.3,0,0.3,0.1c0,0.1-0.1,0.2-0.2,0.2c-0.2,0-0.4,0-0.5,0.1c-0.4,0.1-0.5,0.7-0.9,1.6
                c-0.7,1.9-2.3,6.7-3,9c-0.2,0.5-0.2,0.7-0.4,0.7c-0.2,0-0.2-0.2-0.5-0.7l-3.2-7.6h0c-0.3,0.8-2.3,6.1-3,7.5
                c-0.3,0.6-0.4,0.8-0.5,0.8c-0.2,0-0.2-0.2-0.3-0.6L667.9,414.1z"/>
            <polyline fill-rule="evenodd" clip-rule="evenodd" fill="#422D16" points="724.8,408.4 724.8,408.4 724.8,408.4 723.8,408.4 
                722.7,408.6 722.7,408.6 721.8,408.8 720.8,409.2 720.8,409.2 719.9,409.6 719.9,409.6 719,410.2 718.2,410.7 718.2,410.7 
                717.5,411.4 717.5,411.4 716.8,412.2 716.8,412.2 716.2,413 715.7,413.8 715.7,413.8 715.2,414.7 715.2,414.7 714.9,415.7 
                714.9,415.7 714.7,416.7 714.4,417.7 714.4,417.7 714.4,418.8 714.4,419.8 714.4,419.8 714.7,420.9 714.9,421.8 714.9,421.8 
                715.2,422.8 715.2,422.8 715.7,423.7 716.2,424.6 716.2,424.6 716.8,425.4 716.8,425.4 717.5,426.1 718.2,426.8 718.2,426.8 
                719,427.4 719.9,427.9 719.9,427.9 720.8,428.3 720.8,428.3 721.8,428.7 722.7,429 723.8,429.1 723.8,429.1 724.8,429.2 726.9,429 
                728.9,428.3 728.9,428.3 729.7,427.9 729.7,427.9 730.6,427.4 730.6,427.4 732.1,426.1 732.1,426.1 733.4,424.6 733.9,423.7 
                734.3,422.8 734.7,421.8 734.7,421.8 735,420.9 735.2,418.8 735.2,418.8 735.1,417.7 735.1,417.7 735,416.7 735,416.7 734.7,415.7 
                734.7,415.7 734.3,414.7 733.9,413.8 733.4,413 732.8,412.2 732.8,412.2 732.1,411.4 731.4,410.7 731.4,410.7 730.6,410.2 
                729.7,409.6 729.7,409.6 728.9,409.2 728.9,409.2 727.9,408.8 726.9,408.6 726.9,408.6 725.8,408.4 724.8,408.4 724.8,408.4 	"/>
        </g>
        '''
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
            const_text = "300"
            premium_text = "10k"
            data_group = ET.SubElement(lot_group, "g")
            # Construction Status Group
            const_status_group = ET.SubElement(data_group, "g", {"class": "constStatus"})
            ET.SubElement(const_status_group, "circle", {
                "fill": "#444445",
                "cx": str(cx + 5),
                "cy": str(cy),
                "r": "4"
            })
            ET.SubElement(const_status_group, "text", {
                "transform": f"matrix(1 0 0 1 {cx + 2.6} {cy + 1.2})",
                "fill": "#FFFFFF",
                "font-family": "'ArialMT'",
                "font-size": "4px"
            }).text = const_text

            # Lot Premium Group
            lot_premium_group = ET.SubElement(data_group, "g", {"class": "lotPremium"})
            ET.SubElement(lot_premium_group, "circle", {
                "fill": "#FFFFFF",
                "cx": str(cx),
                "cy": str(cy - 5),  # Moves up by 5px
                "r": "3.8"
            })
            ET.SubElement(lot_premium_group, "polygon", {
                "points": f"{cx+1.2},{cy-6.7} {cx+4},{cy-6.3} {cx+2},{cy-4.3} {cx+2.5},{cy-1.6} "
                        f"{cx},{cy-2.9} {cx-2.4},{cy-1.6} {cx-2},{cy-4.3} {cx-3.9},{cy-6.2} "
                        f"{cx-1.2},{cy-6.6} {cx},{cy-9.1}"
            })
            ET.SubElement(lot_premium_group, "text", {
                "transform": f"matrix(1 0 0 1 {cx-1.9} {cy-3.8})",
                "fill": "#FFFFFF",
                "font-family": "'ArialMT'",
                "font-size": "2.3px"
            }).text = premium_text

            # Sold Status Group
            sold_status_group = ET.SubElement(data_group, "g", {"class": "soldStatus"})
            ET.SubElement(sold_status_group, "circle", {
                "fill": "#FFFFFF",
                "cx": str(cx - 5),  # Moves left by 5px
                "cy": str(cy),
                "r": "4"
            })

            # House icon inside Sold Status
            sold_status_path_group = ET.SubElement(sold_status_group, "g")
            ET.SubElement(sold_status_path_group, "path", {
                "d": (f"M{cx-7.5},{cy}l2.5-2.2l2.5,2.2c0,0,0.1,0,0.1,0c0,0,0.1,0,0.1-0.1c0.1-0.1,0.1-0.2,0-0.2l-2.6-2.3c-0.1-0.1-0.2-0.1-0.2,0 "
                    f"l-0.9,0.8v-0.3c0-0.2-0.2-0.3-0.3-0.3c-0.2,0-0.3,0.2-0.3,0.3v0.9l-1,0.9c-0.1,0.1-0.1,0.2,0,0.2 "
                    f"C{cx-7.7},{cy+0.1},{cx-7.6},{cy+0.1},{cx-7.5},{cy}z M{cx-5.7},{cy+0.8}h1.4v1.7h1c0.2,0,0.3-0.2,0.3-0.3V{cy+0.5} "
                    f"c0-0.1,0-0.2-0.1-0.3l-1.7-1.4c-0.1-0.1-0.1-0.1-0.2-0.1s-0.2,0-0.2,0.1l-1.7,1.4c-0.1,0.1-0.1,0.2-0.1,0.3v1.7 "
                    f"c0,0.2,0.2,0.3,0.3,0.3h1V{cy+0.8}z"),
                "fill": "#000000"
            })


        if 0 <= cx <= canvas_width and 0 <= cy <= canvas_height:
            if colorize:
                transform_matrix = f"matrix(1 0 0 1 {cx} {cy + 4})"
                text_element = ET.SubElement(community_text_groups[community_id], "text", {
                    "transform": transform_matrix,
                    "font-size": "12px",
                    "text-anchor": "middle",
                    "fill": "#000000",
                    "font-family": "Futura PT Book, sans-serif",  # Ensure fallback font
                    "data-lot-id": f"{community_id}-{lot_job}"
                })
            else:
                transform_matrix = f"matrix(1 0 0 1 {cx - 6} {cy + 4})"
                text_element = ET.SubElement(community_text_groups[community_id], "text", {
                    "transform": transform_matrix,
                    "class": "commMapTxt",
                    "data-lot-id": f"{community_id}-{lot_job}"
                })
            text_element.text = legal_lot or "N/A"

    if unused_lots:
        unused_group = ET.SubElement(lots_group, "g", {"id": "unused", "class": "notavailable"})
        for geometry in unused_lots:
            process_geometry(geometry, minx, miny, maxy, scale, x_padding, y_padding, unused_group, "#d3d3d3")

    
    compass_rose_element = fromstring(compass_rose_svg)
    # Insert the compass rose after all community text groups within the text group
    community_groups = list(text_group)  # Get all child elements as a list

    # Find the last community group and insert the compass rose after it
    if community_groups:
        last_community_group = community_groups[-1]
        insert_position = community_groups.index(last_community_group) + 1
        text_group.insert(insert_position, compass_rose_element)
    else:
        # If no community groups exist, just append the compass rose normally
        text_group.append(compass_rose_element)

def add_layer_to_svg(gdf, layer_id, layer_class, fill_color, minx, miny, maxy, scale, x_padding, y_padding, parent_group):
    layer_group = ET.SubElement(parent_group, "g", {"id": layer_id, "class": layer_class})
    for _, row in gdf.iterrows():
        process_geometry(row.geometry, minx, miny, maxy, scale, x_padding, y_padding, layer_group, fill_color)

def process_geometry(geometry, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill, tolerance=0.2):
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == 'Polygon':
        geometry = geometry.simplify(tolerance, preserve_topology=True)  # Simplify geometry
        write_polygon(geometry, minx, miny, maxy, scale, x_padding, y_padding, parent_group, fill)
    elif geometry.geom_type == 'MultiPolygon':
        simplified_polygons = [poly.simplify(tolerance, preserve_topology=True) for poly in geometry.geoms]
        for polygon in simplified_polygons:
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