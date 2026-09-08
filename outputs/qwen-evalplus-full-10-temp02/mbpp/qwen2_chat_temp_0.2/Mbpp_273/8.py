def substract_elements(tuple1, tuple2):
    """
    Subtract the elements of the first tuple from the second tuple with the same index.
    
    Parameters:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple with the elements of tuple1 subtracted by the elements of tuple2 with the same index.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for i in range(len(tuple1)):
        # Subtract the elements of tuple1 and tuple2 at the same index
        result.append(tuple1[i] - tuple2[i])
    # Return the result list
    return result
