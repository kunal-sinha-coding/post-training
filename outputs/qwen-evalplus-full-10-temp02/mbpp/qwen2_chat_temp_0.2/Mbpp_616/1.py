def tuple_modulo(tup1, tup2):
    """
    Perform element-wise modulo on two tuples of the same length.
    
    Parameters:
    tup1 (tuple): The first tuple.
    tup2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple containing the element-wise modulo of the two input tuples.
    """
    # Ensure both tuples have the same length
    if len(tup1) != len(tup2):
        raise ValueError("Both tuples must have the same length.")
    
    # Perform element-wise modulo
    result = tuple(a % b for a, b in zip(tup1, tup2))
    
    return result
