def sequence(n):
    """
    This function calculates the nth number in the Newman Conway sequence.
    
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
    
    # Initialize the first four numbers of the sequence
    a, b, c, d = 1, 2, 3, 4
    
    # Calculate the nth number in the sequence
    for _ in range(4, n + 1):
        next_number = a + b + c + d
        a, b, c, d = b, c, d, next_number
    
    return d