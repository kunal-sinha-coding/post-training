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
    # Calculate the volume using the formula: V = (1/3) * base * height
    volume = (1/3) * length * width * height
    return volume