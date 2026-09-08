import math

def triangle_area(radius):
    """
    Calculate the area of the largest triangle that can be inscribed in a semicircle with a given radius.
    
    Parameters:
    radius (float): The radius of the semicircle.
    
    Returns:
    float: The area of the largest triangle.
    """
    # Since the largest triangle inscribed in a semicircle has a base equal to the diameter of the semicircle,
    # the area of the triangle is half the diameter squared.
    diameter = 2 * radius
    area = 0.5 * diameter ** 2
    return area
