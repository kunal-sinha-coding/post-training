def area_tetrahedron(side):
    """
    Calculate the area of a tetrahedron given its side length.
    
    Parameters:
    side (float): The length of the side of the tetrahedron.
    
    Returns:
    float: The area of the tetrahedron.
    """
    # Calculate the area using the formula: 4 * side^2 / 3
    area = 4 * side ** 2 / 3
    return area