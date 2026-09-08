import math

def angle_complex(real_part, imaginary_part):
    """
    Calculate the angle of a complex number.
    
    Args:
    real_part (float): The real part of the complex number.
    imaginary_part (float): The imaginary part of the complex number.
    
    Returns:
    float: The angle of the complex number in radians.
    """
    # Calculate the angle using the arctan function
    angle_radians = math.atan2(imaginary_part, real_part)
    return angle_radians
