def sequence(n):
    """
    Generate the nth number in the Newman Conway sequence.
    
    Parameters:
    n (int): The position in the sequence.
    
    Returns:
    int: The nth number in the Newman Conway sequence.
    """
    # Base cases
    if n == 0:
        return 0
    elif n == 1:
        return 1
    elif n == 2:
        return 2
    
    # Initialize the first three numbers of the sequence
    a, b, c = 0, 1, 2
    
    # Calculate the nth number in the sequence
    for _ in range(3, n + 1):
        next_number = a + b + c
        a, b, c = b, c, next_number
    
    return c