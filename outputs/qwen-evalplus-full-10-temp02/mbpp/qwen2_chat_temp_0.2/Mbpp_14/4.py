def find_Volume(length, width, height):
    """
    Calculate the volume of a triangular prism.

    Parameters:
    length (float): The length of the base of the prism.
    width (float): The width of the base of the prism.
    height (float): The height of the prism.

    Returns:
    float: The volume of the triangular prism.
    """
    # Calculate the volume using the formula: V = base * height * width
    volume = length * width * height
    return volume