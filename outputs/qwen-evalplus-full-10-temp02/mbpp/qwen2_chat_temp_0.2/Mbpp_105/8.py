def count(lst):
    """
    Count the number of True booleans in the given list.
    
    Args:
    lst (list): A list containing boolean values.
    
    Returns:
    int: The count of True booleans in the list.
    """
    # Initialize a counter for True booleans
    count = 0
    # Iterate through each element in the list
    for item in lst:
        # Check if the item is True
        if item:
            # Increment the counter if the item is True
            count += 1
    # Return the total count of True booleans
    return count