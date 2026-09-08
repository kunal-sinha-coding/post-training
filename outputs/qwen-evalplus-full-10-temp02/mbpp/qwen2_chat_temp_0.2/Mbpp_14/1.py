def find_Volume(length, width, height):
    """
    Calculate the volume of a triangular prism.

    Parameters:
    length (float): The length of the triangular base.
    width (float): The width of the triangular base.
    height (float): The height of the triangular prism.

    Returns:
    float: The volume of the triangular prism.
    """
    # Calculate the volume using the formula: Volume = base * height * width
    volume = length * width * height
    return volume