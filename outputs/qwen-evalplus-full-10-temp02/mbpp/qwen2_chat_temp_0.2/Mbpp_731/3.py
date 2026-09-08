import math

def lateralsurface_cone(radius, height):
    """
    Calculate the lateral surface area of a cone given its radius and height.
    
    Parameters:
    radius (float): The radius of the base of the cone.
    height (float): The height of the cone.
    
    Returns:
    float: The lateral surface area of the cone.
    """
    lateral_surface_area = 2 * math.pi * radius * height
    return lateral_surface_area