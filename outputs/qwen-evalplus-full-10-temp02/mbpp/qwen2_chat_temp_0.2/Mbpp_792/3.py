def count_list(lists):
    """
    Count the number of lists in a given number of lists.
    
    Parameters:
    lists (list): A list of lists.
    
    Returns:
    int: The number of lists in the given list.
    """
    # Initialize a counter for the number of lists
    count = 0
    # Iterate through each sublist in the list
    for sublist in lists:
        # Increment the counter for each sublist
        count += 1
    # Return the total count of lists
    return count