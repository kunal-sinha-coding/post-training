def count_same_pair(list1, list2):
    """
    Counts the number of indices where the two lists have the same values.
    
    Parameters:
    list1 (list): The first list of integers.
    list2 (list): The second list of integers.
    
    Returns:
    int: The count of indices where the lists have the same values.
    """
    count = 0
    for i in range(len(list1)):
        if list1[i] == list2[i]:
            count += 1
    return count