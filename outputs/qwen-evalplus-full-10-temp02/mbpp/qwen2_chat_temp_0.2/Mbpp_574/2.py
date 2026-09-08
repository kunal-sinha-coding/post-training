def surfacearea_cylinder(radius, height):
    """
    Calculate the surface area of a cylinder.

    Parameters:
    radius (float): The radius of the cylinder.
    height (float): The height of the cylinder.

    Returns:
    float: The surface area of the cylinder.
    """
    # Calculate the surface area using the formula: 2 * pi * (radius + height)
    surface_area = 2 * 3.14159 * (radius + height)
    return surface_area