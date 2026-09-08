import math

def is_perfect_square(n):
    # Calculate the integer square root of n
    s = int(math.sqrt(n))
    # Check if the square of the integer square root equals n
    return s * s == n