import cmath

def angle_complex(real, imag):
    """
    Calculate the angle of a complex number.

    Parameters:
    real (float): The real part of the complex number.
    imag (float): The imaginary part of the complex number.

    Returns:
    float: The angle of the complex number in radians.
    """
    angle = cmath.phase(complex(real, imag))
    return angle
