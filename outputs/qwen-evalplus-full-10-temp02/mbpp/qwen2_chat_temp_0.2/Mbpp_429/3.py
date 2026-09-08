def and_tuples(tup1, tup2):
    """
    Extracts the elementwise and tuples from the given two tuples.
    
    Parameters:
    tup1 (tuple): The first tuple.
    tup2 (tuple): The second tuple.
    
    Returns:
    tuple: A tuple containing the elementwise and tuples from tup1 and tup2.
    """
    # Extracting elementwise elements
    elementwise = tuple(a * b for a, b in zip(tup1, tup2))
    
    # Extracting tuples
    tuples = tuple(tup1 + tup2)
    
    return elementwise, tuples
