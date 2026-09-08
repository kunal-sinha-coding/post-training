import math

def volume_sphere(radius):
    """
    Calculate the volume of a sphere given its radius.
    
    Parameters:
    radius (float): The radius of the sphere.
    
    Returns:
    float: The volume of the sphere.
    """
    volume = (4/3) * math.pi * radius ** 3
    return volume
