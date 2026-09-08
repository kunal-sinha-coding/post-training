def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Args:
    complex_num (complex): A complex number.
    
    Returns:
    tuple: A tuple containing the magnitude and phase of the complex number.
    """
    magnitude = abs(complex_num)
    phase = complex_num.phase()
    return (magnitude, phase)
