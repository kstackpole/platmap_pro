def transform_coords(x, y, minx, miny, scale, maxy, x_padding, y_padding):
    """Transform coordinates with scaling, centering, and flipping Y-axis for SVG."""
    scaled_x = (x - minx) * scale + x_padding
    scaled_y = (maxy - y) * scale + y_padding
    return scaled_x, scaled_y
