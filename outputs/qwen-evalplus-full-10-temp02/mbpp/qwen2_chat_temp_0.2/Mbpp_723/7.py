def count_same_pair(list1, list2):
    """
    This function takes two lists of the same length and returns the count of indices where the lists have the same values.
    
    Args:
    list1 (list): The first list of integers.
    list2 (list): The second list of integers.
    
    Returns:
    int: The count of indices where the lists have the same values.
    """
    # Initialize a counter for the number of matching indices
    matching_count = 0
    
    # Iterate through the lists simultaneously
    for i in range(len(list1)):
        # Check if the current elements of both lists are equal
        if list1[i] == list2[i]:
            matching_count += 1
    
    # Return the total count of matching indices
    return matching_count