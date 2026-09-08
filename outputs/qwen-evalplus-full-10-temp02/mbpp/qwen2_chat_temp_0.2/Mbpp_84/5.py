def sequence(n):
    """
    Generate the nth number in the Newman Conway sequence.
    
    Parameters:
    n (int): The position in the sequence.
    
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
    
    # Initialize the first four numbers of the sequence
    a, b, c, d = 1, 2, 3, 5
    
    # Calculate the nth number in the sequence
    for _ in range(5, n + 1):
        next_number = a + b + c + d
        a, b, c, d = b, c, d, next_number
    
    return d