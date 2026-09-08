def left_rotate(n, d):
    # Perform the left rotation
    return (n << d) | (n >> (32 - d))