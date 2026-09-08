def left_rotate(n, d):
    # Perform left rotation by d bits
    return (n << d) | (n >> (32 - d))