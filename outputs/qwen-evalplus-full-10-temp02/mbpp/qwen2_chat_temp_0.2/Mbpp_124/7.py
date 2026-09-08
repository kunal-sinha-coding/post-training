import cmath

def angle_complex(real_part, imag_part):
    """
    Calculate the angle of a complex number.
    
    Args:
    real_part (float): The real part of the complex number.
    imag_part (float): The imaginary part of the complex number.
    
    Returns:
    float: The angle of the complex number in radians.
    """
    angle = cmath.phase(complex(real_part, imag_part))
    return angle
