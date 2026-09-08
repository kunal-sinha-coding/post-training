def tuple_modulo(tup1, tup2):
    """
    This function takes two tuples of the same length and performs the element-wise modulo operation.
    
    Parameters:
    tup1 (tuple): The first tuple.
    tup2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple containing the element-wise modulo of the two input tuples.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the elements of the two tuples
    for i in range(len(tup1)):
        # Perform element-wise modulo operation and append to the result list
        result.append(tup1[i] % tup2[i])
    # Return the list of result elements
    return tuple(result)