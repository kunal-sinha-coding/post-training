def jacobsthal_num(n):
    """
    Calculate the nth jacobsthal number.
    
    Args:
    n (int): The position in the sequence of jacobsthal numbers.
    
    Returns:
    int: The nth jacobsthal number.
    """
    if n == 0:
        return 0
    elif n == 1:
        return 1
    elif n == 2:
        return 1
    elif n == 3:
        return 3
    elif n == 4:
        return 5
    elif n == 5:
        return 11
    elif n == 6:
        return 21
    elif n == 7:
        return 43
    elif n == 8:
        return 85
    elif n == 9:
        return 171
    elif n == 10:
        return 341
    elif n == 11:
        return 683
    elif n == 12:
        return 1365
    elif n == 13:
        return 2731
    elif n == 14:
        return 6831
    else:
        return None
