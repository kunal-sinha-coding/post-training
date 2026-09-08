def sector_area(radius, angle):
    """
    Calculate the area of a sector given its radius and angle in degrees.
    
    Parameters:
    radius (float): The radius of the sector.
    angle (float): The angle in degrees of the sector.
    
    Returns:
    float: The area of the sector. Returns None if the angle is greater than 360 degrees.
    """
    if angle > 360:
        return None
    area = (angle / 360) * 3.14159 * radius ** 2
    return area