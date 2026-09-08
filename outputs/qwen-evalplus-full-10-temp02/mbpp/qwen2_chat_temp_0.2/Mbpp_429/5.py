def and_tuples(tuple1, tuple2):
    """
    Extracts the elementwise and tuples from the given two tuples.
    
    Parameters:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A tuple containing the elementwise and tuples from tuple1 and tuple2.
    """
    # Extracting elementwise elements
    elementwise = tuple((a, b) for a, b in zip(tuple1, tuple2))
    
    # Extracting tuples
    tuples = tuple((a, b) for a, b in zip(tuple1, tuple2) if isinstance(a, tuple) and isinstance(b, tuple))
    
    return elementwise, tuples
