def substract_elements(tuple1, tuple2):
    """
    Subtract the elements of the first tuple from the second tuple with the same index.
    
    Parameters:
    tuple1 (tuple): The first tuple from which elements will be subtracted.
    tuple2 (tuple): The second tuple from which elements will be subtracted.
    
    Returns:
    tuple: A new tuple with the elements of tuple1 subtracted by the elements of tuple2 with the same index.
    """
    # Initialize an empty tuple to store the result
    result = ()
    # Iterate over the indices of the tuples
    for i in range(len(tuple1)):
        # Subtract the corresponding elements from the result tuple
        result += (tuple1[i] - tuple2[i],)
    return result
