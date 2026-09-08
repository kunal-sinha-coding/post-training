def substract_elements(tuple1, tuple2):
    """
    Subtract the elements of the first tuple from the second tuple with the same index.
    
    Args:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple with the elements of the first tuple subtracted by the elements of the second tuple.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for i in range(len(tuple1)):
        # Subtract the element of the second tuple from the element of the first tuple
        result.append(tuple1[i] - tuple2[i])
    # Return the new tuple with the result
    return tuple(result)