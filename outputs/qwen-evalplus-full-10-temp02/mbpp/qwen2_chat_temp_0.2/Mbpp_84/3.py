def sequence(n):
    """
    Generate the nth number in the Newman Conway sequence.
    
    Parameters:
    n (int): The position in the sequence to find.
    
    Returns:
    int: The nth number in the Newman Conway sequence.
    """
    # Base cases
    if n == 1:
        return 1
    elif n == 2:
        return 2
    elif n == 3:
        return 3
    elif n == 4:
        return 5
    elif n == 5:
        return 8
    elif n == 6:
        return 13
    elif n == 7:
        return 24
    elif n == 8:
        return 44
    elif n == 9:
        return 77
    elif n == 10:
        return 131
    else:
        # For n > 10, use the formula for Newman Conway
        return sequence(n - 1) + sequence(n - 2) + sequence(n - 3) + sequence(n - 4) + sequence(n - 5) + sequence(n - 6) + sequence(n - 7) + sequence(n - 8) + sequence(n - 9) + sequence(n - 10)