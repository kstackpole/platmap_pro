import os
import logging
import pandas as pd
import geopandas as gpd

logging.basicConfig(level=logging.DEBUG)

def read_geojson_files(file_paths):
    """Load multiple GeoJSON files and combine them into a single GeoDataFrame."""
    if not file_paths:
        logging.warning("No files provided for reading.")
        return None

    try:
        gdfs = [gpd.read_file(file) for file in file_paths]
        combined_gdf = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True))
        if combined_gdf.crs is None:
            combined_gdf.set_crs("EPSG:4326", inplace=True)
        return combined_gdf.to_crs("EPSG:3857")
    except Exception as e:
        logging.error(f"Error reading GeoJSON files: {e}")
        return None

def save_svg(svg_element, output_file):
    """Save an XML Element as an SVG file with pretty formatting."""
    import xml.dom.minidom as minidom
    import xml.etree.ElementTree as ET

    xml_str = ET.tostring(svg_element, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    pretty_xml = parsed_xml.toprettyxml(indent="  ")

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(pretty_xml)
        logging.info(f"SVG saved to {output_file}")
    except Exception as e:
        logging.error(f"Failed to save SVG: {e}")
