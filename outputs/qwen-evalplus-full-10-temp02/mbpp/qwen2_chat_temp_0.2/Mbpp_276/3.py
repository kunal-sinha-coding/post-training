import math

def volume_cylinder(radius, height):
    """
    Calculate the volume of a cylinder given its radius and height.
    
    Parameters:
    radius (float): The radius of the cylinder.
    height (float): The height of the cylinder.
    
    Returns:
    float: The volume of the cylinder.
    """
    volume = math.pi * radius ** 2 * height
    return volume
