def left_rotate(n, d):
    # Calculate the effective number of bits to rotate
    effective_bits = d % 32
    # Perform the left rotation
    rotated = (n << effective_bits) | (n >> (32 - effective_bits))
    return rotated