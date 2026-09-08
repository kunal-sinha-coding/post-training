def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Args:
    complex_num (complex): A complex number.
    
    Returns:
    tuple: A tuple containing the polar coordinates (r, theta).
    """
    r = abs(complex_num)
    theta = complex_num.phase()
    return (r, theta)
