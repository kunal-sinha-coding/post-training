def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Parameters:
    complex_num (complex): A complex number.
    
    Returns:
    tuple: A tuple containing the polar coordinates of the complex number.
    """
    # Extract real and imaginary parts
    real_part = complex_num.real
    imag_part = complex_num.imag
    
    # Calculate the magnitude (r)
    magnitude = (real_part**2 + imag_part**2)**0.5
    
    # Calculate the angle (theta)
    theta = (imag_part * 180 / real_part) % 360
    
    # Return the polar coordinates as a tuple
    return (magnitude, theta)
