def remove_nested(tup):
    """
    Remove tuples from the given tuple.
    
    Parameters:
    tup (tuple): The input tuple from which tuples will be removed.
    
    Returns:
    tuple: A new tuple with all tuples removed.
    """
    # Use list comprehension to filter out tuples
    return tuple(item for item in tup if not isinstance(item, tuple))
