def left_rotate(n, d):
    """
    Rotate left bits by d bits a given number.
    
    Args:
    n (int): The number to rotate.
    d (int): The number of bits to rotate left.
    
    Returns:
    int: The rotated number.
    """
    # Ensure d is within the bounds of the number of bits
    d = d % 32
    
    # Perform the left rotation
    rotated = n << d | n >> (32 - d)
    
    return rotated