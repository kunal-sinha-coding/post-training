def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Parameters:
    complex_num (complex): A complex number.
    
    Returns:
    tuple: A tuple containing the polar coordinates (magnitude, angle).
    """
    # Extract the real and imaginary parts of the complex number
    real_part = complex_num.real
    imaginary_part = complex_num.imag
    
    # Calculate the magnitude of the complex number
    magnitude = (real_part**2 + imaginary_part**2)**0.5
    
    # Calculate the angle in radians
    angle = complex_num.phase()
    
    # Convert the angle to degrees
    angle_degrees = angle * 180 / math.pi
    
    # Return the polar coordinates as a tuple
    return (magnitude, angle_degrees)