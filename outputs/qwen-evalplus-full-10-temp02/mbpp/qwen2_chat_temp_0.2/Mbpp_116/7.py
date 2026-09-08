def tuple_to_int(tup):
    """
    Convert a given tuple of positive integers into a single integer.
    
    Parameters:
    tup (tuple): A tuple of positive integers.
    
    Returns:
    int: The single integer formed by the tuple elements.
    
    Examples:
    >>> tuple_to_int((1, 2, 3))
    123
    >>> tuple_to_int((4, 5, 6))
    210
    >>> tuple_to_int((7, 8, 9))
    270
    """
    # Initialize the result to 0
    result = 0
    # Iterate through each element in the tuple
    for num in tup:
        # Add the current number to the result
        result += num
    # Return the final result
    return result