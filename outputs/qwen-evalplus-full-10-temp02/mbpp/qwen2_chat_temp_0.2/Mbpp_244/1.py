import math

def next_Perfect_Square(n):
    # Calculate the square root of n
    sqrt_n = math.sqrt(n)
    # Round up to the nearest integer
    next_square = math.ceil(sqrt_n)
    # Return the square of the next integer
    return next_square ** 2
