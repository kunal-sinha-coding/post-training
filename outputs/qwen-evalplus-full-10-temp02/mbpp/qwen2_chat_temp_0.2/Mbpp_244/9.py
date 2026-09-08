import math

def next_Perfect_Square(n):
    # Calculate the square root of the given number
    root = math.sqrt(n)
    # Round up to the nearest integer
    next_square = math.ceil(root)
    # Return the next perfect square greater than the given number
    return next_square * next_square
