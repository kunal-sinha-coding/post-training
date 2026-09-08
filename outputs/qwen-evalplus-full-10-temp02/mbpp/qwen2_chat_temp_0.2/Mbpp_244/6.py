import math

def next_Perfect_Square(n):
    # Calculate the square root of n
    sqrt_n = math.sqrt(n)
    # Round up to the nearest whole number
    next_square = math.ceil(sqrt_n)
    # Return the next perfect square greater than n
    return next_square * next_square
