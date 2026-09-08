def left_rotate(n, d):
    # Calculate the effective rotation needed
    effective_rotation = d % 32
    # Perform the left rotation
    return (n << effective_rotation) | (n >> (32 - effective_rotation))