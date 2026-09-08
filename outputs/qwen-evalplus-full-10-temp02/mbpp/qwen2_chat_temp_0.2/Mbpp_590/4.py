def polar_rect(r, theta):
    """
    Convert polar coordinates to rectangular coordinates.
    
    Parameters:
    r (float): The radius of the circle.
    theta (float): The angle in radians from the positive x-axis.
    
    Returns:
    tuple: A tuple containing the rectangular coordinates (x, y).
    """
    x = r * math.cos(theta)
    y = r * math.sin(theta)
    return (x, y)
