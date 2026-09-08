def tuple_to_int(tup):
    """
    Convert a given tuple of positive integers into a single integer.
    
    Args:
    tup (tuple): A tuple of positive integers.
    
    Returns:
    int: The single integer formed by concatenating the elements of the tuple.
    """
    # Convert the tuple to a string and then to an integer
    return int(''.join(map(str, tup)))
