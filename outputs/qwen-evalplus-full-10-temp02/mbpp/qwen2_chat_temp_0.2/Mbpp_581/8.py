def surface_Area(base_edge, height):
    """
    Calculate the surface area of a square pyramid with a given base edge and height.
    
    Parameters:
    base_edge (float): The length of the base edge of the pyramid.
    height (float): The height of the pyramid.
    
    Returns:
    float: The surface area of the pyramid.
    """
    # Calculate the slant height of the pyramid
    slant_height = (base_edge ** 2 + height ** 2) ** 0.5
    
    # Calculate the surface area of the pyramid
    surface_area = 2 * (base_edge * height + base_edge * slant_height + height * slant_height)
    
    return surface_area