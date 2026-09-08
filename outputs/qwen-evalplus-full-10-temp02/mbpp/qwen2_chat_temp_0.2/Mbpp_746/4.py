def sector_area(radius, angle):
    """
    Calculate the area of a sector given its radius and angle.
    
    Parameters:
    radius (float): The radius of the sector.
    angle (float): The angle in degrees for which the sector is to be calculated.
    
    Returns:
    float: The area of the sector.
    """
    if angle > 360:
        return None
    area = 0.5 * radius * angle
    return area