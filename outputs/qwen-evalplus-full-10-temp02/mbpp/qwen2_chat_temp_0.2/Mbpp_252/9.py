def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Args:
    complex_num (complex): The complex number to be converted.
    
    Returns:
    tuple: A tuple containing the polar coordinates of the complex number.
    """
    # Extract real and imaginary parts of the complex number
    real_part = complex_num.real
    imaginary_part = complex_num.imag
    
    # Calculate the magnitude (r) of the complex number
    magnitude = (real_part**2 + imaginary_part**2)**0.5
    
    # Calculate the angle (theta) in radians
    theta = (imaginary_part * 180 / real_part) % 360
    
    # Return the polar coordinates as a tuple
    return (magnitude, theta)
