def is_perfect_square(n):
    # Calculate the integer square root of n
    root = int(n**0.5)
    # Check if the square of the integer square root equals n
    return root * root == n