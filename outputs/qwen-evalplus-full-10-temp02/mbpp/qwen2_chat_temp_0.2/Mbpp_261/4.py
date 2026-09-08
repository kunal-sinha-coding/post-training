def division_elements(tuple1, tuple2):
    """
    Perform element-wise division of two tuples.
    
    Args:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    tuple: A new tuple containing the results of the element-wise division.
    """
    # Initialize an empty list to store the results
    result = []
    # Iterate over the elements of both tuples
    for i in range(len(tuple1)):
        # Perform element-wise division and append the result to the result list
        result.append(tuple1[i] / tuple2[i])
    # Return the list of results
    return result