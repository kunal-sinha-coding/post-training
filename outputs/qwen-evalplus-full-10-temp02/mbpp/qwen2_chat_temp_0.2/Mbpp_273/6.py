def substract_elements(tuple1, tuple2):
    """
    Subtract the elements of the first tuple from the second tuple with the same index.
    
    Parameters:
    tuple1 (tuple): The first tuple from which elements will be subtracted.
    tuple2 (tuple): The second tuple from which elements will be subtracted.
    
    Returns:
    tuple: A new tuple containing the elements of tuple1 minus the elements of tuple2 with the same index.
    """
    # Initialize an empty list to store the result
    result = []
    # Iterate over the indices of the tuples
    for index in range(len(tuple1)):
        # Subtract the corresponding elements from tuple1 and append to the result list
        result.append(tuple1[index] - tuple2[index])
    # Return the result list
    return result
