import math

def is_perfect_square(n):
    # Calculate the integer square root of the number
    root = int(math.sqrt(n))
    # Check if the square of the integer square root equals the original number
    return root * root == n