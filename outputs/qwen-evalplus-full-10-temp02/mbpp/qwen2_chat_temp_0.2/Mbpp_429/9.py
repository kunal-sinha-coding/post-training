def and_tuples(tuple1, tuple2):
    """
    Extract the elementwise and tuples from the given two tuples.
    
    Parameters:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A tuple containing the elementwise and tuples from tuple1 and tuple2.
    """
    # Extract elementwise elements from tuple1
    elementwise = tuple(a * b for a, b in zip(tuple1, tuple2))
    
    # Extract tuples from tuple1
    tuples = tuple((a, b) for a, b in zip(tuple1, tuple2))
    
    return elementwise, tuples
