def surfacearea_cube(side_length):
    """
    Calculate the surface area of a cube given its side length.
    
    Args:
    side_length (int): The length of the side of the cube.
    
    Returns:
    int: The surface area of the cube.
    """
    # Calculate the surface area using the formula 6 * side_length^2
    surface_area = 6 * side_length ** 2
    return surface_area