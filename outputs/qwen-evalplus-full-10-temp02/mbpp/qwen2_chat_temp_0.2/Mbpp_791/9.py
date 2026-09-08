def remove_nested(tup):
    """
    Remove tuples from the given tuple.
    
    Args:
    tup (tuple): The input tuple from which tuples are to be removed.
    
    Returns:
    tuple: A new tuple with all tuples removed.
    """
    # Using list comprehension to remove tuples from the tuple
    return tuple(item for item in tup if not isinstance(item, tuple))
