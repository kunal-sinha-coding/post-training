def find_lucas(n):
    """
    Calculate the n'th lucas number.
    
    Args:
    n (int): The position in the lucas sequence.
    
    Returns:
    int: The n'th lucas number.
    """
    # Base cases for the first two lucas numbers
    if n == 0:
        return 2
    elif n == 1:
        return 1
    
    # Initialize the first two lucas numbers
    lucas_1, lucas_2 = 2, 1
    
    # Calculate the lucas numbers iteratively
    for _ in range(2, n + 1):
        lucas_next = lucas_1 + lucas_2
        lucas_1, lucas_2 = lucas_2, lucas_next
    
    return lucas_2