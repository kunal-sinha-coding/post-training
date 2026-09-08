def left_rotate(n, d):
    """
    Rotate left bits by d bits a given number. We assume that the number is 32 bit.
    
    Parameters:
    n (int): The number to rotate.
    d (int): The number of bits to rotate left.
    
    Returns:
    int: The rotated number.
    """
    # Ensure d is within the bounds of the number of bits
    d = d % 32
    
    # Perform the left rotation
    return (n << d) | (n >> (32 - d))