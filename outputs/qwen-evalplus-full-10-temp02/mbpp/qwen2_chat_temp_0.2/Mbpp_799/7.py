def left_rotate(n, d):
    # Ensure d is within the bounds of the number
    d = d % 32
    # Perform the left rotation
    return (n << d) | (n >> (32 - d))