def count_bidirectional(test_list):
    """
    This function counts the number of bidirectional tuple pairs in the given list.
    
    Parameters:
    test_list (list of tuples): The list of tuples to be analyzed.
    
    Returns:
    int: The count of bidirectional tuple pairs.
    """
    count = 0
    for i in range(len(test_list)):
        for j in range(i + 1, len(test_list)):
            if test_list[i] == test_list[j]:
                count += 1
    return count