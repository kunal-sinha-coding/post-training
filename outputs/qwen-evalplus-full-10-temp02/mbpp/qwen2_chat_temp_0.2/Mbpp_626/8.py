import math

def triangle_area(radius):
    """
    Calculate the area of the largest triangle that can be inscribed in a semicircle with a given radius.
    
    Parameters:
    radius (float): The radius of the semicircle.
    
    Returns:
    float: The area of the largest triangle.
    """
    # Calculate the area of the semicircle
    semicircle_area = math.pi * radius ** 2
    
    # Since the largest triangle inscribed in a semicircle can be formed by the largest base and the largest height
    # The largest base is the diameter of the semicircle, which is 2 * radius
    # The largest height is the radius of the semicircle
    largest_base = 2 * radius
    largest_height = radius
    
    # Calculate the area of the largest triangle
    largest_triangle_area = 0.5 * largest_base * largest_height
    
    return largest_triangle_area