def tuple_modulo(tuple1, tuple2):
    """
    This function takes two tuples of the same length and performs the element-wise modulo operation.
    
    Parameters:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple containing the element-wise modulo of the two input tuples.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the elements of the two tuples
    for i in range(len(tuple1)):
        # Perform element-wise modulo operation and append to the result list
        result.append(tuple1[i] % tuple2[i])
    # Return the result list
    return result