def convert(complex_num):
    """
    Convert a complex number to polar coordinates.
    
    Parameters:
    complex_num (complex): A complex number.
    
    Returns:
    tuple: A tuple containing the magnitude and phase of the complex number.
    """
    # Extract the real and imaginary parts of the complex number
    real_part = complex_num.real
    imaginary_part = complex_num.imag
    
    # Calculate the magnitude
    magnitude = (real_part**2 + imaginary_part**2)**0.5
    
    # Calculate the phase
    phase = complex_num.phase()
    
    # Return the magnitude and phase as a tuple
    return (magnitude, phase)