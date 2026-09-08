def tuple_modulo(tuple1, tuple2):
    """
    Perform element-wise modulo on two tuples of the same length.
    
    Args:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple containing the element-wise modulo of the two input tuples.
    """
    # Using the zip function to iterate over pairs of elements from both tuples
    result = tuple(a % b for a, b in zip(tuple1, tuple2))
    return result
