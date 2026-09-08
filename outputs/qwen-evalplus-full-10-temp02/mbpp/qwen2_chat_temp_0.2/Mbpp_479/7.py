def first_Digit(number):
    """
    This function takes an integer as input and returns its first digit.
    
    Args:
    number (int): The integer whose first digit is to be found.
    
    Returns:
    int: The first digit of the given number.
    
    Examples:
    >>> first_Digit(123)
    1
    >>> first_Digit(456)
    4
    >>> first_Digit(789)
    7
    """
    return number // 10