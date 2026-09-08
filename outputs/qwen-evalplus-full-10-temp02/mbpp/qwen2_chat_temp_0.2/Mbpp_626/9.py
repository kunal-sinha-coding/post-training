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
    
    # Since the largest triangle inscribed in a semicircle can be formed by the two largest circles
    # and the hypotenuse of the right triangle formed by the two circles, the area of the largest triangle
    # is half the area of the semicircle
    largest_triangle_area = semicircle_area / 2
    
    return largest_triangle_area