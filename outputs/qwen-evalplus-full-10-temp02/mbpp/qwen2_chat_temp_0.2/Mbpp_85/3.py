import math

def surfacearea_sphere(radius):
    """
    Calculate the surface area of a sphere given its radius.
    
    Parameters:
    radius (float): The radius of the sphere.
    
    Returns:
    float: The surface area of the sphere.
    """
    surface_area = 4 * math.pi * radius ** 2
    return surface_area
