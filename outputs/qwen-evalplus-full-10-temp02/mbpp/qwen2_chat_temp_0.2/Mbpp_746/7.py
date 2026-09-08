def sector_area(radius, angle):
    """
    Calculate the area of a sector given its radius and angle.
    
    Parameters:
    radius (float): The radius of the sector.
    angle (float): The angle in degrees of the sector.
    
    Returns:
    float: The area of the sector.
    
    Raises:
    ValueError: If the angle is greater than 360 degrees.
    """
    if angle > 360:
        raise ValueError("Angle must be less than or equal to 360 degrees.")
    # Calculate the area using the formula: (angle/360) * π * r^2
    area = (angle / 360) * 3.14159 * radius ** 2
    return area