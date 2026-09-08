def left_rotate(number, d):
    # Perform left rotation by d bits
    rotated_number = (number << d) | (number >> (32 - d))
    return rotated_number