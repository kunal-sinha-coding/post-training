def surface_Area(base_edge, height):
    """
    Calculate the surface area of a square pyramid.

    Parameters:
    base_edge (float): The length of the base edge of the pyramid.
    height (float): The height of the pyramid.

    Returns:
    float: The surface area of the pyramid.
    """
    # Calculate the slant height of the pyramid
    slant_height = (base_edge * height) ** 0.5
    # Calculate the area of the base of the pyramid
    base_area = base_edge ** 2
    # Calculate the area of the four triangular faces
    face_area = 3 * (base_area + slant_height)
    # Calculate the total surface area
    total_surface_area = base_area + face_area
    return total_surface_area