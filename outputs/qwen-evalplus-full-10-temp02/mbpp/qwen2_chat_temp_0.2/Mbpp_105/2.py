def count(lst):
    """
    Count the number of true booleans in the given list.
    
    Parameters:
    lst (list): A list containing boolean values.
    
    Returns:
    int: The count of true booleans in the list.
    """
    # Initialize a counter for true booleans
    count_true = 0
    # Iterate through each element in the list
    for element in lst:
        # Check if the element is true
        if element:
            # Increment the counter if the element is true
            count_true += 1
    # Return the total count of true booleans
    return count_true