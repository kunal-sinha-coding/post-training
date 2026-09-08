def tuple_modulo(tuple1, tuple2):
    """
    Perform element-wise modulo on two tuples of the same length.
    
    Args:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple containing the element-wise modulo of the two input tuples.
    """
    # Ensure both tuples have the same length
    if len(tuple1) != len(tuple2):
        raise ValueError("Both tuples must have the same length.")
    
    # Perform element-wise modulo
    result = tuple(a % b for a, b in zip(tuple1, tuple2))
    return result
