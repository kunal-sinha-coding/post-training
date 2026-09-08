def check_smaller(tuple1, tuple2):
    """
    Check if each element of the second tuple is smaller than its corresponding element in the first tuple.
    
    Parameters:
    tuple1 (tuple): The first tuple.
    tuple2 (tuple): The second tuple.
    
    Returns:
    bool: True if all elements in tuple2 are smaller than their corresponding elements in tuple1, False otherwise.
    """
    # Iterate through each element in tuple2
    for i in range(len(tuple2)):
        # Check if the current element in tuple2 is smaller than the corresponding element in tuple1
        if tuple2[i] < tuple1[i]:
            return False
    # If all elements in tuple2 are smaller than their corresponding elements in tuple1, return True
    return True