def count_bidirectional(tuples_list):
    """
    This function takes a list of tuples as input and returns the count of bidirectional tuple pairs.
    
    Args:
    tuples_list (list of tuples): A list of tuples to be analyzed.
    
    Returns:
    int: The count of bidirectional tuple pairs.
    """
    count = 0
    for i in range(len(tuples_list)):
        for j in range(i + 1, len(tuples_list)):
            if tuples_list[i] == tuples_list[j]:
                count += 1
    return count
