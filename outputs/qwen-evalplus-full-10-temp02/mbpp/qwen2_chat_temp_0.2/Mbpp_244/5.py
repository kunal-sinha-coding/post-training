import math

def next_Perfect_Square(n):
    # Calculate the square root of the given number
    sqrt_n = math.sqrt(n)
    # Round up to the nearest integer
    up_sqrt_n = math.ceil(sqrt_n)
    # Return the square of the rounded up integer
    return up_sqrt_n ** 2
