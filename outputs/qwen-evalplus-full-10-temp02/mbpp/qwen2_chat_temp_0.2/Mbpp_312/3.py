import math

def volume_cone(radius, height):
    """
    Calculate the volume of a cone.
    
    Parameters:
    radius (float): The radius of the base of the cone.
    height (float): The height of the cone.
    
    Returns:
    float: The volume of the cone.
    """
    volume = (math.pi * radius ** 2) * height
    return volume
