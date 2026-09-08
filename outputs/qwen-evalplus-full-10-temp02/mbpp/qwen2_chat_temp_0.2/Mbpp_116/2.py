def tuple_to_int(tup):
    """
    Convert a given tuple of positive integers into a single integer.
    
    Args:
    tup (tuple): A tuple of positive integers.
    
    Returns:
    int: The single integer formed by the elements of the tuple.
    """
    # Initialize the result to 0
    result = 0
    # Iterate through each element in the tuple
    for num in tup:
        # Add the current element to the result
        result += num
    # Return the final result
    return result