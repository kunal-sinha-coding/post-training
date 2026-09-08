def left_rotate(n, d):
    """
    Rotate left bits by d bits a given number. We assume that the number is 32 bit.
    
    :param n: The number to rotate.
    :param d: The number of bits to rotate left.
    :return: The rotated number.
    """
    # Calculate the effective number of bits to rotate
    effective_d = d % 32
    # Perform the left rotation
    return (n << effective_d) | (n >> (32 - effective_d))