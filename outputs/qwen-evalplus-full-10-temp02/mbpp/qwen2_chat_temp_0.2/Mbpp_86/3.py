def centered_hexagonal_number(n):
    """
    Calculate the nth centered hexagonal number.
    
    A centered hexagonal number is a hexagonal number that is centered within a hexagon.
    The formula for the nth centered hexagonal number is:
    H(n) = (n * (n + 1)) / 2 + 1
    """
    return (n * (n + 1)) // 2 + 1
