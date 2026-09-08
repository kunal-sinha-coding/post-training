def polar_rect(rho, theta):
    """
    Convert polar coordinates to rectangular coordinates.
    
    Parameters:
    rho (float): The radial distance from the origin.
    theta (float): The angle in radians from the positive x-axis.
    
    Returns:
    tuple: A tuple containing the rectangular coordinates (x, y).
    """
    x = rho * math.cos(theta)
    y = rho * math.sin(theta)
    return (x, y)
