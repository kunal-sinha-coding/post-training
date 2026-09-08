def count_bidirectional(test_list):
    """
    Count the number of bidirectional tuple pairs in a given list.
    
    Args:
    test_list (list of tuples): The list of tuples to be analyzed.
    
    Returns:
    int: The count of bidirectional tuple pairs.
    """
    bidirectional_pairs = 0
    for i in range(len(test_list)):
        for j in range(i + 1, len(test_list)):
            if test_list[i] == test_list[j]:
                bidirectional_pairs += 1
    return bidirectional_pairs
