import math

def triangle_area(radius):
    """
    Calculate the area of the largest triangle that can be inscribed in a semicircle with a given radius.
    
    Parameters:
    radius (float): The radius of the semicircle.
    
    Returns:
    float: The area of the largest triangle.
    """
    # If the radius is negative, return None
    if radius < 0:
        return None
    
    # Calculate the semi-perimeter of the semicircle
    s = 2 * radius
    
    # Calculate the area of the triangle using Heron's formula
    area = math.sqrt(s * (s - radius) * (s - radius) * (s - radius))
    
    return area